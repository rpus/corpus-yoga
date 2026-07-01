function setupExporter() {
  const AGENT = 'Claude';
  const originalWriteText = navigator.clipboard.writeText;
  const capturedResponses = [];
  const humanMessages = [];
  let currentCapture = null;
  let interceptorActive = false;
  let humanTotal = 0;
  let agentTotal = 0;

  // Liveness/progress flag the driver (safari_capture.py) polls — so it detects start, progress,
  // completion, and errors directly instead of waiting out a download timeout.
  window.__scrape = { started: true, captured: 0, done: false, error: null };

  const _consoleLogs = [];
  const log = (level, ...args) => {
    const msg = args.map(a => (a instanceof Error) ? a.stack : typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ');
    _consoleLogs.push(`[${new Date().toISOString()}] [${level}] ${msg}`);
    console[level.toLowerCase()](...args);
  };

  // DOM Selectors - easily modifiable if Claude's UI changes
  const SELECTORS = {
    copyButton: 'button[data-testid="action-bar-copy"]',
    feedbackButton: 'button[aria-label="Give positive feedback"]',
    messageContainer: '.mb-1.group',
    agentContainer: '.group',
    messageText: 'p.whitespace-pre-wrap',
    responseText: 'p.font-claude-response-body',
  };

  const DELAYS = {
    copy: 100,
    startup: 1000,
    cleanup: 3000,
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

  function readFromDOM(btn) {
    const msgContainer = btn.closest(SELECTORS.messageContainer) || btn.closest(SELECTORS.agentContainer);
    if (!msgContainer) return null;
    const els = msgContainer.querySelectorAll(SELECTORS.responseText);
    if (els.length) return Array.from(els).map(e => e.innerText.trim()).filter(t => t).join('\n\n');
    return null;
  }

  function describeButton(btn) {
    const msgContainer = btn.closest(SELECTORS.messageContainer) || btn.closest(SELECTORS.agentContainer);
    if (!msgContainer) return '(no container)';

    // Plain text message
    const p = msgContainer.querySelector(SELECTORS.messageText);
    if (p) return '"' + p.innerText.trim().substring(0, 60).replace(/\n/g, ' / ') + '"';

    // Image attachments
    const imgs = msgContainer.querySelectorAll('img[alt]');
    if (imgs.length) {
      const names = Array.from(imgs).map(i => i.alt).filter(a => a).join(', ');
      return '[image: ' + names.substring(0, 60) + ']';
    }

    // File/code attachments and tool results: strip sr-only text then use innerText
    const srOnly = msgContainer.querySelector('.sr-only');
    const t = (srOnly ? msgContainer.innerText.replace(srOnly.innerText, '') : msgContainer.innerText)
                .trim().substring(0, 60).replace(/\n/g, ' / ');
    return t.length > 5 ? '"' + t + '"' : '(no text)';
  }

  // Intercept clipboard writes and route to the active capture target
  navigator.clipboard.writeText = function(text) {
    if (interceptorActive && text && currentCapture) {
      currentCapture.push({ content: text });
      updateStatus();
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
    const h = humanTotal ? `${humanMessages.length}/${humanTotal}` : humanMessages.length;
    const a = agentTotal ? `${capturedResponses.length}/${agentTotal}` : capturedResponses.length;
    window.__scrape.captured = humanMessages.length + capturedResponses.length;
    setStatus(`Human: ${h} | ${AGENT}: ${a}`);
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

  // agentOnly=true  → Claude responses  (action bar contains a feedback button)
  // agentOnly=false → human messages    (no feedback button in the action bar)
  function getCopyButtons(agentOnly) {
    return Array.from(document.querySelectorAll(SELECTORS.copyButton))
      .filter(btn => !!actionBarOf(btn).querySelector(SELECTORS.feedbackButton) === agentOnly);
  }

  async function triggerCopyButtons(buttons, label) {
    let captured = 0;
    let placeholders = 0;
    for (let i = 0; i < buttons.length; i++) {
      const countBefore = currentCapture.length;
      try {
        if (buttons[i].offsetParent !== null) {
          buttons[i].scrollIntoView({ behavior: 'instant', block: 'nearest' });
          buttons[i].click();
          await delay(DELAYS.copy);
          if (currentCapture.length > countBefore) {
            captured++;
            log('LOG', `📋 Captured ${label} message ${captured}/${buttons.length}`);
          } else {
            const domText = readFromDOM(buttons[i]);
            if (domText) {
              captured++;
              log('LOG', `📋 Captured ${label} message ${captured}/${buttons.length} (from DOM)`);
              currentCapture.push({ content: domText });
            } else {
              const desc = describeButton(buttons[i]);
              log('LOG', `📎 Button ${i + 1}/${buttons.length} — no text capture, placeholder inserted — ${desc}`);
              currentCapture.push({ content: `[no capture — ${desc}]` });
              placeholders++;
            }
            updateStatus();
          }
        } else {
          log('WARN', `⏭️ Skipped button ${i + 1}/${buttons.length} — not visible`);
        }
      } catch (error) {
        log('WARN', `Failed on button ${i + 1}:`, error);
      }
    }
    return { captured, placeholders };
  }

  function buildMarkdown(title) {
    let markdown = `# ${title}\n\n<${window.location.href}>\n\n`;
    const maxLength = Math.max(humanMessages.length, capturedResponses.length);

    for (let i = 0; i < maxLength; i++) {
      if (i < humanMessages.length && humanMessages[i].content) {
        markdown += `## Human (${i+1})\n\n${humanMessages[i].content}\n\n---\n\n`;
      }
      if (i < capturedResponses.length && capturedResponses[i].content) {
        markdown += `## ${AGENT} (${i+1})\n\n${capturedResponses[i].content}\n\n---\n\n`;
      }
    }

    return markdown;
  }

  async function startExport() {
    try {
      const humanButtons = getCopyButtons(false);
      const agentButtons = getCopyButtons(true);

      if (humanButtons.length === 0 && agentButtons.length === 0) {
        const rawCopy     = document.querySelectorAll(SELECTORS.copyButton).length;
        const rawFeedback = document.querySelectorAll(SELECTORS.feedbackButton).length;
        throw new Error(
          rawCopy === 0
            ? `No copy buttons in DOM (feedback: ${rawFeedback}). Page not loaded, wrong page, or copy-button selector "${SELECTORS.copyButton}" drifted.`
            : `Found ${rawCopy} copy button(s) and ${rawFeedback} feedback button(s), but paired 0 into messages — the pairing logic drifted, not the buttons.`
        );
      }

      humanTotal = humanButtons.length;
      agentTotal = agentButtons.length;
      log('LOG', `🔍 Copy buttons found: ${humanButtons.length} human, ${agentButtons.length} ${AGENT.toLowerCase()}`);
      if (Math.abs(humanButtons.length - agentButtons.length) > 1) {
        log('WARN', `⚠️ Unbalanced counts (${humanButtons.length} human vs ${agentButtons.length} ${AGENT.toLowerCase()}) — possible misclassification from selector drift`);
      }

      // Phase 1: Human messages
      setStatus('Copying human messages...');
      currentCapture = humanMessages;
      interceptorActive = true;
      const { captured: humanCaptured, placeholders: humanPlaceholders } = await triggerCopyButtons(humanButtons, 'human');
      log('LOG', `📊 Phase 1: ${humanCaptured} captured, ${humanPlaceholders} placeholders — ${humanCaptured + humanPlaceholders}/${humanButtons.length} human messages accounted for`);

      // Phase 2: Agent responses
      setStatus(`Copying ${AGENT} responses...`);
      currentCapture = capturedResponses;
      const { captured: agentCaptured, placeholders: agentPlaceholders } = await triggerCopyButtons(agentButtons, AGENT.toLowerCase());
      log('LOG', `📊 Phase 2: ${agentCaptured} captured, ${agentPlaceholders} placeholders — ${agentCaptured + agentPlaceholders}/${agentButtons.length} ${AGENT.toLowerCase()} responses accounted for`);

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

    if (humanMessages.length === 0 && capturedResponses.length === 0) {
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
