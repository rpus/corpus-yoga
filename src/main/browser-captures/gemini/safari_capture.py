#!/usr/bin/env python
"""
Capture markdown for Gemini conversations via Safari.

Two modes:
  (no args)   Navigate to gemini.google.com/app, find all conversation IDs,
              and capture all of them. Always overwrites previous captures.
  --id <id>   Capture a single conversation by ID (used by the macOS Shortcut).

Requires Safari open, focused, and logged into gemini.google.com throughout.
Called by safari_capture.sh — do not invoke directly.

Usage:
    python safari_capture.py              --browser-captures ext/browser-captures/gemini
    python safari_capture.py --id <id>   --browser-captures ext/browser-captures/gemini
"""

import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safari_utils import (  # type: ignore[import-not-found]
    safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    wait_for_log, collect_md_and_log,
    PAGE_LOAD_WAIT,
)

REPO_DIR  = Path(__file__).resolve().parents[4]
JS_SCRIPT = Path(__file__).parent / 'browser-chat-capture.js'

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


def capture_one(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    safari_run_js_file(JS_SCRIPT)
    print(f'  script injected, waiting...')
    log = wait_for_log(start, EXPORT_TIMEOUT)
    if log is None:
        print(f'  TIMEOUT after {EXPORT_TIMEOUT}s — skipping')
        return None
    time.sleep(SETTLE_PAUSE)
    return start, collect_md_and_log(start, out_dir)


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
    ids = [u for u in raw.splitlines() if u]
    print(f'found {len(ids)} conversations')
    return ids


def capture_all(ids, captures_root, label):
    if not ids:
        print(f'{label}: nothing to do')
        return
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    print(f'capturing {len(ids)} conversations')
    safari_focus()
    for i, conv_id in enumerate(ids):
        print(f'[{i+1}/{len(ids)}] {conv_id}')
        safari_navigate(f'https://gemini.google.com/app/{conv_id}')
        time.sleep(PAGE_LOAD_WAIT)
        result = capture_one(captures_root / conv_id)
        if result is not None:
            start, files = result
            print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', required=True, choices=['claude', 'gemini'])
    ap.add_argument('--browser-captures', default=None,
                    help='Path to ext/browser-captures/<agent>/ (default: repo-relative)')
    ap.add_argument('--id', metavar='ID',
                    help='Capture a single conversation; default is discover mode')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f'Error: {JS_SCRIPT} not found', file=sys.stderr)
        raise SystemExit(1)

    captures_root = Path(args.browser_captures or REPO_DIR / 'ext' / 'browser-captures' / args.agent).resolve()
    captures_root.mkdir(parents=True, exist_ok=True)

    if args.id:
        safari_focus()
        print(f'--- capture started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
        print(f'[1/1] {args.id}')
        out_dir = captures_root / args.id
        result = capture_one(out_dir)
        if result is not None:
            start, files = result
            print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')
        print(f'--- capture finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    else:
        capture_all(ids_from_safari(), captures_root, 'discover')


if __name__ == '__main__':
    main()
