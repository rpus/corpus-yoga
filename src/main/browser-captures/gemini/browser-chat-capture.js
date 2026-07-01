function setupExporter() {
  const AGENT = 'Gemini';
  const originalWriteText = navigator.clipboard.writeText;
  const originalWrite = navigator.clipboard.write.bind(navigator.clipboard);
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

  // DOM Selectors — Gemini uses custom Angular elements as stable anchors
  const SELECTORS = {
    humanElement: 'user-query',
    agentElement: 'model-response',
    humanCopyButton: 'button[aria-label="Copy prompt"]',
    agentCopyButton: 'button[aria-label="Copy"]',
  };

  const DELAYS = {
    copy: 300,
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
      currentCapture.push({ content: text });
      updateStatus();
    }
  };

  // Gemini response copy buttons use clipboard.write() with a ClipboardItem asynchronously,
  // which the browser blocks (NotAllowedError) outside a user-gesture context. We intercept
  // the call before it reaches the browser, extract text/plain from the ClipboardItem, and
  // suppress the actual write so Gemini's code doesn't throw.
  navigator.clipboard.write = function (items) {
    if (interceptorActive && currentCapture) {
      Promise.all(items.map(item =>
        item.types.includes('text/plain')
          ? item.getType('text/plain').then(blob => blob.text())
          : Promise.resolve(null)
      )).then(texts => {
        const text = texts.find(t => t);
        if (text) { currentCapture.push({ content: text }); updateStatus(); }
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
    const h = humanTotal ? `${humanMessages.length}/${humanTotal}` : humanMessages.length;
    const a = agentTotal ? `${capturedResponses.length}/${agentTotal}` : capturedResponses.length;
    window.__scrape.captured = humanMessages.length + capturedResponses.length;
    setStatus(`Human: ${h} | ${AGENT}: ${a}`);
  }

  function getCopyButtonsFromElements(elements, ariaLabel) {
    const buttons = [];
    elements.forEach(el => {
      const btn = el.querySelector(`button[aria-label="${ariaLabel}"]`);
      if (btn) buttons.push(btn);
    });
    return buttons;
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
            log('WARN', `⚠️ Button ${i + 1}/${buttons.length} — no clipboard capture`);
            currentCapture.push({ content: `[no capture — ${label} message ${i + 1}]` });
            placeholders++;
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
      const humanElements = [...document.querySelectorAll(SELECTORS.humanElement)];
      const agentElements = [...document.querySelectorAll(SELECTORS.agentElement)];
      const humanButtons = getCopyButtonsFromElements(humanElements, 'Copy prompt');
      const agentButtons = getCopyButtonsFromElements(agentElements, 'Copy');

      if (humanButtons.length === 0 && agentButtons.length === 0) {
        throw new Error('No copy buttons found!');
      }

      humanTotal = humanButtons.length;
      agentTotal = agentButtons.length;
      log('LOG', `🔍 Copy buttons found: ${humanButtons.length} human, ${agentButtons.length} ${AGENT.toLowerCase()}`);

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
