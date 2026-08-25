#!/usr/bin/env python
"""
model.py — per-schema definition catalogues, candidates for rsc/schema/model.json.
Output: tmp/cache/model/{schema}/v{N}.json for each versioned schema (flat, not mirroring
rsc/schema/{pipeline}/{schema}/). rsc/schema/model.json is hand-curated from these.

`model` is a NOUN: the catalogues. A bare invocation shows their current state and
writes nothing (so there is no `status` verb — the bare noun IS the status). Only
the `sync` verb writes: it brings tmp/cache/model into agreement with the schemas, and
re-running is silence (L1) — which is what naming it `sync` promises.

Usage:
    corpus-yoga model         # status: which catalogues exist under tmp/cache/model/
    corpus-yoga model sync    # (re-)generate every catalogue to agree with the schemas
"""

import re
import sys
from pathlib import Path

from frontier import verdicts
from gen_model_candidate import generate
from model_curation import (documented, rejected, edge_queue,
                            orphan_entries, coverage_gaps, unrecorded_collisions,
                            shared_name_candidates, identity_violations, emptiness_violations,
                            worksheet_rows, accept_shared_name, reject_shared_name)

SELF = 'src/main/model/model.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ — modules both tiers import
from declared_parser import command_parser  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[2]
SCHEMA_DIR = REPO_ROOT / 'rsc' / 'schema'
OUT_DIR    = REPO_ROOT / 'tmp' / 'cache' / 'model'


def _sorted_versions(schema_dir: Path) -> list[Path]:
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )


def _catalogues() -> list[tuple[str, Path]]:
    """(family, schema-version file) for every versioned schema — the inventory
    that `project` writes and `status` reports, so the two can never disagree."""
    out = []
    for pipeline_dir in sorted(SCHEMA_DIR.iterdir()):
        if not pipeline_dir.is_dir() or pipeline_dir.name.startswith('_'):
            continue
        for schema_dir in sorted(pipeline_dir.iterdir()):
            if not schema_dir.is_dir():
                continue
            for version in _sorted_versions(schema_dir):
                out.append((schema_dir.name, version))
    return out


def curation_report() -> None:
    """Both disposal loops, in numbers (issue #19; model_curation.py): the step
    that used to read 'update model.json if needed' now reports whether it IS
    needed. Loop 1 is leisurely (name collisions awaiting a model_join edge or a
    shrug — no gate pressure); loop 2 blocks (shared-type edges obligate
    model.json, gated per type by `corpus-yoga test run`'s check_model_obligations)."""
    queue = edge_queue()
    orphans = orphan_entries()
    gaps = coverage_gaps()
    print(f'rsc/schema/model.json — {len(documented())} documented · {len(rejected())} rejected · '
          f'{len(queue)} shared type(s) obligated by model_join and undisposed · '
          f'{len(orphans)} documented but ungrounded · {len(gaps)} documented incompletely'
          + (' (GATES)' if queue or orphans or gaps else ''))
    for names, rows in sorted(queue.items(), key=lambda kv: sorted(kv[0])):
        print(f'  ✗ {"/".join(sorted(names))} — model_join row(s) {", ".join(map(str, rows))}: '
              'document in rsc/schema/model.json | reject into rsc/schema/model_rejected.txt')
    for name in orphans:
        print(f'  ✗ {name} — documented with no grounding model_join edge: '
              'curate the asserting edge, or retire the entry')
    for name, fams in sorted(gaps.items()):
        print(f'  ✗ {name} — occurrences omit data famil(y/ies) its edge asserts: '
              f'{", ".join(fams)} — add the occurrence(s)')
    shared = unrecorded_collisions()
    if shared:
        print(f'FAIL: rsc/schema/model_join.csv - {len(shared)} definition name(s) '
              'appear in two or more schema families with no row recording whether '
              'the definitions are one shared type or mere namesakes')
        print('    → record a verdict by adding one model_join.csv row per name, its '
              'relationship column choosing a kind from rsc/schema/model_join_kinds.csv '
              '(identical / subset / name_collision / ...); machine-checked proposals '
              'sit ready to paste in tmp/cache/model/shared_name_candidates.csv')
    else:
        print('rsc/schema/model_join.csv — every cross-family shared name disposed')
    for line, kind, cells in identity_violations():
        print(f'FAIL: model_join row {line} ({kind}) no longer holds at latest - {cells}')
        print('    → a one-sided mint falsified the edge: re-judge its relationship kind '
              '(rsc/schema/model_join_kinds.csv) or restore the identity in the schemas')
    corpus_roots = (REPO_ROOT / 'data' / 'input' / 'claude' / 'chat' / 'browser-API',
                    REPO_ROOT / 'tmp' / 'cache' / 'chat-exports')
    if any(r.is_dir() for r in corpus_roots):
        for line, kind, cell, datum in emptiness_violations(REPO_ROOT):
            print(f'FAIL: model_join row {line} ({kind}) falsified by the corpus - '
                  f'{cell} carries a value in {datum}')
            print('    → the always-null note is stale: re-judge the edge '
                  '(rsc/schema/model_join_kinds.csv names the kinds)')
    else:
        print('model_join emptiness edges: unchecked — no browser-API or chat-exports '
              'corpus in this room')


def sync() -> None:
    """The verb: bring tmp/cache/model into agreement with the schemas by (re-)generating
    every catalogue. Idempotent (L1) — the ONLY path here that writes."""
    for name, schema in _catalogues():
        out_dir = OUT_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        target, text = out_dir / schema.name, generate(name, schema)
        if target.exists() and target.read_text() == text:
            continue   # content-keyed (#494): current means no write
        target.write_text(text)
        print(f'  ✓ tmp/cache/model/{name}/{schema.name}')
    render_collision_worksheet()
    # the report is status's (bare corpus-yoga model): a sync writes, and the run's
    # tail probes status right after it - reporting here too would state every
    # finding twice in one section (#494)


def render_collision_worksheet() -> None:
    """The leisurely queue as a worksheet (machine proposes, human disposes):
    one pre-filled model_join row per undisposed SHARED NAME, the relationship
    cell blank except where structural equality makes 'identical' a mechanical
    proposal. Rendered by sync beside the catalogues it derives from."""
    import csv, io
    rows = shared_name_candidates()
    path = OUT_DIR / 'shared_name_candidates.csv'
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=['name', 'families',
                                             'conversations_path', 'session_path',
                                             'apiConversation_path', 'mcp_path',
                                             'relationship', 'note'])
    writer.writeheader()
    writer.writerows(rows)
    if path.exists() and path.read_bytes() == buf.getvalue().encode():
        return   # content-keyed (#494): current means no write and nothing said
    path.write_bytes(buf.getvalue().encode())   # bytes: csv's CRLF must survive the compare
    proposed = sum(1 for r in rows if r['relationship'])
    print(f'  ✓ tmp/cache/model/shared_name_candidates.csv ({len(rows)} undisposed, '
          f'{proposed} with a machine proposal)')


def status() -> None:
    """The bare-noun default: show current state, write nothing. Reports which
    catalogues tmp/cache/model/ already holds and which a `project` would still
    mint, then the model.json disposal queue."""
    present, missing = [], []
    for name, schema in _catalogues():
        (present if (OUT_DIR / name / schema.name).exists() else missing).append(
            f'{name}/{schema.name}')
    total = len(present) + len(missing)
    print(f'tmp/cache/model: {len(present)}/{total} catalogues present')
    if missing:
        # the count is the fact; 52 derivable filenames were the mumble - the
        # names are exactly the schema tree's, and sync mints them all
        print(f'{len(missing)} catalogue(s) not yet projected - corpus-yoga model sync mints them')
    frontier_report()
    curation_report()


def frontier_report() -> None:
    """Each family's frontier verdict (#373): the newest datum in this room
    against the family's latest schema version, read from the validation logs
    the pipelines' own validate steps wrote - no new validation. Stated here so
    the usr gate's corpus tail says it: quiet lines when the frontier is
    modelled, a FAIL atom when it is not, counted by the stage table."""
    for v in verdicts():
        family = f"{v['pipeline']}/{v['family']}"
        if v['kind'] == 'no-datum':
            print(f"frontier: {family} - no datum in this room (latest {v['latest']})")
        elif v['kind'] == 'green' and v['scope'] == 'all':
            print(f"frontier: {family} - recency unknown for its {v['count']} datum(s); "
                  f"all modelled by latest {v['latest']}")
        elif v['kind'] == 'green':
            print(f"frontier: {family} - newest datum ({v['subject']}) modelled by latest {v['latest']}")
        else:
            said = ('newest datum' if v['scope'] == 'newest'
                    else f"datum (recency unknown - all {v['count']} checked)")
            print(f"FAIL: frontier: {family} - {said} ({v['subject']}) holds no passing "
                  f"{v['latest']}.log - corpus-yoga pipeline run {v['pipeline']} refreshes the evidence; "
                  f"red thereafter means a schema version is owed (rsc/schema/WORKFLOW.md) - {v['log']}")


def list_candidates() -> None:
    """The disposal queue with its three feeders (#470), each row naming its
    disposal: undisposed shared names (the worksheet, re-rendered fresh),
    falsified identity edges, and corpus-falsified emptiness edges."""
    render_collision_worksheet()
    rows = shared_name_candidates()
    for row in rows:
        verdict = (f"accept adopts '{row['relationship']}'" if row['relationship']
                   else 'no machine proposal - judge the kind by hand')
        print(f"  {row['name']} ({row['families']}) - {verdict}")
    print(f'{len(rows)} undisposed shared name(s) - dispose each: '
          'corpus-yoga model accept <name> | corpus-yoga model reject <name> --reason <why> '
          '(--all disposes the queue as read)')
    for line, kind, cells in identity_violations():
        print(f'  falsified identity edge: row {line} ({kind}) - {cells} - re-judge '
              'the kind in rsc/schema/model_join.csv or restore the identity')
    corpus_roots = (REPO_ROOT / 'data' / 'input' / 'claude' / 'chat' / 'browser-API',
                    REPO_ROOT / 'tmp' / 'cache' / 'chat-exports')
    if any(r.is_dir() for r in corpus_roots):
        for line, kind, cell, datum in emptiness_violations(REPO_ROOT):
            print(f'  falsified emptiness edge: row {line} ({kind}) - {cell} carries '
                  f'a value in {datum} - re-judge the kind in rsc/schema/model_join.csv')
    else:
        print('  emptiness edges: unchecked - no browser-API or chat-exports corpus in this room')


def _disposal_rows(parser, args):
    """The queue the disposal acts on: the worksheet as read, refused when it is
    absent or moved since rendering - re-render with corpus-yoga model sync."""
    rows = worksheet_rows()
    if rows is None:
        parser.error('the worksheet is absent or stale against the schemas - '
                     'run corpus-yoga model sync, read it, then dispose')
        raise SystemExit(2)   # parser.error exits; stated for the type checker
    if args.all:
        return rows
    match = [r for r in rows if r['name'] == args.name]
    if not match:
        parser.error(f'{args.name} is not in the queue - corpus-yoga model list-candidates names it')
    return match


def main():
    parser = command_parser('model')  # generated from the declaration (#476)
    args = parser.parse_args()
    if args.verb == 'sync':
        sync()
    elif args.verb == 'list-candidates':
        list_candidates()
    elif args.verb in ('accept', 'reject'):
        # exactly one of --all and a name: the flag disposes the queue as read,
        # the positional disposes one shared name (the indexing precedent)
        if args.all == bool(args.name):
            parser.error(f'{args.verb} takes a <name> or --all, not both and not neither')
        from datetime import date
        today = date.today().isoformat()
        for row in _disposal_rows(parser, args):
            if args.verb == 'accept':
                print(accept_shared_name(row, today))
            else:
                print(reject_shared_name(row, args.reason, today))
        render_collision_worksheet()
    else:
        # bare → status (read-only); only the verbs above write
        status()


if __name__ == '__main__':
    main()
