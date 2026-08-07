#!/usr/bin/env python
"""
supersede.py — do later bulk exports SUPERSEDE earlier ones?

A bulk export is a synchronised snapshot of FOUR components: conversations,
memories, projects, users — licensed here as FIVE, because a conversation
carries two different kinds of content: its messages (append-only atoms) and
its summary (a per-snapshot oracle reading, checked as its own component).
The same unprejudiced supersession processing is applied to each — no
component is assumed append-only, mutable, or static; whether an earlier
batch's data survives into the later one is an empirical finding per
component per batch pair, and the deletability verdict is simply their
conjunction.

The uniform model: each component atomises to {unit key: set of atoms}, and a
unit is superseded iff its atoms are a subset of its later self's. Atoms are
the format's content identities — uuid'd immutable constituents where the
format provides them; where it doesn't, canonical values for bounded fields
and fingerprints only for unbounded content:

  conversations  unit = conversation uuid;  atoms = message uuids
                 (read from the RAW atomised json/ pieces — format-agnostic,
                 so an old batch's schema vintage is irrelevant)
  summaries      unit = conversation uuid;  atom = fingerprint of the summary
                 (a per-snapshot oracle READING — nondeterministically emitted —
                 so only the IDENTICAL summary covers it; message coverage
                 says nothing about it, hence its own component)
  memories       unit = account uuid;       atoms = (field, canonical value)
  projects       unit = project uuid;       atoms = (doc uuid, content fingerprint)
                 per doc, plus a fingerprint of the prompt/name/description
  users          unit = user uuid;          atoms = canonical user object

Envelope timestamps (created_at/updated_at) are excluded throughout:
supersession claims retained DATA, not byte equality of snapshots.

The verdict SHOWS ITS WORKING (user specification, 2026-07-08): a batch is
deletable iff every atom it holds survives somewhere durable that is KEPT,
and each batch's report names the evidence per component — the WITNESSES
(every later batch whose verified ⊑ covers it: a licence conditional on that
witness's own retention; diachronic appending is checked per pair, never
assumed) and the unconditional DEPOSITS that outlive every batch: for
memories, the byte-identical copy in data/output/memories; for summaries, every
reading held verbatim in data/output/markdown/claude/chat/summaries
(summaries.py). A component with no witness and no deposit is
unique data — a loud WARN, and the batch is not deletable until it is
deposited or superseded. Verdicts describe what exists
NOW: re-run after any deletion, since deleting a witness expires the
licences it carried.

A tmp/cache/ batch dir whose data/input/ datum is gone is an ORPHANED DERIVATION — the
shadow of a batch already disposed of, not a batch. Its archive copies are
complete, so left in it would keep passing for a live batch (and witnessing
others) indefinitely; it is excluded from the comparison and WARNed with its
rm remedy — datum-scoped tmp/cache/ dirs die with their data/input/ datum (README), but
deletion stays deliberate, so the machinery names the orphan rather than
resurrecting it.

Usage:
  src/run_python_script.sh src/main/pipeline/chat-exports/supersede.py \
    [--chat-exports-cache tmp/cache/chat-exports] [--bulk-exports data/input/claude/chat/bulk-export] \
    [--memories-output data/output/memories] \
    [--summaries-output data/output/markdown/claude/chat/summaries] \
    [--browser-api <browser-API root; no default — when given, also compares the latest batch against live captures, informationally>]

Requires the batches' atomised json/ (written by the chat-exports pipeline);
memories/projects/users are read from the batch's tmp/cache/ archive copies (written
by archive_components.py; data/input/ raw fallback for cache dirs predating that step).
Exit 0 iff every earlier batch is covered (witnessed or deposited).
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/pipeline/chat-exports/supersede.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
from argparse_help import enrich  # noqa: E402

REPO = REPO_ROOT


def _rel(p: Path) -> Path:
    """Repo-relative spelling for printed paths — symmetric and brief whatever
    spelling the caller passed (run.sh passes cache absolute, input relative), and
    runnable from the repo root, where every printed command runs."""
    try:
        return p.relative_to(REPO)
    except ValueError:
        return p


def batch_time(name):
    m = re.search(r'-(\d{10})-[0-9a-f]+-batch', name)
    if m:
        return datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', name)
    if m:
        return datetime(*map(int, m.groups()), tzinfo=timezone.utc)
    return None


def _canon(value):
    """Canonical form of a bounded JSON value — atoms carry the VALUE itself
    (set equality is then exact string equality, no fingerprint, no collision
    caveat). Right for the bounded components: memory fields, user objects."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _fp(value):
    """Content fingerprint of an arbitrary JSON value — for atoms over
    UNBOUNDED content (project doc bodies), where carrying the value itself
    would make atom sets as large as the corpus."""
    return hashlib.sha256(_canon(value).encode()).hexdigest()[:16]


# ── component atomisers: batch -> {unit key: (display name, set of atoms)} ────

def units_conversations(gen_dir, ext_dir):
    units = {}
    for f in sorted((gen_dir / 'json').glob('*.json')):
        c = json.load(f.open())
        u = c.get('uuid')
        if u:
            units[u] = (f.stem, {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')})
    return units


def units_summaries(gen_dir, ext_dir):
    """Each conversation's summary as ONE fingerprinted atom. The summary is a
    per-snapshot oracle READING (a nondeterministic emission: the same transcript has
    been observed to re-read differently — №99, capture vs export, identical
    updated_at), so a later batch covers it only by carrying the IDENTICAL summary;
    a divergent later summary is a NEW reading, not a superseding one, and deleting
    the earlier batch would destroy a reading that exists nowhere else. Message
    coverage says nothing about this — hence its own component in the licence.
    Empty summaries contribute no unit (nothing to lose, nothing to orphan)."""
    units = {}
    for f in sorted((gen_dir / 'json').glob('*.json')):
        c = json.load(f.open())
        u, s = c.get('uuid'), c.get('summary')
        if u and s:
            units[u] = (f.stem, {_fp(s)})
    return units


def _component_path(gen_dir, ext_dir, *rel):
    """Prefer the batch's tmp/cache/ archive copy (written by archive_components.py);
    fall back to the raw data/input/ batch dir for cache dirs predating the archive step."""
    archived = gen_dir.joinpath(*rel)
    return archived if archived.exists() else ext_dir / rel[-1]


def units_memories(gen_dir, ext_dir):
    path = _component_path(gen_dir, ext_dir, 'memories', 'memories.json')
    if not path.exists():
        return {}
    units = {}
    for m in json.loads(path.read_text()):
        key = m.get('account_uuid', '?')
        atoms = {(field, _canon(value)) for field, value in m.items() if field != 'account_uuid'}
        units[key] = ('memories', atoms)
    return units


def units_projects(gen_dir, ext_dir):
    units = {}
    proj_dir = _component_path(gen_dir, ext_dir, 'projects')
    for f in sorted(proj_dir.glob('*.json')) if proj_dir.is_dir() else []:
        p = json.loads(f.read_text())
        # uniform (kind, constituent id, fingerprint) atoms; the envelope has exactly
        # one constituent, so its id slot is empty
        atoms = {('doc', d['uuid'], _fp([d.get('filename'), d.get('content')]))
                 for d in p.get('docs', [])}
        atoms.add(('meta', '', _fp([p.get('name'), p.get('description'), p.get('prompt_template')])))
        units[p.get('uuid', f.stem)] = (p.get('name', f.stem), atoms)
    return units


def units_users(gen_dir, ext_dir):
    path = _component_path(gen_dir, ext_dir, 'users', 'users.json')
    if not path.exists():
        return {}
    return {u.get('uuid', '?'): (u.get('full_name', 'user'), {_canon(u)})
            for u in json.loads(path.read_text())}


COMPONENTS = [('conversations', units_conversations),
              ('summaries', units_summaries),
              ('memories', units_memories),
              ('projects', units_projects),
              ('users', units_users)]


def compare_component(earlier, latest):
    """Classify each earlier unit against the latest; return (subset, details)."""
    subset = 0
    details = []
    for key, (name, atoms) in sorted(earlier.items()):
        if key not in latest:
            details.append(f'    ORPHANED {name} ({key}): {len(atoms)} atom(s) absent from latest')
        elif atoms <= latest[key][1]:
            subset += 1
        else:
            missing = len(atoms - latest[key][1])
            details.append(f'    DIVERGENT {name} ({key}): {missing} atom(s) present here, missing in latest')
    return subset, details


def covers(earlier, later) -> bool:
    """True iff every earlier unit's atoms survive in the later corpus —
    the verified ⊑ of one component between two specific batches."""
    return all(key in later and atoms <= later[key][1]
               for key, (_n, atoms) in earlier.items())


def _short(batch_name: str) -> str:
    """The batch's own 8-hex segment, for compact witness citations."""
    m = re.search(r'-([0-9a-f]{8})-batch', batch_name)
    return m.group(1) if m else batch_name


def deposit_witness(gen_dir, ext_dir, lib_dir: Path):
    """The deposit file byte-identical to this batch's memory state, or None —
    the unconditional licence: a copy that outlives every batch."""
    path = _component_path(gen_dir, ext_dir, 'memories', 'memories.json')
    if not path.exists() or not lib_dir.is_dir():
        return None
    text = path.read_text()
    for f in sorted(lib_dir.glob('*.json')):
        if f.read_text() == text:
            return f
    return None


def summaries_deposit_fps(lib_dir: Path):
    """Fingerprints of every deposited summary reading (summaries.py's
    verbatim <ts>.md / browser-capture.md files) — the summaries component's
    unconditional licence: deposits outlive every batch and every capture refresh."""
    fps = set()
    if lib_dir.is_dir():
        for f in lib_dir.glob('*/*.md'):
            if f.name != 'index.md':
                fps.add(_fp(f.read_text()))
    return fps


# ── captures cross-check (conversations only: that is what the capture source has) ─

def load_captures(captures_dir):
    """{conversation uuid: set of message uuids} (+ names) from <uuid>/<uuid>.json captures."""
    convs, names = {}, {}
    for d in sorted(captures_dir.iterdir()):
        j = d / f'{d.name}.json' if d.is_dir() else None
        if j and j.exists():
            c = json.load(j.open())
            u = c.get('uuid', d.name)
            convs[u] = {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')}
            names[u] = c.get('name', '')
    return convs, names


def compare_vs_captures(latest, latest_convs, latest_names, captures_dir):
    """Directional per-conversation supersession between the latest bulk export and the
    live-capture corpus (the data frontier). Informational: capture-ahead is the normal
    post-snapshot direction; capture-stale names conversations to recapture in place;
    an anomaly (unique messages on BOTH sides) wants investigation."""
    caps, cap_names = load_captures(captures_dir)
    shared = set(latest_convs) & set(caps)
    in_sync = ahead = 0
    stale, anomalies = [], []
    for u in sorted(shared):
        b, c = latest_convs[u][1], caps[u]
        if b == c:
            in_sync += 1
        elif b < c:
            ahead += 1
        elif c < b:
            stale.append(u)
        else:
            anomalies.append(u)
    export_only = sorted(set(latest_convs) - set(caps))
    capture_only = sorted(set(caps) - set(latest_convs))
    # The summary is a plain line: every noteworthy class below emits its own
    # per-item WARN, so a WARN prefix here would always double-count one fact:
    # one ghost conversation would be reported as two.
    print(f'{latest.name} vs captures: {len(shared)} shared — {in_sync} in-sync, '
          f'{ahead} capture-ahead, {len(stale)} capture-stale, {len(anomalies)} anomalies; '
          f'{len(export_only)} export-only (no local capture), '
          f'{len(capture_only)} capture-only (absent from this export)')
    # Each mismatched conversation is its own WARN: line — pipeline.sh
    # gathers WARN: (and "→ run:") lines verbatim into its tail, so the NAMES
    # reach the part of the log that gets read, not just the counts.
    def _blank(stem: str) -> bool:
        """No content in any message (e.g. a stray blank send): the export's
        record is complete however long it is kept — nothing worth capturing."""
        try:
            c = json.loads((latest / 'json' / f'{stem}.json').read_text())
        except (OSError, ValueError):
            return False
        msgs = c.get('chat_messages', [])
        return all(not m.get('text') and not m.get('content') for m in msgs)

    for u in export_only:
        if not latest_convs[u][1] or _blank(latest_convs[u][0]):
            print(f'  export-only {latest_convs[u][0]} ({u}): blank (no message content) — '
                  'the export holds its complete record; nothing to capture')
            continue
        print(f'WARN: export-only {latest_convs[u][0]} ({u}) — no capture of it here; to capture:')
        print(f'    → run: yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in capture_only:
        print(f'  capture-only {cap_names.get(u, "")!r} ({u}): in the captures, absent from this export')
    for u in stale:
        print(f'WARN: capture-stale {cap_names.get(u, "")!r} ({u}) — the export holds '
              f'{len(latest_convs[u][1] - caps[u])} message(s) the capture lacks — to recapture:')
        print(f'    → run: yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in anomalies:
        print(f'WARN: anomaly {cap_names.get(u, "")!r} ({u}) — unique messages on both sides — investigate')


def _gather(root, ext_root):
    """The cheap shared prefix: the export dirs present (time-ordered), the orphaned
    derivations among them, and any unparseable names. Directory reads only — no json,
    no atomising — so bare `supersede` stays a fast read-only status."""
    batches = sorted((d for d in root.glob('data-*') if (d / 'json').is_dir()),
                     key=lambda d: (batch_time(d.name) or datetime.min.replace(tzinfo=timezone.utc)))
    unparseable = [d.name for d in batches if batch_time(d.name) is None]
    orphans = [d for d in batches if not (ext_root / d.name).is_dir()]
    live = [d for d in batches if (ext_root / d.name).is_dir()]
    return live, orphans, unparseable


def _warn_unparseable(unparseable):
    for n in unparseable:
        print(f'warning: cannot parse a time from batch name {n} — ordering may be wrong', file=sys.stderr)


def status(root, ext_root):
    """Bare noun → read-only inventory: which export dirs exist, in what order, which
    are orphaned derivations. Computes no coverage and writes nothing — `supersede
    check` does the comparison."""
    live, orphans, unparseable = _gather(root, ext_root)
    _warn_unparseable(unparseable)
    for d in orphans:
        print(f'WARN: orphaned derivation {d.name} — no {_rel(ext_root / d.name)} beside it, '
              f'excluded from any comparison; dispose the shadow with: rm -r {_rel(d)}')
    if not live:
        print(f'supersede: no export dirs with atomised json/ under {_rel(root)}')
        return 0
    print(f'supersede: {len(live)} export dir(s) with atomised json/ under {_rel(root)}; '
          f'latest {live[-1].name}'
          + (f'; {len(orphans)} orphaned derivation(s) excluded' if orphans else ''))
    print('  run `yoga supersede check` to compute supersession')
    return 0


def check(args):
    """The `check` verb: the full supersession comparison — for each earlier export dir,
    whether every component is witnessed by a later batch or deposited, with the working
    shown. Reads every batch's atoms; writes nothing. Exit 0 iff all covered."""
    root = Path(args.chat_exports_cache)
    ext_root = Path(args.bulk_exports)
    batches, orphans, unparseable = _gather(root, ext_root)
    _warn_unparseable(unparseable)
    # Orphaned derivations (docstring): a tmp/cache/ dir with no data/input/ datum beside it must
    # not feed the comparison — its archive copies are complete, so it would keep passing
    # for a live batch (and witnessing others) after the data it derives from was disposed.
    for d in orphans:
        print(f'WARN: orphaned derivation {d.name} — no {_rel(ext_root / d.name)} beside it; '
              'excluded from comparison. If the export was deliberately deleted, this '
              'shadow is the disposal\'s one remaining step:')
        print(f'    → run: rm -r {_rel(d)}')

    if not batches:
        print(f'no export dirs with atomised json/ under {root} — nothing to compare')
        return 0

    latest = batches[-1]
    all_units = {b.name: {name: fn(b, ext_root / b.name) for name, fn in COMPONENTS}
                 for b in batches}
    latest_units = all_units[latest.name]
    if len(batches) < 2:
        print(f'1 export dir with atomised json/ under {root} — no earlier exports to compare')
    else:
        print(f'latest: {latest.name} — ' + ', '.join(
            f'{len(latest_units[name])} {name}' for name, _ in COMPONENTS))

    # Show the working: a batch is deletable iff every atom it holds survives
    # somewhere durable that is KEPT — for each component, name the WITNESSES
    # (later batches whose verified ⊑ covers it: a licence conditional on the
    # witness's own retention) and the unconditional DEPOSITS (memories: the
    # byte-identical data/output/memories copy; summaries: every reading held verbatim
    # in the summaries output — deposits outlive every batch). Witnessed-by-later
    # relies on nothing but per-pair verified subset — diachronic appending is
    # checked, never assumed. Verdicts describe what exists NOW: re-run after
    # any deletion, since deleting a witness expires the licences it carried.
    covered_all = True
    deletable = []
    summ_fps = summaries_deposit_fps(Path(args.summaries_output))
    for i, b in enumerate(batches[:-1]):
        ext_dir = ext_root / b.name
        working, uncovered = [], []
        for name, _ in COMPONENTS:
            earlier = all_units[b.name][name]
            witnesses = [w.name for w in batches[i + 1:]
                         if covers(earlier, all_units[w.name][name])]
            dep = deposit_witness(b, ext_dir, Path(args.memories_output)) if name == 'memories' else None
            if dep is not None:
                working.append(f'    memories: copied — {dep} is byte-identical (unconditional)'
                               + (f'; also ⊑ {", ".join(_short(w) for w in witnesses)}' if witnesses else ''))
            elif (name == 'summaries' and earlier
                  and all(atoms <= summ_fps for _k, (_n2, atoms) in earlier.items())):
                working.append(f'    summaries: deposited — every reading held verbatim in '
                               f'{args.summaries_output} (unconditional)'
                               + (f'; also ⊑ {", ".join(_short(w) for w in witnesses)}' if witnesses else ''))
            elif witnesses:
                working.append(f'    {name} ⊑ {", ".join(_short(w) for w in witnesses)}'
                               ' (while one of these is kept)')
            else:
                uncovered.append(name)
                _, details = compare_component(earlier, latest_units[name])
                working += details
        if not uncovered:
            print(f'{b.name} → deletable; the working:')
            deletable.append(b)
        else:
            print(f'WARN: {b.name} holds unique {", ".join(uncovered)} data — '
                  'found in no later export and no deposit')
        for line in working:
            print(line)
        covered_all = covered_all and not uncovered

    if len(batches) >= 2:
        # The deletability verdict — a computed CONCLUSION, which as a severity is
        # INFO (it acts on nothing, gates nothing); the tail hoists FAIL/WARN/INFO
        # atoms alike.
        print('INFO: ' + (
            f'keep {latest.name}; every earlier export dir is covered — '
            'batch-witnessed licences hold while their witnesses are kept, deposit '
            'licences unconditionally; re-run after any deletion'
            if covered_all else
            'some earlier export dir(s) hold data found nowhere else (WARN lines above) — '
            'not deletable until deposited or superseded'))
        # Each licensed disposal is its own INFO atom — the reason plus one
        # runnable command over BOTH dirs (the export and its tmp/cache/ derivation
        # together, so no orphaned-derivation WARN ever follows a licensed deletion).
        for b in deletable:
            print(f'  INFO: {b.name} deletable — every atom witnessed or deposited; to dispose:')
            print(f'    → run: rm -r {_rel(ext_root / b.name)} {_rel(b)}')
    sufficient = covered_all

    if args.browser_api and Path(args.browser_api).is_dir():
        compare_vs_captures(latest, latest_units['conversations'], None, Path(args.browser_api))

    return 0 if sufficient else 1


DEFAULT_CACHE = 'tmp/cache/chat-exports'
DEFAULT_BULK = 'data/input/claude/chat/bulk-export'


def main():
    ap = argparse.ArgumentParser(
        description='Do later bulk exports SUPERSEDE earlier ones? Bare shows the '
                    'export-dir inventory; `check` computes coverage. Writes nothing.')
    sub = ap.add_subparsers(dest='verb')
    # The flags live on `check`, the verb that uses them — so the pipeline's
    # `… check --browser-api …` parses, and the top-level --help stays short (just the
    # {check} block) rather than unfurling five flags and tripping the one-screen gate.
    # Bare status reads the standard dirs by default; overriding them is a check concern.
    cp = sub.add_parser('check')
    cp.add_argument('--chat-exports-cache', metavar='DIR', default=DEFAULT_CACHE)
    cp.add_argument('--bulk-exports', metavar='DIR', default=DEFAULT_BULK)
    cp.add_argument('--browser-api', metavar='DIR', default=None)
    cp.add_argument('--memories-output', metavar='DIR', default='data/output/memories')
    cp.add_argument('--summaries-output', metavar='DIR', default='data/output/markdown/claude/chat/summaries')
    enrich(ap, 'supersede')
    args = ap.parse_args()
    if args.verb is None:
        return status(Path(DEFAULT_CACHE), Path(DEFAULT_BULK))
    return check(args)


if __name__ == '__main__':
    sys.exit(main())
