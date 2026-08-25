#!/usr/bin/env python
"""
compare_sources.py — Cross-source consistency check. The same conversation projected from the
live API capture (apiConversation) and from the bulk export should render to identical markdown.
Both sides are now directories of per-conversation files -- the captures, and the json/ pieces
project_markdown atomised out of the bulk array -- so this just projects each and pairs by uuid.

Both formats carry the full edit/regeneration tree; project() reduces each to the active path
(via the explicit current_leaf_message_uuid for a capture, the inferred latest-created leaf for the
export). Identical output across two independent formats validates the projection and the model_join
correspondence end-to-end.

A TRANSCRIPT difference has three readings, told apart by the turn sequences (#535, the
append-only invariant the dev gate's cross_sources check held): the export is a PREFIX of
the capture (the conversation progressed after the snapshot - lawful, "appended-to"); the
capture is a prefix of the EXPORT (a stale capture - FAIL, with the recapture prescribed);
or the two diverge inside the shared prefix (a projection defect or corruption - FAIL).
Use --diff to see the text. The SUMMARY (v3's
optional field) is compared separately and reported as its own category: the backend regenerates
it between snapshots, so two snapshots of an identical transcript can legitimately carry
different prose summaries -- that is summary drift, not a transcript difference, and it never
sets the exit status.

Usage:
  src/run_python_script.sh src/main/model/compare_sources.py \
    --browser-api data/input/claude/chat/browser-API \
    --bulk-export data/input/claude/chat/bulk-export/<batch> [--diff]

Exit status is non-zero iff any shared conversation is capture-stale or divergent.
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

SELF = 'src/main/model/compare_sources.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main/ on the path
from markdown_projection import REPO, project, find_api_json, render, turn_seq


def _transcript_and_summary(conv):
    """(render-without-summary, summary) for one source conversation. The TRANSCRIPT
    (title, url, turns) is the byte-compared contract; the summary is a mutable field
    the backend regenerates between snapshots, compared separately. (Frontmatter never
    appears here: these are in-memory renders — the provenance dressing belongs to
    write_markdown's files, not to render() itself.)"""
    lean = project(conv)
    summary = lean.pop('summary', '')
    return render(lean), summary


def api_by_uuid(captures_dir):
    out, names, summaries = {}, {}, {}
    for sub in sorted(p for p in Path(captures_dir).iterdir() if p.is_dir()):
        api = find_api_json(sub)
        if api is not None:
            out[api['uuid']], summaries[api['uuid']] = _transcript_and_summary(api)
            names[api['uuid']] = api.get('name', '')
    return out, names, summaries


def bulk_by_uuid(batch_dir):
    """The bulk side, read from the per-conversation json/ pieces project_markdown atomised out of
    the array (tmp/cache/chat-exports/<batch>/json/) -- the 24 MB array itself is never re-read here."""
    json_dir = REPO / 'tmp' / 'cache' / 'chat-exports' / Path(batch_dir).name / 'json'
    if not json_dir.is_dir():
        sys.exit(f"no atomised json/ at {json_dir}; "
                 f"run project_markdown.py --bulk-export {batch_dir} first")
    out, names, summaries = {}, {}, {}
    for f in sorted(json_dir.glob('*.json')):
        c = json.loads(f.read_text())
        out[c['uuid']], summaries[c['uuid']] = _transcript_and_summary(c)
        names[c['uuid']] = c.get('name', '')
    return out, names, summaries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-api', required=True, help='dir of <uuid>/ capture folders')
    ap.add_argument('--bulk-export', required=True, help='a bulk-export batch dir (reads its atomised json/ pieces)')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    api, api_names, api_summ = api_by_uuid(args.browser_api)
    bulk, bulk_names, bulk_summ = bulk_by_uuid(args.bulk_export)
    shared = set(api) & set(bulk)

    identical = appended = summary_drift = 0
    stale, divergent = [], []
    for u in sorted(shared):
        if api_summ[u] != bulk_summ[u]:
            summary_drift += 1
        if api[u] == bulk[u]:
            identical += 1
            continue
        a, b = turn_seq(api[u]), turn_seq(bulk[u])
        if len(b) < len(a) and a[:len(b)] == b:
            appended += 1          # the export is a prefix of the capture: it progressed
        elif len(b) > len(a) and b[:len(a)] == a:
            stale.append(u)        # the capture is a prefix of the export: recapture
        else:
            divergent.append(u)
        if args.diff:
            print(f"===== {u} =====")
            print('\n'.join(difflib.unified_diff(api[u].splitlines(), bulk[u].splitlines(),
                                                  'api', 'bulk', lineterm='')))

    api_only = sorted(set(api) - set(bulk))
    bulk_only = sorted(set(bulk) - set(api))
    print(f"shared {len(shared)}: {identical} transcripts identical, {appended} appended-to, "
          f"{len(stale)} capture-stale, {len(divergent)} divergent, "
          f"{summary_drift} summary-drift (snapshots' summaries differ; never gates) "
          f"| api-only {len(api_only)}, bulk-only {len(bulk_only)}")
    for u in stale:
        print(f"FAIL: capture-stale {api_names.get(u, '')!r} ({u}) - the export extends the capture; to recapture:")
        print(f"    → run: corpus-yoga browser capture --provider claude --id {u}"
              f"  # first front https://claude.ai/chat/{u} in Safari (logged in)")
    for u in divergent:
        print(f"FAIL: divergent {api_names.get(u, '')!r} ({u}) - the two sources disagree inside "
              f"their shared turns: a projection defect, corruption, or a post-export edit; "
              f"investigate with --diff")
    for u in api_only:
        print(f"  api-only {u}: {api_names.get(u, '')!r} (captured; not in this export)")
    for u in bulk_only:
        print(f"  bulk-only {u}: {bulk_names.get(u, '')!r} (in the export; no capture of it here)")
    return 1 if (stale or divergent) else 0


if __name__ == '__main__':
    sys.exit(main())
