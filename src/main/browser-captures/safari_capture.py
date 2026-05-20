#!/usr/bin/env python
"""
Capture markdown and live API JSON for Claude.ai conversations via Safari.

Two modes:
  --recapture   Re-capture all UUID directories already in ext/browser-captures/.
                Safe for routine use — only updates known conversations.
  --discover    Navigate to claude.ai/recents, find all conversation UUIDs,
                and capture all of them.

Always overwrites previous captures — conversations grow over time.

Requires Safari open, focused, and logged into claude.ai throughout.
Called by safari_capture.sh — do not invoke directly.

Usage:
    python safari_capture.py --recapture  --browser-captures ext/browser-captures
    python safari_capture.py --discover   --browser-captures ext/browser-captures
"""

import argparse, shutil, sys, time
from pathlib import Path

from safari_utils import (
    safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    safari_fetch_api_json, wait_for_log, collect_md_and_log,
    PAGE_LOAD_WAIT,
)

REPO_DIR  = Path(__file__).resolve().parents[3]
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


def capture_one(uuid, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    safari_navigate(f'https://claude.ai/chat/{uuid}')
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

    json_file = safari_fetch_api_json(uuid)
    if json_file:
        md_files = list(out_dir.glob('*.md'))
        stem = md_files[0].stem if md_files else uuid
        shutil.move(str(json_file), out_dir / f'{stem}.json')
        files.append(f'{stem}.json')
    else:
        print(f'  warning: API JSON fetch timed out')

    print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')


def uuids_from_filesystem(captures_root):
    print(f'scanning {captures_root}')
    uuids = [d.name for d in sorted(captures_root.iterdir()) if d.is_dir()]
    print(f'found {len(uuids)} existing captures')
    return uuids


def uuids_from_safari():
    safari_focus()
    print('navigating to claude.ai/recents')
    safari_navigate('https://claude.ai/recents')
    time.sleep(PAGE_LOAD_WAIT)
    print('loading all conversations...')
    prev = 0
    while True:
        safari_eval_js('window.scrollTo(0, document.body.scrollHeight)')
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


def run(uuids, captures_root, label):
    if not uuids:
        print(f'{label}: nothing to do')
        return
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    print(f'capturing {len(uuids)} conversations')
    safari_focus()
    for i, uuid in enumerate(uuids):
        print(f'[{i+1}/{len(uuids)}] {uuid}')
        capture_one(uuid, captures_root / uuid)
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True,
                    help='Path to ext/browser-captures/')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--recapture', action='store_true',
                   help='Re-capture all UUID directories already present')
    g.add_argument('--discover', action='store_true',
                   help='Discover from Recents and capture new conversations only')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f'Error: {JS_SCRIPT} not found', file=sys.stderr)
        raise SystemExit(1)

    captures_root = Path(args.browser_captures).resolve()
    captures_root.mkdir(parents=True, exist_ok=True)

    if args.recapture:
        run(uuids_from_filesystem(captures_root), captures_root, 'recapture')
    else:
        run(uuids_from_safari(), captures_root, 'discover')


if __name__ == '__main__':
    main()
