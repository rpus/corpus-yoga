function setupExporter() {
  const AGENT = 'Gemini';
  const originalWriteText = navigator.clipboard.writeText;
  const originalWrite = navigator.clipboard.write.bind(navigator.clipboard);
  let currentCapture = null;
  let interceptorActive = false;

  // Ordered transcript: {role: 'Human'|AGENT, content} in true conversation order.
  // Gemini renders only the last ~10 exchanges initially and lazy-loads older
  // history in batches when scrolled near the top (prepending and re-positioning
  // the scroll) — so a one-shot DOM snapshot only ever sees the tail. The capture
  // therefore walks to the top of the history, then walks back down capturing each
  // message row. Unlike claude.ai, Gemini RETAINS loaded rows (no virtualized
  // eviction observed), but the same walk architecture is used for uniformity and
  // robustness; under retention the dedup marker is simply never needed twice.
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

  // DOM Selectors — Gemini uses custom Angular elements as stable anchors
  const SELECTORS = {
    messageRow: 'user-query, model-response',   // role comes from the tag name
    humanCopyButton: 'button[aria-label="Copy prompt"]',
    agentCopyButton: 'button[aria-label="Copy"]',
  };

  const DELAYS = {
    copy: 300,
    startup: 1000,
    cleanup: 3000,
    scrollSettle: 1500,   // per scroll step, for the lazy-loader to fetch/prepend a batch
  };

  const LIMITS = {
    maxScrollSteps: 400,  // per phase; a runaway backstop, not a target
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
    const title = document.title.replace(/ - Google Gemini$/, '').trim();
    const slug = title.toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')   // collapse anything non-alphanumeric (incl. bidi/zero-width marks)
      .replace(/^_+|_+$/g, '')
      .substring(0, 100);
    if (!slug || title === AGENT) {
      return convId || `${AGENT.toLowerCase()}_conversation`;
    }
    return slug;
  }

  navigator.clipboard.writeText = function(text) {
    if (interceptorActive && text && currentCapture) {
      currentCapture.push(text);
    }
  };

  // Gemini response copy buttons use clipboard.write() with a ClipboardItem asynchronously,
  // which the browser blocks (NotAllowedError) outside a user-gesture context. We intercept
  // the call before it reaches the browser, extract text/plain from the ClipboardItem, and
  // suppress the actual write so Gemini's code doesn't throw.
  navigator.clipboard.write = function (items) {
    if (interceptorActive && currentCapture) {
      const target = currentCapture;
      Promise.all(items.map(item =>
        item.types.includes('text/plain')
          ? item.getType('text/plain').then(blob => blob.text())
          : Promise.resolve(null)
      )).then(texts => {
        const text = texts.find(t => t);
        if (text) target.push(text);
      });
      return Promise.resolve();
    }
    return originalWrite(items);
  };

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

  function liveRows() {
    return Array.from(document.querySelectorAll(SELECTORS.messageRow))
      .filter(r => !r.closest('[inert]'));
  }

  function roleOf(row) {
    return row.tagName === 'USER-QUERY' ? 'Human' : AGENT;
  }

  function copyButtonOf(row) {
    return row.querySelector(row.tagName === 'USER-QUERY' ? SELECTORS.humanCopyButton : SELECTORS.agentCopyButton);
  }

  function describeRow(row) {
    const t = (row.innerText || '').trim().substring(0, 60).replace(/\n/g, ' / ');
    return t.length > 5 ? '"' + t + '"' : '(no text)';
  }

  // The conversation's scroll container: nearest scrollable ancestor of a live message row.
  function scrollerOf() {
    let el = liveRows()[0];
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

  // Phase 1: walk to the top of the history. Gemini fetches an older batch only when
  // the viewport nears the top, then prepends it and throws scrollTop back down — so
  // the top is only trusted after stableTicks quiet ticks at scrollTop 0.
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
    return `[no capture — ${describeRow(row)}]`;
  }

  // Phase 2: walk back down, capturing each message row in document order. A row is
  // captured once, marked with a dataset attribute — element identity, immune to
  // identical message text. Only rows at/above the sweep's viewport edge are taken,
  // so ordering cannot be corrupted by rows rendered ahead of the sweep. The bottom
  // is only trusted after stableTicks steps with no scroll movement AND no new rows.
  async function captureWalkingDown() {
    const sc = scrollerOf();
    let stable = 0;
    for (let i = 0; i < LIMITS.maxScrollSteps; i++) {
      let added = 0;
      const limit = (sc ? sc.getBoundingClientRect().bottom : window.innerHeight) + 100;
      for (const row of liveRows()) {
        if (row.dataset.scraped) continue;
        if (row.getBoundingClientRect().top > limit) continue;
        row.dataset.scraped = '1';
        const copyBtn = copyButtonOf(row);
        if (!copyBtn) {
          log('LOG', `row without copy button skipped — ${describeRow(row)}`);
          continue;
        }
        const role = roleOf(row);
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
        // Three guesses used to be offered here and none of them chosen, while the DOM held
        // the evidence that separates them: WHICH page this is, and whether the selector
        // matched anything at all before liveRows() dropped the inert ones.
        const matched = document.querySelectorAll(SELECTORS.messageRow).length;
        throw new Error(
          `No live message rows at ${location.pathname} — ` + (matched
            ? `${matched} matched "${SELECTORS.messageRow}" but every one is inert: this is the previous conversation, still on screen while the new one loads`
            : `nothing matched "${SELECTORS.messageRow}": either the page never rendered this conversation, or the selector has drifted`)
        );
      }

      setStatus('Loading full history (walking to top)...');
      interceptorActive = true;
      await scrollToTop();

      setStatus('Capturing (walking down)...');
      await captureWalkingDown();

      const h = transcript.filter(t => t.role === 'Human').length;
      log('LOG', `📊 Captured ${transcript.length} messages (${h} human, ${transcript.length - h} ${AGENT.toLowerCase()})`);
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

    const rawTitle = document.title.replace(/ - Google Gemini$/, '').trim();
    const filename = `${getConversationTitle()}.md`;
    downloadBlob(buildMarkdown(rawTitle || `Conversation with ${AGENT}`), filename, 'text/markdown');

    setStatus(`✅ Downloaded: ${filename}`, 'success');

    log('LOG', 'Export complete.');
  }

  function cleanup() {
    navigator.clipboard.writeText = originalWriteText;
    navigator.clipboard.write = originalWrite;
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
