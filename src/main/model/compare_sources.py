#!/usr/bin/env python
"""
compare_sources.py — Cross-source consistency check. The same conversation projected from the
live API capture (apiConversation) and from the bulk export should render to identical markdown.
Both sides are now directories of per-conversation files -- the captures, and the json/ pieces
project_markdown atomised out of the bulk array -- so this just projects each and pairs by uuid.
A second verifier alongside compare_markdown.py (which checks projection vs the legacy scrape).

Both formats carry the full edit/regeneration tree; project() reduces each to the active path
(via the explicit current_leaf_message_uuid for a capture, the inferred latest-created leaf for the
export). Identical output across two independent formats validates the projection and the model_join
correspondence end-to-end.

A difference is expected only from temporal drift -- the two snapshots are taken at different
times, so one conversation may simply be longer. A *conflict* at a shared turn signals a
projection bug (e.g. dead branches leaking in). Use --diff to tell which.

Usage:
  src/run_python_script.sh src/main/model/compare_sources.py \
    --browser-captures ext/browser-captures/claude \
    --bulk-export ext/chat-exports/<batch> [--diff]

Exit status is non-zero iff any conversation present in both sources differs.
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, project, find_api_json, render


def api_by_uuid(captures_dir):
    out, names = {}, {}
    for sub in sorted(p for p in Path(captures_dir).iterdir() if p.is_dir()):
        api = find_api_json(sub)
        if api is not None:
            out[api['uuid']] = render(project(api))
            names[api['uuid']] = api.get('name', '')
    return out, names


def bulk_by_uuid(batch_dir):
    """The bulk side, read from the per-conversation json/ pieces project_markdown atomised out of
    the array (gen/chat-exports/<batch>/json/) -- the 24 MB array itself is never re-read here."""
    json_dir = REPO / 'gen' / 'chat-exports' / Path(batch_dir).name / 'json'
    if not json_dir.is_dir():
        sys.exit(f"no atomised json/ at {json_dir}; "
                 f"run project_markdown.py --bulk-export {batch_dir} first")
    out, names = {}, {}
    for f in sorted(json_dir.glob('*.json')):
        c = json.loads(f.read_text())
        out[c['uuid']] = render(project(c))
        names[c['uuid']] = c.get('name', '')
    return out, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True, help='dir of <uuid>/ capture folders')
    ap.add_argument('--bulk-export', required=True, help='a bulk-export batch dir (reads its atomised json/ pieces)')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    api, api_names = api_by_uuid(args.browser_captures)
    bulk, bulk_names = bulk_by_uuid(args.bulk_export)
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

    api_only = sorted(set(api) - set(bulk))
    bulk_only = sorted(set(bulk) - set(api))
    print(f"shared {len(shared)}: {identical} identical, {differ} differ "
          f"| api-only {len(api_only)}, bulk-only {len(bulk_only)}")
    for u in api_only:
        print(f"  api-only {u}: {api_names.get(u, '')!r} (captured; not in this export)")
    for u in bulk_only:
        print(f"  bulk-only {u}: {bulk_names.get(u, '')!r} (in the export; no capture of it here)")
    return 1 if differ else 0


if __name__ == '__main__':
    sys.exit(main())
