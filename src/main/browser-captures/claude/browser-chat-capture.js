function setupExporter() {
  const AGENT = 'Claude';
  const originalWriteText = navigator.clipboard.writeText;
  let currentCapture = null;
  let interceptorActive = false;

  // Ordered transcript: {role: 'Human'|AGENT, content} in true conversation order.
  // claude.ai virtualizes long conversations (a sliding window of ~10-12 rendered
  // messages; off-window nodes are REMOVED), so a one-shot DOM snapshot only ever
  // sees the tail. The capture therefore walks to the top of the history, then
  // walks back down capturing each message as it enters the render window.
  // Deduplication is by DOM element identity (a dataset marker on captured rows):
  // rendered rows are stable keyed nodes while in the window, and text-based keys
  // cannot distinguish genuinely repeated messages (same text sent twice, the same
  // file re-uploaded) from window overlap.
  const transcript = [];

  // Liveness/progress flags the driver (safari_capture.py) polls — so it detects start,
  // progress, completion, and errors directly instead of waiting out a download timeout.
  // `progress` is a heartbeat that ticks on every scroll step: during the walk-to-top
  // phase nothing is captured for minutes, and without it the driver would call a
  // healthy walk a stall.
  window.__scrape = { started: true, captured: 0, progress: 0, done: false, error: null };

  const _consoleLogs = [];
  const log = (level, ...args) => {
    const msg = args.map(a => (a instanceof Error) ? a.stack : typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ');
    _consoleLogs.push(`[${new Date().toISOString()}] [${level}] ${msg}`);
    console[level.toLowerCase()](...args);
  };

  // DOM Selectors - easily modifiable if Claude's UI changes
  const SELECTORS = {
    messageRow: '[data-test-render-count]',   // one per message; survives virtualization re-renders
    copyButton: 'button[data-testid="action-bar-copy"]',
    // both vintages: claude.ai renamed the label ~2026-07 (found 2026-07-22
    // when every scrape of a 100-conversation recapture came out all-Human).
    // The feedback buttons are the bar's ONLY testid-less buttons (surveyed
    // 2026-07-22), so labels are all they offer — last-resort cue only.
    feedbackButton: 'button[aria-label="Good response"], button[aria-label="Give positive feedback"]',
    editButton: 'button[data-testid="action-bar-edit"]',   // human bars only; testid-grade
    messageContainer: '.mb-1.group',
    agentContainer: '.group',
    messageText: 'p.whitespace-pre-wrap',
    responseText: 'p.font-claude-response-body',
  };

  const DELAYS = {
    copy: 100,
    startup: 1000,
    cleanup: 3000,
    scrollSettle: 1500,   // per scroll step, for the virtualizer to fetch/render
  };

  const LIMITS = {
    maxScrollSteps: 400,  // per phase; ~10 min at scrollSettle — a runaway backstop, not a target
    stableTicks: 3,       // consecutive no-change ticks before an edge is trusted
  };

  const STATUS = {  // status-box colour per state — CSS named colours, identical for both agents
    info:    'blue',
    success: 'green',
    warn:    'orange',
    error:   'red',
  };

  function downloadBlob(content, filename, type) {
    const blob = new Blob([content], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function getConversationTitle() {
    const convId = location.pathname.split('/').pop();
    const title = document.title.replace(/ - Claude$/, '').trim();
    const slug = title.toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')   // collapse anything non-alphanumeric (incl. bidi/zero-width marks)
      .replace(/^_+|_+$/g, '')
      .substring(0, 100);
    if (!slug || title === AGENT || title.includes('New conversation')) {
      return convId || `${AGENT.toLowerCase()}_conversation`;
    }
    return slug;
  }

  function readFromDOM(row) {
    const els = row.querySelectorAll(SELECTORS.responseText);
    if (els.length) return Array.from(els).map(e => e.innerText.trim()).filter(t => t).join('\n\n');
    return null;
  }

  function describeRow(row) {
    // Plain text message
    const p = row.querySelector(SELECTORS.messageText);
    if (p) return '"' + p.innerText.trim().substring(0, 60).replace(/\n/g, ' / ') + '"';

    // Image attachments
    const imgs = row.querySelectorAll('img[alt]');
    if (imgs.length) {
      const names = Array.from(imgs).map(i => i.alt).filter(a => a).join(', ');
      return '[image: ' + names.substring(0, 60) + ']';
    }

    // File/code attachments and tool results: strip sr-only text then use innerText
    const srOnly = row.querySelector('.sr-only');
    const t = (srOnly ? row.innerText.replace(srOnly.innerText, '') : row.innerText)
                .trim().substring(0, 60).replace(/\n/g, ' / ');
    return t.length > 5 ? '"' + t + '"' : '(no text)';
  }

  // Intercept clipboard writes and route to the active capture target
  navigator.clipboard.writeText = function(text) {
    if (interceptorActive && text && currentCapture) {
      currentCapture.push(text);
    }
  };

  // Create status indicator
  const statusDiv = document.createElement('div');
  statusDiv.style.cssText = `
    position: fixed; top: 10px; right: 10px; z-index: 10000;
    background: ${STATUS.info}; color: white; padding: 10px 15px;
    border-radius: 5px; font-family: monospace; font-size: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.3); max-width: 300px;
  `;
  document.body.appendChild(statusDiv);

  function setStatus(msg, state = 'info') {
    const p = window.__capture_progress ? `conversation ${window.__capture_progress} — ` : '';
    statusDiv.textContent = p + msg;
    statusDiv.style.background = STATUS[state];
  }

  function updateStatus() {
    window.__scrape.captured = transcript.length;
    const h = transcript.filter(t => t.role === 'Human').length;
    setStatus(`Human: ${h} | ${AGENT}: ${transcript.length - h}`);
  }

  // A copy button's action bar = the largest ancestor still containing exactly
  // that one copy button. We derive it from the leaf buttons (stable testids)
  // rather than a labeled wrapper, which is prone to drift.
  function actionBarOf(btn) {
    let bar = btn, el = btn.parentElement;
    while (el && el.querySelectorAll(SELECTORS.copyButton).length === 1) {
      bar = el;
      el = el.parentElement;
    }
    return bar;
  }

  // Human message ↔ agent response. Primary cue is STRUCTURAL: only agent rows
  // render response-body paragraphs — the same selector content extraction
  // trusts, so role and content can no longer fail independently (the 2026-07-22
  // lesson: the feedback button's aria-label drifted and 100 conversations
  // scraped all-Human with perfect content). The feedback button, both label
  // vintages, stays as fallback for a row whose text kind is ambiguous.
  function roleOf(copyBtn) {
    const row = copyBtn.closest(SELECTORS.messageRow);
    if (row && row.querySelector(SELECTORS.responseText)) return AGENT;
    if (row && row.querySelector(SELECTORS.messageText)) return 'Human';
    const bar = actionBarOf(copyBtn);
    if (bar.querySelector(SELECTORS.editButton)) return 'Human';   // testid-grade
    return bar.querySelector(SELECTORS.feedbackButton) ? AGENT : 'Human';
  }

  // Message rows of the LIVE conversation frame only: during navigation transitions
  // claude.ai can hold a previous render in an [inert] frame. (The frame's testid
  // names contain "stale-nav" even when live — filter on the inert attribute, which
  // reflects actual state, never on the name.)
  function liveRows() {
    return Array.from(document.querySelectorAll(SELECTORS.messageRow))
      .filter(r => !r.closest('[inert]'));
  }

  // The conversation's scroll container: nearest scrollable ancestor of a live message row.
  function scrollerOf() {
    let el = liveRows()[0] || document.querySelector(SELECTORS.copyButton);
    while (el) {
      const s = getComputedStyle(el);
      if ((s.overflowY === 'scroll' || s.overflowY === 'auto') && el.scrollHeight > el.clientHeight) return el;
      el = el.parentElement;
    }
    return null;
  }

  function tickProgress(msg) {
    window.__scrape.progress++;
    setStatus(msg);
  }

  // Phase 1: walk to the top of the history. Instantly pinning scrollTop to 0 does NOT
  // work — the virtualizer loads on gradual passes — and content prepending above pushes
  // scrollTop back off 0, so the top is only trusted after stableTicks quiet ticks.
  async function scrollToTop() {
    const sc = scrollerOf();
    let stable = 0;
    for (let i = 0; i < LIMITS.maxScrollSteps; i++) {
      if (sc) sc.scrollBy(0, -Math.round(sc.clientHeight * 0.8));
      else window.scrollBy(0, -600);
      await delay(DELAYS.scrollSettle);
      tickProgress(`loading history… step ${i + 1}`);
      const top = sc ? sc.scrollTop : window.scrollY;
      stable = top === 0 ? stable + 1 : 0;
      if (stable >= LIMITS.stableTicks) return;
    }
    log('WARN', `⚠️ hit maxScrollSteps (${LIMITS.maxScrollSteps}) walking up — history may be longer than captured`);
  }

  async function captureRow(row, copyBtn) {
    const tmp = [];
    currentCapture = tmp;
    try {
      copyBtn.click();
      await delay(DELAYS.copy);
    } catch (error) {
      log('WARN', 'copy click failed:', error);
    }
    currentCapture = null;
    if (tmp.length) return tmp[0];
    const domText = readFromDOM(row);
    if (domText) return domText;
    return `[no capture — ${describeRow(row)}]`;
  }

  // Phase 2: walk back down, capturing each message row as it enters the render window.
  // Rows are processed in document order per step; the monotonic downward walk makes
  // append-order the true conversation order. A row is captured once, marked with a
  // dataset attribute — element identity, immune to identical message text. The bottom
  // is only trusted after stableTicks steps with no scroll movement AND no new rows.
  async function captureWalkingDown() {
    const sc = scrollerOf();
    let stable = 0;
    for (let i = 0; i < LIMITS.maxScrollSteps; i++) {
      let added = 0;
      // Capture only rows at/above the sweep's viewport edge: the virtualizer is lazy
      // about evicting rows from the PREVIOUS view (hysteresis), and those leftovers
      // sit far below — sweeping them early corrupts the transcript order. They are
      // captured when the walk actually reaches them.
      const limit = (sc ? sc.getBoundingClientRect().bottom : window.innerHeight) + 100;
      for (const row of liveRows()) {
        if (row.dataset.scraped) continue;
        if (row.getBoundingClientRect().top > limit) continue;
        row.dataset.scraped = '1';
        const copyBtn = row.querySelector(SELECTORS.copyButton);
        if (!copyBtn) {
          log('LOG', `row without copy button skipped — ${describeRow(row)}`);
          continue;
        }
        const role = roleOf(copyBtn);
        const content = await captureRow(row, copyBtn);
        transcript.push({ role, content });
        added++;
        updateStatus();
        log('LOG', `📋 Captured ${role} message (${transcript.length} total)`);
      }
      const before = sc ? sc.scrollTop : window.scrollY;
      if (sc) sc.scrollBy(0, Math.round(sc.clientHeight * 0.8));
      else window.scrollBy(0, 600);
      await delay(DELAYS.scrollSettle);
      tickProgress(`capturing… ${transcript.length} messages`);
      const after = sc ? sc.scrollTop : window.scrollY;
      stable = (after === before && added === 0) ? stable + 1 : 0;
      if (stable >= LIMITS.stableTicks) return;
    }
    log('WARN', `⚠️ hit maxScrollSteps (${LIMITS.maxScrollSteps}) walking down — capture may be incomplete`);
  }

  function buildMarkdown(title) {
    let markdown = `# ${title}\n\n<${window.location.href}>\n\n`;
    let h = 0, a = 0;
    for (const turn of transcript) {
      const n = turn.role === 'Human' ? ++h : ++a;
      markdown += `## ${turn.role} (${n})\n\n${turn.content}\n\n---\n\n`;
    }
    return markdown;
  }

  async function startExport() {
    try {
      if (!liveRows().length) {
        const rawCopy = document.querySelectorAll(SELECTORS.copyButton).length;
        throw new Error(
          rawCopy === 0
            ? `No message rows or copy buttons in DOM. Page not loaded, wrong page, or selectors "${SELECTORS.messageRow}" / "${SELECTORS.copyButton}" drifted.`
            : `No "${SELECTORS.messageRow}" rows but ${rawCopy} copy button(s) — the row selector drifted, not the page.`
        );
      }

      setStatus('Loading full history (walking to top)...');
      interceptorActive = true;
      await scrollToTop();

      setStatus('Capturing (walking down)...');
      await captureWalkingDown();

      const h = transcript.filter(t => t.role === 'Human').length;
      log('LOG', `📊 Captured ${transcript.length} messages (${h} human, ${transcript.length - h} ${AGENT.toLowerCase()})`);
      // A real conversation alternates: one speaker owning EVERY turn means the
      // role cue died, and a mis-roled scrape is worse than none (2026-07-22: a
      // WARN here let 100 all-Human scrapes land silently). Fail, write nothing.
      if (transcript.length >= 2 && (h === 0 || h === transcript.length)) {
        throw new Error(`role detection broke: ${h} human of ${transcript.length} — ` +
                        'selector drift? nothing written');
      }
      if (Math.abs(h - (transcript.length - h)) > 1) {
        log('WARN', `⚠️ Unbalanced counts (${h} human vs ${transcript.length - h} ${AGENT.toLowerCase()}) — possible misclassification from selector drift`);
      }

      completeExport();

    } catch (error) {
      window.__scrape.error = error.message || String(error);
      setStatus(`Error: ${error.message}`, 'error');
      log('ERROR', 'Export failed:', error);
    } finally {
      setTimeout(cleanup, DELAYS.cleanup);
    }
  }

  function completeExport() {
    interceptorActive = false;

    if (transcript.length === 0) {
      setStatus('No messages captured!', 'error');
      return;
    }

    const rawTitle = getConversationTitle();
    const filename = `${rawTitle}.md`;
    downloadBlob(buildMarkdown(rawTitle || `Conversation with ${AGENT}`), filename, 'text/markdown');

    setStatus(`✅ Downloaded: ${filename}`, 'success');

    log('LOG', 'Export complete.');
  }

  function cleanup() {
    navigator.clipboard.writeText = originalWriteText;
    document.removeEventListener('visibilitychange', onVisibilityChange);
    downloadBlob(_consoleLogs.join('\n'), `${getConversationTitle()}.log`, 'text/plain');
    if (document.body.contains(statusDiv)) {
      document.body.removeChild(statusDiv);
    }
    window.__scrape.done = true;
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'hidden') {
      log('WARN', '⚠️ Page hidden — script execution may be suspended by the browser');
      setStatus('⚠️ Page hidden — please return to this tab', 'warn');
    } else {
      statusDiv.style.background = STATUS.info;
      updateStatus();
    }
  }
  document.addEventListener('visibilitychange', onVisibilityChange);

  // Initialize
  updateStatus();
  setTimeout(startExport, DELAYS.startup);
}

// Run the exporter
setupExporter();
