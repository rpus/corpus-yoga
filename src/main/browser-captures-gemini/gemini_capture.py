#!/usr/bin/env python
"""
Capture markdown for Gemini conversations via Safari.

Two modes:
  --recapture   Re-capture all ID directories already in ext/browser-captures-gemini/.
                Safe for routine use — only updates known conversations.
  --discover    Navigate to gemini.google.com/app, find all conversation IDs,
                and capture all of them.

Always overwrites previous captures — conversations grow over time.

Requires Safari open, focused, and logged into gemini.google.com throughout.
Called by gemini_capture.sh — do not invoke directly.

Usage:
    python gemini_capture.py --recapture  --browser-captures ext/browser-captures-gemini
    python gemini_capture.py --discover   --browser-captures ext/browser-captures-gemini
"""

import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'browser-captures'))
from safari_utils import (  # type: ignore[import-not-found]
    safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    wait_for_log, collect_md_and_log,
    PAGE_LOAD_WAIT,
)

REPO_DIR  = Path(__file__).resolve().parents[3]
JS_SCRIPT = Path(__file__).parent / 'browser-chat-capture-gemini.js'

DISCOVER_JS = """\
(function () {
  const seen = new Set(), r = [];
  document.querySelectorAll('a[href*="/app/"]').forEach(function (a) {
    const id = a.pathname.split('/').pop();
    if (id && /^[0-9a-f]{8,}$/.test(id) && !seen.has(id)) { seen.add(id); r.push(id); }
  });
  return r.join('\\n');
})()"""
EXPORT_TIMEOUT = 900
SETTLE_PAUSE   = 2


def capture_one(conv_id, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    safari_navigate(f'https://gemini.google.com/app/{conv_id}')
    time.sleep(PAGE_LOAD_WAIT)

    start = time.time()
    safari_run_js_file(JS_SCRIPT)
    print(f'  script injected, waiting...')

    log = wait_for_log(start, EXPORT_TIMEOUT)
    if log is None:
        print(f'  TIMEOUT after {EXPORT_TIMEOUT}s — skipping')
        return

    time.sleep(SETTLE_PAUSE)
    files = collect_md_and_log(start, out_dir)
    print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')


def ids_from_filesystem(captures_root):
    print(f'scanning {captures_root}')
    ids = [d.name for d in sorted(captures_root.iterdir()) if d.is_dir()]
    print(f'found {len(ids)} existing captures')
    return ids


def ids_from_safari():
    safari_focus()
    print('navigating to gemini.google.com/app')
    safari_navigate('https://gemini.google.com/app')
    time.sleep(PAGE_LOAD_WAIT)
    print('loading all conversations...')
    prev = 0
    while True:
        safari_eval_js(
            '(function(){'
            'var a=document.querySelector(\'a[href*="/app/"]\');'
            'while(a){var s=getComputedStyle(a);'
            'if((s.overflowY==="scroll"||s.overflowY==="auto")&&a.scrollHeight>a.clientHeight)'
            '{a.scrollTo(0,a.scrollHeight);return;}'
            'a=a.parentElement;}'
            'window.scrollTo(0,document.body.scrollHeight);'
            '})()'
        )
        time.sleep(2)
        count = safari_eval_js("document.querySelectorAll('a[href*=\"/app/\"]').length")
        try:
            count = int(count)
        except (ValueError, TypeError):
            break
        if count == prev:
            break
        prev = count
    print('extracting conversation IDs')
    raw = safari_eval_js(DISCOVER_JS)
    ids = [i for i in raw.splitlines() if i]
    print(f'found {len(ids)} conversations')
    return ids


def run(ids, captures_root, label):
    if not ids:
        print(f'{label}: nothing to do')
        return
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    print(f'capturing {len(ids)} conversations')
    safari_focus()
    for i, conv_id in enumerate(ids):
        print(f'[{i+1}/{len(ids)}] {conv_id}')
        capture_one(conv_id, captures_root / conv_id)
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True,
                    help='Path to ext/browser-captures-gemini/')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--recapture', action='store_true',
                   help='Re-capture all ID directories already present')
    g.add_argument('--discover', action='store_true',
                   help='Discover from Gemini app page and capture all conversations')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f'Error: {JS_SCRIPT} not found', file=sys.stderr)
        raise SystemExit(1)

    captures_root = Path(args.browser_captures).resolve()
    captures_root.mkdir(parents=True, exist_ok=True)

    if args.recapture:
        run(ids_from_filesystem(captures_root), captures_root, 'recapture')
    else:
        run(ids_from_safari(), captures_root, 'discover')


if __name__ == '__main__':
    main()
