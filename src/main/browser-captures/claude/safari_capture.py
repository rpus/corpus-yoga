#!/usr/bin/env python
"""
Capture markdown and live API JSON for Claude.ai conversations via Safari.

Two modes:
  (no args)     Navigate to claude.ai/recents, find all conversation UUIDs,
                and capture all of them. Always overwrites previous captures.
  --uuid <uuid> Capture a single conversation by UUID (used by the macOS Shortcut).

Requires Safari open, focused, and logged into claude.ai throughout.
Called by safari_capture.sh — do not invoke directly.

Usage:
    python safari_capture.py                 --browser-captures ext/browser-captures/claude
    python safari_capture.py --uuid <uuid>   --browser-captures ext/browser-captures/claude
"""

import argparse, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safari_utils import (  # type: ignore[import-not-found]
    safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    safari_fetch_api_json, wait_for_log, collect_md_and_log,
    PAGE_LOAD_WAIT,
)

REPO_DIR  = Path(__file__).resolve().parents[4]
JS_SCRIPT = Path(__file__).parent / 'browser-chat-capture.js'

DISCOVER_JS = """\
(function () {
  const seen = new Set(), r = [];
  document.querySelectorAll('a[href*="/chat/"]').forEach(function (a) {
    const u = a.pathname.split('/').pop();
    if (u && !seen.has(u)) { seen.add(u); r.push(u); }
  });
  return r.join('\\n');
})()"""
EXPORT_TIMEOUT    = 900
SETTLE_PAUSE      = 2


def fetch_json(uuid, out_dir, files):
    json_file = safari_fetch_api_json(uuid)
    if json_file:
        new_md = [f for f in files if f.endswith('.md')]
        stem = Path(new_md[0]).stem if new_md else uuid
        shutil.move(str(json_file), out_dir / f'{stem}.json')
        files.append(f'{stem}.json')
    else:
        print(f'  warning: API JSON fetch timed out')


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


def uuids_from_safari():
    safari_focus()
    print('navigating to claude.ai/recents')
    safari_navigate('https://claude.ai/recents')
    time.sleep(PAGE_LOAD_WAIT)
    print('loading all conversations...')
    prev = 0
    while True:
        safari_eval_js(
            '(function(){'
            'var a=document.querySelector(\'a[href*="/chat/"]\');'
            'while(a){var s=getComputedStyle(a);'
            'if((s.overflowY==="scroll"||s.overflowY==="auto")&&a.scrollHeight>a.clientHeight)'
            '{a.scrollTo(0,a.scrollHeight);return;}'
            'a=a.parentElement;}'
            'window.scrollTo(0,document.body.scrollHeight);'
            '})()'
        )
        time.sleep(2)
        count = safari_eval_js("document.querySelectorAll('a[href*=\"/chat/\"]').length")
        try:
            count = int(count)
        except (ValueError, TypeError):
            break
        if count == prev:
            break
        prev = count
    print('extracting UUIDs')
    raw = safari_eval_js(DISCOVER_JS)
    uuids = [u for u in raw.splitlines() if u]
    print(f'found {len(uuids)} conversations')
    return uuids


def capture_all(uuids, captures_root, label):
    if not uuids:
        print(f'{label}: nothing to do')
        return
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    print(f'capturing {len(uuids)} conversations')
    safari_focus()
    for i, uuid in enumerate(uuids):
        print(f'[{i+1}/{len(uuids)}] {uuid}')
        safari_navigate(f'https://claude.ai/chat/{uuid}')
        time.sleep(PAGE_LOAD_WAIT)
        result = capture_one(captures_root / uuid)
        if result is not None:
            start, files = result
            fetch_json(uuid, captures_root / uuid, files)
            print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures',
                    default=str(REPO_DIR / 'ext' / 'browser-captures' / 'claude'),
                    help='Path to ext/browser-captures/claude/ (default: repo-relative)')
    ap.add_argument('--uuid', metavar='UUID',
                    help='Capture a single conversation; default is discover mode')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f'Error: {JS_SCRIPT} not found', file=sys.stderr)
        raise SystemExit(1)

    captures_root = Path(args.browser_captures).resolve()
    captures_root.mkdir(parents=True, exist_ok=True)

    if args.uuid:
        safari_focus()
        print(f'--- capture started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
        print(f'[1/1] {args.uuid}')
        out_dir = captures_root / args.uuid
        result = capture_one(out_dir)
        if result is not None:
            start, files = result
            fetch_json(args.uuid, out_dir, files)
            print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')
        print(f'--- capture finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    else:
        capture_all(uuids_from_safari(), captures_root, 'discover')


if __name__ == '__main__':
    main()
