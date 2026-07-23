#!/usr/bin/env python
"""
prune_twin_deposits.py — ONE-SHOT repair for the pre-fix twin deposits.
SELF-RETIRING: delete this script once both rooms' detectors read zero
(the `yoga summaries` status and every sync WARN on twins until then);
history keeps it reachable.

Before the nearest-earlier fix, accumulate_summaries deduped against the
batch sequence only, which disposal shrinks: each batch disposal re-stamped
its readings under the next surviving batch, and the old loop — checking
filename existence only — deposited them again, byte-identical under the
new stamp. Forensics (PR #21, 2026-07-23): three write events (Jul 10
genuine, Jul 11 + Jul 12 twin layers, one per disposal), 196 twins across
99 of 100 folders in the shared store, dormant since.

The criterion is accumulate_summaries.twins_of — the ONE authority, shared
with the standing detector: a deposit byte-identical to its nearest earlier
sibling is one the fixed loop would never write. Removing exactly those
makes the store what correct machinery would have produced; every genuine
reading survives under its earliest stamp, and a genuine A→B→A recurrence
is not a twin and is kept.

Deleting deposits is an L4 exception, decided explicitly by the rooms on
PR #21 — never by default, which is why --apply is a separate deliberate
act. Bare invocation is a READ-ONLY census (detect/report precedes purge).
index.md files are untouched here: the next `yoga summaries sync` rebuilds
each from its folder listing.

Usage:
  src/run_python_script.sh src/main/chat-exports/prune_twin_deposits.py \\
      [--summaries-output output/markdown/claude/chat/summaries] [--apply]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO

from accumulate_summaries import twins_of  # noqa: E402 — the one criterion authority


def main():
    ap = argparse.ArgumentParser(
        description='One-shot repair: remove bug-minted twin deposits (byte-identical '
                    'to their nearest earlier sibling). Bare is a read-only census; '
                    '--apply removes. Self-retiring: delete once both rooms read zero.')
    ap.add_argument('--summaries-output', metavar='DIR',
                    default=str(REPO / 'output' / 'markdown' / 'claude' / 'chat' / 'summaries'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    root = Path(args.summaries_output)
    if not root.is_dir():
        print(f'no summaries store at {root} — nothing to census')
        return 0

    total = 0
    plan: list[Path] = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        deps = [p for p in folder.glob('*.md')
                if p.name not in ('index.md', 'browser-capture.md')]
        total += len(deps)
        t = twins_of(folder)
        if t:
            plan.extend(t)
            print(f'  {folder.name}: {len(t)} twin(s) of {len(deps)} '
                  f'({", ".join(p.stem for p in t)})')

    print(f'{total} deposit(s); {len(plan)} twin(s) to remove, {total - len(plan)} kept '
          '(every reading survives under its earliest stamp)')
    if not plan:
        print('store is clean — this script has served; delete it (history keeps it)')
        return 0
    if not args.apply:
        print('census only — pass --apply to remove; afterwards `yoga summaries sync` '
              'rebuilds each index.md and the detector should read zero')
        return 0
    for p in plan:
        p.unlink()
    print(f'removed {len(plan)} twin(s); run `yoga summaries sync` to rebuild index.md '
          'files, then confirm the detector reads zero')
    return 0


if __name__ == '__main__':
    sys.exit(main())
