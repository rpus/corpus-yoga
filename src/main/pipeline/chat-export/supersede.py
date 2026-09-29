#!/usr/bin/env python
"""
supersede.py — do later bulk exports SUPERSEDE earlier ones?

A bulk export is a synchronised snapshot of FOUR components: conversations,
memories, projects, users — licensed here as FIVE, because a conversation
carries two different kinds of content: its messages (append-only atoms) and
its summary (a per-snapshot oracle reading, checked as its own component).
The same unprejudiced supersession processing is applied to each — no
component is assumed append-only, mutable, or static; whether an earlier
export's data survives into the later one is an empirical finding per
component per export pair, and the deletability verdict is simply their
conjunction.

The uniform model: each component atomises to {unit key: set of atoms}, and a
unit is superseded iff its atoms are a subset of its later self's. Atoms are
the format's content identities — uuid'd immutable constituents where the
format provides them; where it doesn't, canonical values for bounded fields
and fingerprints only for unbounded content:

  conversations  unit = conversation uuid;  atoms = message uuids
                 (read from the RAW atomised json/ pieces — format-agnostic,
                 so an old export's schema vintage is irrelevant)
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

The verdict SHOWS ITS WORKING (user specification, 2026-07-08): an export is
deletable iff every atom it holds survives somewhere durable that is KEPT,
and each export's report names the evidence per component — the WITNESSES
(every later export whose verified ⊑ covers it: a licence conditional on that
witness's own retention; diachronic appending is checked per pair, never
assumed) and the unconditional DEPOSITS that outlive every export: for
memories, the byte-identical copy in data/output/memories; for summaries, every
reading held verbatim in data/output/markdown/claude/chat/summaries
(summaries.py). A component with no witness and no deposit is
unique data — a loud WARN, and the export is not deletable until it is
deposited or superseded. Verdicts describe what exists
NOW: re-run after any deletion, since deleting a witness expires the
licences it carried.

A witness counts only while it is kept (#715): the exports are judged latest first, the
latest kept, an earlier one deletable when a KEPT later export or a deposit covers each
of its components, and an export found uncovered kept in its turn, so the verdict
licenses one act over every deletable export at once and no order among them matters.

A tmp/cache/ export dir whose data/input/ datum is gone is an ORPHANED DERIVATION — the
shadow of an export already disposed of, not an export. Its archive copies are
complete, so left in it would keep passing for a live export (and witnessing
others) indefinitely; it is excluded from the comparison and named, and the janitor
removes it - datum-scoped tmp/cache/ dirs die with their data/input/ datum (README).

The verdict is the bare noun's whole act, and its disposal is the janitor (#715):

  corpus-yoga supersede                    # the verdict with its working; writes nothing
  corpus-yoga supersede clean --dry-run    # the verdict, then what it would remove: each deletable
                                           # export with its manifest and its shadow, each orphaned shadow
  corpus-yoga supersede clean --apply      # remove it, then the verdict over what remains

  src/run_python_script.sh src/main/pipeline/chat-export/supersede.py [clean (--dry-run | --apply)] \
    [--api-capture <API-capture root; no default — when given, also compares the latest export against live captures, informationally>]

The roots it reads - tmp/cache/chat-export, data/input/claude/chat/bulk-export, data/output/memories,
data/output/markdown/claude/chat/summaries - are the declaration's, resolved through the tier
contract (src/main/tier.py, #702): no path is passed, so a rehearsal's name rebinds them all.

The chat-export run's tail is the dry run: the verdict, and what a reader's apply would
remove. Requires the exports' atomised json/ (written by the chat-export pipeline);
memories/projects/users are read from the export's tmp/cache/ archive copies (written
by archive_components.py; data/input/ raw fallback for cache dirs predating that step).
The bare noun exits 0 iff every earlier export is covered.
"""
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/pipeline/chat-export/supersede.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main - the tier's shared modules
import tier  # noqa: E402 — the tiers, one home (#702)
import corpus  # noqa: E402 - human, size_of: the store's sizes in one spelling
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
from declared_parser import command_parser  # noqa: E402

REPO = REPO_ROOT


def _rel(p: Path) -> Path:
    """Repo-relative spelling for printed paths — symmetric and brief whatever
    spelling the caller passed (run.sh passes cache absolute, input relative), and
    runnable from the repo root, where every printed command runs."""
    try:
        return p.relative_to(REPO)
    except ValueError:
        return p


VINTAGES_CSV = REPO_ROOT / 'rsc' / 'naming' / 'export_dir_vintages.csv'
CACHE = 'tmp/cache/chat-export'                                   # the exports' shadows: <export>/json/ and the archived components
BULK = 'data/input/claude/chat/bulk-export'                        # the exports and their manifests
MEMORIES_OUTPUT = 'data/output/memories'                           # the memory deposits - a deposit is the unconditional licence
SUMMARIES_OUTPUT = 'data/output/markdown/claude/chat/summaries'   # the summary deposits, likewise


def _vintages():
    """The export-dir naming vintages, as data (rsc/naming/export_dir_vintages.csv),
    file order first-match: each row's pattern carries named groups - epoch and hex8
    where the vintage has them, datetime where it has that."""
    with VINTAGES_CSV.open() as f:
        return [(row['id'], re.compile(row['pattern'])) for row in csv.DictReader(f)]


def _vintage_match(name):
    for vintage_id, pattern in _vintages():
        m = pattern.match(name)
        if m:
            return vintage_id, m.groupdict()
    return None, {}


def export_time(name):
    """The export's ordering instant, per its name's vintage: the EXPLICIT datetime
    where the vintage carries one (v3: the manifest's created_at to the second; v1:
    the name's core), else the epoch (v2's only instant). The epoch stamps an
    instant the manifests leave unnamed - exports order by the instant whose
    meaning the flow states (the maintainer's ruling, 2026-08-24)."""
    _vintage_id, groups = _vintage_match(name)
    if groups.get('datetime'):
        return datetime(*map(int, groups['datetime'].split('-')), tzinfo=timezone.utc)
    if groups.get('epoch'):
        return datetime.fromtimestamp(int(groups['epoch']), tz=timezone.utc)
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


# ── component atomisers: export -> {unit key: (display name, set of atoms)} ────

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
    updated_at), so a later export covers it only by carrying the IDENTICAL summary;
    a divergent later summary is a NEW reading, not a superseding one, and deleting
    the earlier export would destroy a reading that exists nowhere else. Message
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
    """Prefer the export's tmp/cache/ archive copy (written by archive_components.py);
    fall back to the raw data/input/ export dir for cache dirs predating the archive step."""
    archived = gen_dir.joinpath(*rel)
    return archived if archived.exists() else ext_dir / rel[-1]


def units_memories(gen_dir, ext_dir):
    path = _component_path(gen_dir, ext_dir, 'memories', 'memories.json')
    if not path.exists():
        return {}
    units = {}
    data = json.loads(path.read_text())
    # both eras carry one account's object: the pre-manifest export wrapped it in a
    # single-element array, the manifest era ships it bare (memories v2) - one rule reads both
    for m in (data if isinstance(data, list) else [data]):
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
    the verified ⊑ of one component between two specific exports."""
    return all(key in later and atoms <= later[key][1]
               for key, (_n, atoms) in earlier.items())


def _short(export_name: str) -> str:
    """The export's own 8-hex capture token, for compact witness citations - the
    whole name where its vintage carries none (v1)."""
    _vintage_id, groups = _vintage_match(export_name)
    return groups.get('hex8') or export_name


def deposit_witness(gen_dir, ext_dir, lib_dir: Path):
    """The deposit file byte-identical to this export's memory state, or None —
    the unconditional licence: a copy that outlives every export."""
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
    unconditional licence: deposits outlive every export and every capture refresh."""
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
    # Each mismatched conversation is its own FAIL: atom - counted by
    # pipeline.sh's stage table and folded into the run's verdict (#446).
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
        print(f'FAIL: export-only {latest_convs[u][0]} ({u}) - no capture of it here; to capture:')
        print(f'    → run: corpus-yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in capture_only:
        print(f'  capture-only {cap_names.get(u, "")!r} ({u}): in the captures, absent from this export')
    for u in stale:
        print(f'FAIL: capture-stale {cap_names.get(u, "")!r} ({u}) - the export holds '
              f'{len(latest_convs[u][1] - caps[u])} message(s) the capture lacks — to recapture:')
        print(f'    → run: corpus-yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in anomalies:
        print(f'FAIL: anomaly {cap_names.get(u, "")!r} ({u}) - unique messages on both sides - investigate')


def _gather(root, ext_root):
    """The cheap shared prefix: the export dirs present (time-ordered), the orphaned
    derivations among them, and any unparseable names. Directory reads only — no json,
    no atomising — so bare `supersede` stays a fast read-only status."""
    exports = sorted((d for d in root.glob('data-*') if (d / 'json').is_dir()),
                     key=lambda d: (export_time(d.name) or datetime.min.replace(tzinfo=timezone.utc)))
    unparseable = [d.name for d in exports if export_time(d.name) is None]
    orphans = [d for d in exports if not (ext_root / d.name).is_dir()]
    live = [d for d in exports if (ext_root / d.name).is_dir()]
    return live, orphans, unparseable


def _warn_unparseable(unparseable):
    for n in unparseable:
        print(f'FAIL: {n} matches no vintage in rsc/naming/export_dir_vintages.csv - ordering may be wrong', file=sys.stderr)



def verdict(args) -> tuple[list[Path], list[Path], bool]:
    """The supersession verdict - the bare noun's whole act and the janitor's derivation,
    one function (#715): for each earlier export, whether every component survives in a
    KEPT export or a deposit, the working shown. Judged latest first, so that a witness
    counts only while it is kept (the module docstring). Reads every export's atoms;
    writes nothing. Returns (the deletable exports in time order, the orphaned shadows,
    whether every earlier export is covered)."""
    root, ext_root = tier.path(CACHE), tier.path(BULK)
    exports, orphans, unparseable = _gather(root, ext_root)
    _warn_unparseable(unparseable)
    # Orphaned derivations (docstring): a tmp/cache/ dir with no data/input/ datum beside it must
    # not feed the comparison — its archive copies are complete, so it would keep passing
    # for a live export (and witnessing others) after the data it derives from was disposed.
    for d in orphans:
        print(f'FAIL: orphaned derivation {d.name} - no {_rel(ext_root / d.name)} beside it; excluded from '
              'comparison - the shadow of an export disposed of, which corpus-yoga supersede clean removes')
    if not exports:
        print(f'supersede: no export dirs with atomised json/ under {_rel(root)} - nothing to compare')
        return [], orphans, True

    latest = exports[-1]
    all_units = {b.name: {name: fn(b, ext_root / b.name) for name, fn in COMPONENTS}
                 for b in exports}
    latest_units = all_units[latest.name]
    if len(exports) < 2:
        print(f'supersede: 1 export dir with atomised json/ under {_rel(root)} - no earlier export to compare')
    else:
        print(f'latest: {latest.name} — ' + ', '.join(
            f'{len(latest_units[name])} {name}' for name, _ in COMPONENTS))

    # Show the working: an export is deletable iff every atom it holds survives
    # somewhere durable that is KEPT — for each component, name the WITNESSES
    # (kept later exports whose verified ⊑ covers it) and the unconditional DEPOSITS
    # (memories: the byte-identical data/output/memories copy; summaries: every reading
    # held verbatim in the summaries output — deposits outlive every export).
    # Witnessed-by-later relies on nothing but per-pair verified subset — diachronic
    # appending is checked, never assumed. Latest first: the latest is kept, and an
    # export found uncovered is kept and witnesses the ones before it.
    summ_fps = summaries_deposit_fps(tier.path(SUMMARIES_OUTPUT))
    kept = {latest.name}
    judged: dict[str, tuple[list[str], list[str]]] = {}   # export name -> (the working, its uncovered components)
    for i in range(len(exports) - 2, -1, -1):
        b = exports[i]
        ext_dir = ext_root / b.name
        working, uncovered = [], []
        for name, _ in COMPONENTS:
            earlier = all_units[b.name][name]
            witnesses = [w.name for w in exports[i + 1:]
                         if w.name in kept and covers(earlier, all_units[w.name][name])]
            dep = deposit_witness(b, ext_dir, tier.path(MEMORIES_OUTPUT)) if name == 'memories' else None
            if dep is not None:
                working.append(f'    memories: copied — {_rel(dep)} is byte-identical (unconditional)'
                               + (f'; also ⊑ {", ".join(_short(w) for w in witnesses)}' if witnesses else ''))
            elif (name == 'summaries' and earlier
                  and all(atoms <= summ_fps for _k, (_n2, atoms) in earlier.items())):
                working.append(f'    summaries: deposited — every reading held verbatim in '
                               f'{_rel(tier.path(SUMMARIES_OUTPUT))} (unconditional)'
                               + (f'; also ⊑ {", ".join(_short(w) for w in witnesses)}' if witnesses else ''))
            elif witnesses:
                working.append(f'    {name} ⊑ {", ".join(_short(w) for w in witnesses)} (kept)')
            else:
                uncovered.append(name)
                _, details = compare_component(earlier, latest_units[name])
                working += details
        judged[b.name] = (working, uncovered)
        if uncovered:
            kept.add(b.name)

    deletable = []
    for b in exports[:-1]:
        working, uncovered = judged[b.name]
        if not uncovered:
            print(f'{b.name} → deletable; the working:')
            deletable.append(b)
        else:
            print(f'FAIL: {b.name} holds unique {", ".join(uncovered)} data - '
                  'found in no kept export and no deposit')
        for line in working:
            print(line)
    covered_all = all(not judged[b.name][1] for b in exports[:-1])

    if len(exports) >= 2:
        # The deletability verdict - a computed CONCLUSION, stated as untiered
        # prose (#530): it violates no property and licenses one act, the janitor's.
        held = len(exports) - 1 - len(deletable)
        if covered_all:
            print(f'keep {latest.name}; every earlier export is covered by a kept export or a deposit - '
                  f'corpus-yoga supersede clean removes the {len(deletable)} deletable, '
                  'each with its manifest and its shadow')
        else:
            print(f'keep {latest.name} and the {held} earlier export(s) holding data found nowhere else '
                  '(the FAIL lines above); '
                  + (f'corpus-yoga supersede clean removes the {len(deletable)} deletable, each with its manifest and its shadow'
                     if deletable else 'none is deletable'))

    if args.api_capture and Path(args.api_capture).is_dir():
        compare_vs_captures(latest, latest_units['conversations'], None, Path(args.api_capture))
    return deletable, orphans, covered_all


# ── the janitor: one list of entries, one loop, the flag deciding only whether the act runs ──

KINDS = {'export': 'exports', 'manifest': 'manifests', 'shadow': 'shadows',
         'orphaned shadow': 'orphaned shadows'}   # each kind of entry, and its plural
PASSES = 3   # the Finder writes into a directory being emptied; a second pass is the whole remedy


def _remove(path: Path) -> str | None:
    """Remove the entry as it stands at the act. None when it is gone, else why it is not."""
    import shutil
    why = 'still present'
    for _ in range(PASSES):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
        except OSError as e:
            why = (e.strerror or str(e)).lower()
        if not (path.exists() or path.is_symlink()):
            return None
    return why


def _count(n: int, kind: str) -> str:
    return f'{n} {kind if n == 1 else KINDS[kind]}'


def _manifest_of(ext_root: Path, export: Path) -> Path | None:
    """The export's record beside it - manifest-<X>.json for data-<X>/, the pairing the
    stage promotes by (src/main/corpus.py) - or None where the store holds no record."""
    manifest = ext_root / f'manifest-{export.name[len("data-"):]}.json'
    return manifest if manifest.is_file() else None


def entries(deletable: list[Path], orphans: list[Path], ext_root: Path):
    """Everything the janitor acts on, in the order it acts: (kind, name, the line's label,
    the act). The one list both faces walk - the dry run is the apply with the act elided."""
    out = []
    for b in deletable:
        datum = ext_root / b.name
        out.append(('export', _rel(datum).as_posix(),
                    f'export {_rel(datum)} - every atom witnessed by a kept export or deposited: '
                    f'{corpus.human(corpus.size_of(datum))}', lambda datum=datum: _remove(datum)))
        manifest = _manifest_of(ext_root, b)
        if manifest is not None:
            out.append(('manifest', _rel(manifest).as_posix(),
                        f'manifest {_rel(manifest)} - the export\'s record: {corpus.human(corpus.size_of(manifest))}',
                        lambda manifest=manifest: _remove(manifest)))
        out.append(('shadow', _rel(b).as_posix(),
                    f'shadow {_rel(b)} - its derivation in the cache: {corpus.human(corpus.size_of(b))}',
                    lambda b=b: _remove(b)))
    for d in orphans:
        out.append(('orphaned shadow', _rel(d).as_posix(),
                    f'orphaned shadow {_rel(d)} - no export beside it: {corpus.human(corpus.size_of(d))}',
                    lambda d=d: _remove(d)))
    return out


def clean(args, apply: bool) -> int:
    """The verdict first, its working the evidence for the act; then one loop over the one
    list, the flag deciding only whether the act runs after the line. The apply relays the
    verdict re-derived over what remains, beneath its lines and above its own verdict, the
    last line."""
    deletable, orphans, _covered = verdict(args)
    rows = entries(deletable, orphans, tier.path(BULK))
    did = {kind: 0 for kind in KINDS}
    left: list[str] = []
    if rows:
        print()
    for kind, name, label, act in rows:
        if not apply:
            print(f'  would remove {label}')
            did[kind] += 1
            continue
        print(f'  will remove {label}')
        why = act()
        if why is None:
            print('    did')
            did[kind] += 1
        else:
            print(f'    did NOT - {why}')
            left.append(f'{kind}: {name} - {why}')
    counts = ', '.join(_count(did[kind], kind) for kind in KINDS if did[kind]) or 'nothing'
    if not apply:
        print(f'supersede clean: would remove {counts}' + (' (--apply removes them)' if counts != 'nothing' else ''))
        return 0
    # the verdict over what remains is the certified state after the act: evidence, beneath
    # the lines and above the last line, informing and never gating
    print()
    verdict(args)
    print()
    if left:
        print(f'supersede clean: NOT DONE - removed {counts}; NOT removed ' + '; '.join(left))
    else:
        print(f'supersede clean: DONE - removed {counts}')
    return 1 if left else 0


def main():
    # Whole surface declared (#476, #477): --api-capture on the noun, and on clean the flag
    # that decides whether the act runs; the roots are the tier contract's (#702).
    args = command_parser('supersede').parse_args()
    if args.verb == 'clean':
        return clean(args, bool(args.apply))
    _deletable, _orphans, covered = verdict(args)
    return 0 if covered else 1


if __name__ == '__main__':
    sys.exit(main())
