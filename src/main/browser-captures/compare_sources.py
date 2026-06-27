#!/usr/bin/env python
"""
compare_sources.py — Cross-source consistency check. The same conversation projected from the
live API capture (apiConversation) and from the bulk export (conversations.json) should render
to identical markdown. Pairs by uuid. A second verifier alongside compare_markdown.py (which
checks projection vs the legacy scrape).

Both formats carry the full edit/regeneration tree; project()/project_bulk() each reduce to the
active path (explicit current_leaf_message_uuid vs the latest-created message as leaf). Identical
output across two independent formats validates the projection and the model_join correspondence
end-to-end.

A difference is expected only from temporal drift -- the two snapshots are taken at different
times, so one conversation may simply be longer. A *conflict* at a shared turn signals a
projection bug (e.g. dead branches leaking in). Use --diff to tell which.

Usage:
  src/run_python_script.sh src/main/browser-captures/compare_sources.py \
    --browser-captures ext/browser-captures/claude \
    --bulk-export ext/chat-exports/<batch>/conversations.json [--diff]

Exit status is non-zero iff any conversation present in both sources differs.
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

from project_markdown import project, project_bulk, find_api_json, render


def api_by_uuid(captures_dir):
    out = {}
    for sub in sorted(p for p in Path(captures_dir).iterdir() if p.is_dir()):
        api = find_api_json(sub)
        if api is not None:
            out[api['uuid']] = render(project(api))
    return out


def bulk_by_uuid(conversations_json):
    return {c['uuid']: render(project_bulk(c))
            for c in json.loads(Path(conversations_json).read_text())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True, help='dir of <uuid>/ capture folders')
    ap.add_argument('--bulk-export', required=True, help='a bulk-export conversations.json')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    api = api_by_uuid(args.browser_captures)
    bulk = bulk_by_uuid(args.bulk_export)
    shared = set(api) & set(bulk)

    identical = differ = 0
    for u in sorted(shared):
        if api[u] == bulk[u]:
            identical += 1
            continue
        differ += 1
        if args.diff:
            print(f"===== {u} =====")
            print('\n'.join(difflib.unified_diff(api[u].splitlines(), bulk[u].splitlines(),
                                                  'api', 'bulk', lineterm='')))

    print(f"shared {len(shared)}: {identical} identical, {differ} differ "
          f"| api-only {len(set(api) - set(bulk))}, bulk-only {len(set(bulk) - set(api))}")
    return 1 if differ else 0


if __name__ == '__main__':
    sys.exit(main())
