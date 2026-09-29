"""
corpus.py - the corpus's units: what a unit is, where a staged one stands to the held one
of its address, whether the pipelines have found it valid, and its promotion into shared
storage (#687). The home rsc/CALCULUS.md's roadmap names for the Mergeable protocol; this is
its first face, promotion, and the four older comparisons it names stand as they are.

THE STAGE - the room's stage is one root, tmp/stage (src/main/tier.py, #702): tmp/stage/
input is what the captures write, at the address each unit will have under data/input, a
tier shared by every rehearsal; and each rehearsal has a directory of its own, tmp/stage/
rehearsal/<stamp>, named by the stamp of its log, holding only what it derived - a data tier
whose input links to tmp/stage/input and whose output is its preview, a tmp tier with the
verdicts. A capture writes the stage's input and reads nothing (L10). `corpus-yoga pipeline
rehearse` (src/main/cli/pipeline/rehearse.sh) is the checkout's own code run with
CORPUS_YOGA_REHEARSAL=<stamp>, the one name the contract resolves to that rehearsal's tiers,
so it judges the staged units alone and writes its own directory alone;
a rehearsal is evidence, disposed of by corpus-yoga stage clean and nothing else.

UNIT - what a pipeline's declaration selects (src/main/pipeline/<pipeline>/pipeline.json):
under the declared input of each provider, every match of input_glob or extra_input_glob,
cut to subject_depth, is one unit - a directory with everything under it, or a file with
its declared companion (<stem> standing for the file's stem: claude's workspace <stem>/
beside <stem>.jsonl). Where the companion names <star>, what the glob's * matched, the
unit is named by the star and the companion is its record, which the stage alone holds:
the staged bulk export <X> is data-<X>/, its member, and manifest-<X>.json, the record
of what its capture fetched - paired where both are present, unpaired where one is, and
an unpaired unit is never promoted. Promotion copies the members; the record stays in
the stage until its janitor removes the unit. One selection names the stage's units, the
audit's subjects (src/main/validation_audit.py) and the datum's cache address,
<cache root>[/<provider>]/<subject>, the subject being the name of the datum the steps
read. A file no declaration selects is a unit of its own, measured by its bytes and
validated by nothing.

RELATION - the five relations of src/main/append_only.py, derived once from an order:
ABSENT where nothing is held; IDENTICAL where the measures are equal; EXTENDS where the
held measure precedes the staged one; AHEAD where the staged precedes the held; DIVERGED
where neither does. A kind of unit supplies its measure and the order it is compared in,
the declaration's `measure` naming a row of MEASURE; a new kind adds a row and nothing
else:

    prefix          the bytes of each selected file, each by prefix
    message-uuids   the set of message uuids of <unit>/<unit>.json, by inclusion
    turn-extent     (human turns, total turns) of the unit's markdown, componentwise
    mirror          a mirror of a single-writer source: identical, else the staged
                    replaces the held - every state follows every other
    whole           held whole or not at all: identical, else diverged

VERDICT - the pipelines are the one validator, and a rehearsal is where they judge the
stage: each datum's verdict is the record the validation step wrote under the named
rehearsal's cache, tmp/stage/rehearsal/<stamp>/tmp/cache, at the unit's cache address
(src/main/validation_verdict.py, #701), at the family's latest version; the log beside it is
never read. The promote verbs read the newest rehearsal unless --rehearsal names one. A unit is promotable when every family judged there has a
current green record - its datum digest one of the staged unit's own files (or, for a
converted datum, the recorded digest of its source one of them), and its schema digest
that of origin/main's version of the family, so that a form only a branch's schema admits
waits for the merge that licenses it. A unit no pipeline
selects, or whose pipeline declares no family for its provider, is promoted on its
relation alone and says so.

PROMOTE - each capturing noun has the verb: what `corpus-yoga browser capture` staged,
`corpus-yoga browser promote` promotes, over the same extent words (--provider <p> |
--all, --id <prefix>); agent, export and forge likewise. A noun's units are the staged
units under the roots its capture declares it writes (src/main/cli/<noun>/capture.json's
w rows under tmp/stage/input). Every staged unit gets its verdict; the relation refuses
only where the held copy would lose something (AHEAD, DIVERGED). Promotion is a copy,
never a move: the unit's members are written over the held ones by address, byte-equal
being silence, and the stage is never written by promote - the captures own it, and
`corpus-yoga stage clean` is its one janitor, removing a rehearsal's derived tiers and the
units the store holds byte-equal. A promoted unit's verdict stays in the stage's cache,
and the plain run judges the promoted datum again from the same bytes - two hands on
tmp/cache would break L6 as effects.writers_disjoint holds it. Each noun's bare status,
bare `corpus-yoga pipeline` and bare `corpus-yoga stage` report the stage.
"""
import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SELF = 'src/main/corpus.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'cache'))
from append_only import Relation, may_replace  # noqa: E402
from markdown_projection import turn_extent  # noqa: E402
import cache_io  # noqa: E402
import validation_verdict as verdicts  # noqa: E402
import tier  # noqa: E402 — the tiers, one home (#702)

STAGE = tier.TMP_STAGE_INPUT                 # what the captures write
MEMBERS_CSV = REPO / 'rsc' / 'naming' / 'export_archive_members.csv'   # what a bulk export's deposit holds, per archive category (#721)
STORE = tier.DATA / 'input'
REHEARSAL: str | None = None             # the rehearsal a verdict is read from; None is the newest


def rehearsal_stamp() -> str | None:
    return REHEARSAL or tier.newest_rehearsal()
PIPELINE_ROOT = REPO / 'src' / 'main' / 'pipeline'
CLI_ROOT = REPO / 'src' / 'main' / 'cli'
NOUNS = ('browser', 'agent', 'export', 'forge')      # the capturing nouns, each with promote


# -- unit ----------------------------------------------------------------------------------

@dataclass
class Unit:
    address: Path                 # relative to the input root (data/input or tmp/stage/input)
    members: list[Path]           # the paths that make it: its directory, or its file and companion
    files: list[Path]             # every file under the members
    selected: list[Path]          # the files the glob selected - what the measure reads
    measure: str                  # a row of MEASURE
    pipeline: str | None          # the pipeline whose declaration selected it, or None
    provider: str | None
    subject: tuple[str, ...] = field(default_factory=tuple)   # its cache address under the pipeline's root[/provider]
    datum: Path | None = None     # the member the pipeline reads, where the unit is named by a star and not by it
    record: list[Path] = field(default_factory=list)          # what the stage alone holds of it: never promoted
    missing: list[str] = field(default_factory=list)          # what is absent of a unit named by a star, by name

    @property
    def path(self) -> Path:
        """Where the pipeline's datum lies, relative to the input root."""
        return self.datum if self.datum is not None else self.address

    @property
    def cache(self) -> Path | None:
        """The datum's address under the named rehearsal's cache, where its verdict is."""
        stamp = rehearsal_stamp()
        if self.pipeline is None or stamp is None:
            return None
        rel = Path(cache_io.path_for(self.pipeline)).relative_to('tmp/cache')
        return tier.rehearsal_tmp(stamp) / 'cache' / rel / (self.provider or '') / Path(*self.subject)


def pipelines() -> dict[str, dict]:
    return {d.name: json.loads((d / 'pipeline.json').read_text())
            for d in sorted(PIPELINE_ROOT.iterdir()) if (d / 'pipeline.json').is_file()}


def resolve(template: str, provider: str | None, facts: dict) -> str:
    """A declared input with <provider> and <qualifier> the provider's own."""
    if provider is None:
        return template
    return (template.replace('<provider>', provider)
            .replace('<qualifier>', facts['provider'][provider].get('qualifier', '')))


def stores(declared: dict[str, dict] | None = None) -> list[dict]:
    """One row per store a pipeline reads - one, or one per provider where the input carries
    <provider>: pipeline, provider, input (relative to data/input), globs [(glob, measure)],
    companion, depth."""
    out = []
    for name, facts in (declared if declared is not None else pipelines()).items():
        forms = sorted(facts['provider'].items()) if 'provider' in facts else [(None, facts)]
        for provider, f in forms:
            out.append(dict(
                pipeline=name, provider=provider,
                input=Path(resolve(facts['input'], provider, facts).removeprefix('data/input/')),
                globs=[(g, m) for g, m in ((f['input_glob'], f['measure']),
                                           (f['extra_input_glob'], f['extra_measure'])) if g],
                companion=f['companion'], depth=facts['subject_depth']))
    return out


def _files_under(root: Path, path: Path) -> list[Path]:
    if path.is_file():
        return [path.relative_to(root)]
    return [f.relative_to(root) for f in sorted(path.rglob('*')) if f.is_file() and f.name != '.DS_Store']


def _star(pattern: str, name: str) -> str | None:
    """What the one * of a pattern matched in a name, or None where it matches nothing."""
    if pattern.count('*') != 1:
        return None
    before, after = pattern.split('*')
    matched = re.fullmatch(re.escape(before) + '(.*)' + re.escape(after), name)
    return matched.group(1) if matched else None


def _deposit_missing(manifest: Path, payload: Path) -> list[str]:
    """A bulk export's completeness, on sight (#721): the manifest lists the archives its
    capture was to fetch, rsc/naming/export_archive_members.csv what each one's deposit
    holds, and the payload holds those members or it does not. The members owed and absent,
    by name; empty for a complete export."""
    import csv
    try:
        categories = [f['category'] for f in json.loads(manifest.read_text()).get('data_files', [])]
    except (OSError, ValueError, TypeError, KeyError):
        return ['(the manifest is unreadable)']
    with MEMBERS_CSV.open(newline='') as f:
        deposits = {}
        for row in csv.DictReader(f):
            deposits.setdefault(row['category'], []).append(row['deposit'])
    return [member for c in categories for member in deposits.get(c, [f'({c}: no row in {MEMBERS_CSV.name})'])
            if not (payload / member).exists()]


def _select_pairs(root: Path, store: dict) -> list[Unit]:
    """The units of a store whose companion names <star>: one per star, found from the
    datum or the companion, the datum its member, the companion its record, and its
    missing whichever is absent."""
    base = root / store['input']
    pattern, measure = store['globs'][0]
    datum_form, companion_form = pattern.rstrip('/'), store['companion']
    found: dict[str, None] = {}
    for item in sorted(base.glob(datum_form)):
        if item.is_dir() == pattern.endswith('/'):
            found[_star(datum_form, item.name) or ''] = None
    for item in sorted(base.glob(companion_form.replace('<star>', '*'))):
        found[_star(companion_form.replace('<star>', '*'), item.name) or ''] = None
    out = []
    for star in sorted(s for s in found if s):
        datum = base / datum_form.replace('*', star)
        companion = base / companion_form.replace('<star>', star)
        members = [datum.relative_to(root)] if datum.exists() else []
        record = [companion.relative_to(root)] if companion.exists() else []
        missing = [name for m, name in ((datum, datum.name + ('/' if pattern.endswith('/') else '')),
                                        (companion, companion.name)) if not m.exists()]
        if not missing:
            missing = _deposit_missing(companion, datum)   # complete, or the members the record says are owed
        files = [f for m in members + record for f in _files_under(root, root / m)]
        out.append(Unit((base / star).relative_to(root), members, files, list(members), measure, store['pipeline'],
                        store['provider'], (datum.name,), datum.relative_to(root), record, missing))
    return out


def select(root: Path, store: dict) -> list[Unit]:
    """The units one store's declaration selects under root."""
    base = root / store['input']
    if not base.is_dir():
        return []
    if '<star>' in store['companion']:
        return _select_pairs(root, store)
    units: dict[Path, Unit] = {}
    for pattern, measure in store['globs']:
        glob, dirs_only = pattern.rstrip('/'), pattern.endswith('/')
        for item in sorted(base.glob(glob)):
            if item.is_dir() != dirs_only:
                continue
            rel = item.relative_to(base)
            depth = store['depth']
            subject = (rel.parts[:-1] + (item.name if dirs_only else item.stem,))[:depth]
            unit_path = base.joinpath(*rel.parts[:depth]) if (len(rel.parts) > depth or item.is_dir()) else item
            address = unit_path.relative_to(root)
            unit = units.get(address)
            if unit is None:
                members = [address]
                if store['companion'] and unit_path.is_file():
                    companion = unit_path.parent / store['companion'].replace('<stem>', unit_path.stem).rstrip('/')
                    if companion.exists():
                        members.append(companion.relative_to(root))
                files = [f for m in members for f in _files_under(root, root / m)]
                unit = Unit(address, members, files, [], measure, store['pipeline'], store['provider'], subject)
                units[address] = unit
            unit.selected.append(item.relative_to(root))
    return list(units.values())


def units(root: Path) -> list[Unit]:
    """Every unit under root: what the declarations select, then every file they do not."""
    out: list[Unit] = []
    covered: set[Path] = set()
    if not root.is_dir():
        return out
    for store in stores():
        for unit in select(root, store):
            out.append(unit)
            covered.update(unit.files)
    for rel in _files_under(root, root):
        if rel not in covered:
            out.append(Unit(rel, [rel], [rel], [rel], 'prefix', None, None))
    return sorted(out, key=lambda u: u.address)


# -- relation ------------------------------------------------------------------------------

def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytes_of(root: Path, unit: Unit):
    """{file name: bytes} of the selected files present under root."""
    present = {rel.name: (root / rel).read_bytes() for rel in unit.selected if (root / rel).is_file()}
    return present or None


def _uuids_of(root: Path, unit: Unit):
    conv = root / unit.path / f'{unit.path.name}.json'
    if not conv.is_file():
        return None
    try:
        return {m['uuid'] for m in json.loads(conv.read_text()).get('chat_messages', []) if m.get('uuid')}
    except ValueError:
        return None


def _extent_of(root: Path, unit: Unit):
    mds = sorted((root / unit.path).glob('*.md')) if (root / unit.path).is_dir() else []
    return max((turn_extent(m.read_text()) for m in mds), default=None)


def _tree_of(root: Path, unit: Unit):
    path = root / unit.path
    if not path.exists():
        return None
    return {f.relative_to(path).as_posix() if path.is_dir() else f.name: _digest((root / f if not f.is_absolute() else f).read_bytes())
            for f in [root / rel for rel in _files_under(root, path)]}


def _leq_prefix(a, b) -> bool:
    return all(k in b and b[k].startswith(v) for k, v in a.items())


def _leq_subset(a, b) -> bool:
    return a <= b


def _leq_pair(a, b) -> bool:
    return a[0] <= b[0] and a[1] <= b[1]


def _leq_any(a, b) -> bool:
    return True


def _leq_equal(a, b) -> bool:
    return a == b


def _words_bytes(staged, held, unit: Unit) -> str:
    names = ', '.join(sorted(staged))
    return f'{sum(len(v) for v in (held or {}).values())} -> {sum(len(v) for v in staged.values())} bytes of {names}'


def _words_count(noun: str) -> Callable:
    return lambda staged, held, unit: f'{len(held or ())} -> {len(staged)} {noun}'


def _words_extent(staged, held, unit: Unit) -> str:
    say = lambda m: f'{m[0]} human turns of {m[1]}'
    return f'{say(held) if held else "nothing"} -> {say(staged)}'


def _words_mirror(staged, held, unit: Unit) -> str:
    removed = len(set(held or {}) - set(staged))
    return f'mirrored: {len(held or ())} -> {len(staged)} file(s), {removed} removed'


def _words_whole(staged, held, unit: Unit) -> str:
    return 'held whole or not at all'


# measure name: (value under a root, the order, the words) - a new kind of unit adds a row
MEASURE: dict[str, tuple[Callable, Callable, Callable]] = {
    'prefix':        (_bytes_of,  _leq_prefix, _words_bytes),
    'message-uuids': (_uuids_of,  _leq_subset, _words_count('message(s)')),
    'turn-extent':   (_extent_of, _leq_pair,   _words_extent),
    'mirror':        (_tree_of,   _leq_any,    _words_mirror),
    'whole':         (_tree_of,   _leq_equal,  _words_whole),
}


def derive(staged, held, leq: Callable) -> Relation:
    """The one derivation of the five relations from an order."""
    if held is None:
        return Relation.ABSENT
    if staged == held:
        return Relation.IDENTICAL
    if leq(held, staged):
        return Relation.EXTENDS
    if leq(staged, held):
        return Relation.AHEAD
    return Relation.DIVERGED


def relation(unit: Unit) -> tuple[Relation, str]:
    """Where the staged unit stands to the held one, and the measure's own words."""
    value, leq, words = MEASURE[unit.measure]
    staged = value(STAGE, unit)
    if staged is None:
        return Relation.DIVERGED, f'the staged unit holds nothing its measure ({unit.measure}) reads'
    held = value(STORE, unit)
    return derive(staged, held, leq), words(staged, held, unit)


# -- verdict -------------------------------------------------------------------------------

def _main_schema_digest(pipeline: str, family: str) -> tuple[str | None, str]:
    """The digest of origin/main's latest version file of a family, and the version's name."""
    fam_dir = f'rsc/schema/pipeline/{pipeline}/{family}'
    ls = subprocess.run(['git', '-C', str(REPO), 'ls-tree', '--name-only', 'origin/main', fam_dir + '/'],
                        capture_output=True, text=True).stdout.split()
    versions = sorted((v for v in ls if v.rsplit('/', 1)[-1].startswith('v') and v.endswith('.json')),
                      key=lambda v: int(''.join(c for c in v.rsplit('/', 1)[-1] if c.isdigit()) or 0))
    if not versions:
        return None, '(no version at origin/main)'
    blob = subprocess.run(['git', '-C', str(REPO), 'show', f'origin/main:{versions[-1]}'], capture_output=True).stdout
    return _digest(blob), versions[-1].rsplit('/', 1)[-1][:-5]


def _own_digests(unit: Unit) -> set[str]:
    """What a verdict on this staged unit can name as its datum: each file's digest, and
    the digest of the unit's tree as run.sh records a converted directory's source."""
    own = {_digest((STAGE / rel).read_bytes()) for rel in unit.files}
    root = STAGE / unit.path
    if root.is_dir():
        lines = ''.join(f'{rel.relative_to(unit.path).as_posix()} {_digest((STAGE / rel).read_bytes())}\n'
                        for rel in unit.files if rel.is_relative_to(unit.path))
        own.add(_digest(lines.encode()))
    return own


def verdict(unit: Unit) -> tuple[bool | None, str]:
    """Whether the pipelines have found the staged unit valid at origin/main's versions:
    True, False with the reason, or None where no pipeline selects the unit."""
    if unit.pipeline is None:
        return None, 'no pipeline selects it - promoted on its relation alone'
    schemas = pipelines()[unit.pipeline]['schemas']
    judges = [s for s in schemas if unit.provider is None or '/' not in s or s.startswith(unit.provider + '/')]
    if not judges:
        return None, f'no family of {unit.pipeline} validates {unit.provider}\'s - promoted on its relation alone'
    cache = unit.cache
    remedy = 'corpus-yoga pipeline rehearse judges it'
    if cache is None:
        return False, f'no rehearsal - {remedy}'
    # the verdict is its record (src/main/validation_verdict.py, #701); the log beside it is never read
    by_family: dict[str, list[Path]] = {}
    for rec in (cache / 'validation').rglob(f'v*{verdicts.SUFFIX}'):
        by_family.setdefault(rec.parent.relative_to(cache / 'validation').as_posix(), []).append(rec)
    if not by_family:
        return False, f'no verdict - {remedy}'
    own = _own_digests(unit)
    recorded = cache / 'source.sha256'
    converted = recorded.is_file() and recorded.read_text().strip() in own
    words = []
    for leaf, recs in sorted(by_family.items()):
        latest = max(recs, key=lambda f: int(''.join(c for c in f.name.split('.')[0] if c.isdigit()) or 0))
        version = latest.name[:-len(verdicts.SUFFIX)]
        family = next((s for s in judges if s.rsplit('/', 1)[-1] == leaf.split('/')[0]), leaf)
        record = verdicts.read(latest)
        if record is None:
            return False, f'no verdict at {family} - {remedy}'
        if record['datum_sha256'] not in own and not converted:
            return False, f'the verdict at {family} is not on this staged unit - {remedy}'
        main_digest, main_version = _main_schema_digest(unit.pipeline, family)
        if main_digest is None or record['schema_sha256'] != main_digest:
            if main_version == version:
                return False, (f'the verdict at {family} {version} is against a schema origin/main does not hold - '
                               'corpus-yoga pipeline rehearse re-judges it')
            return False, (f'the verdict at {family} is at {version} of this checkout, which origin/main does not hold '
                           f'({main_version} there) - the mint\'s merge licenses the promotion')
        if record['verdict'] != 'valid':
            return False, f'fails {family} {version} - a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)'
        words.append(f'{family} {version}')
    return True, 'validates at ' + ', '.join(words) + f' (origin/main; rehearsal {rehearsal_stamp()})'


# -- promote -------------------------------------------------------------------------------

def roots_of(noun: str) -> list[Path]:
    """The stage roots a noun's capture declares it writes, relative to tmp/stage/input."""
    decl = json.loads((CLI_ROOT / noun / 'capture.json').read_text())
    return [Path(w.removeprefix('tmp/stage/input/')) for w in decl.get('w', []) if w.startswith('tmp/stage/input/')]


def noun_of(unit: Unit) -> str | None:
    """The capturing noun whose promote verb reaches the unit, or None."""
    for noun in NOUNS:
        if any(unit.address.is_relative_to(root) for root in roots_of(noun)):
            return noun
    return None


REMEDY = {
    Relation.AHEAD:    'the held unit holds more - recapture it; to drop the staged copy instead:',
    Relation.DIVERGED: 'each holds what the other lacks - inspect both; to keep the held one and drop the staged copy:',
}


def survey(selected: list[Unit] | None = None) -> list[tuple[Unit, Relation, str, bool | None, str]]:
    """(unit, relation, the relation's words, verdict, the verdict's words), for the units
    given or for everything staged. Every unit gets its verdict: an identical capture in a
    form the family refuses is refused like any other."""
    rows = []
    for unit in (units(STAGE) if selected is None else selected):
        rel, detail = relation(unit)
        if unit.missing:
            whole = bool(unit.members and unit.record)   # both stand, and the record says what is owed
            rows.append((unit, Relation.ABSENT if not unit.members else rel,
                         f'no {", ".join(unit.missing)} staged', False,
                         INCOMPLETE.format(n=len(unit.missing)) if whole else UNPAIRED))
            continue
        ok, words = verdict(unit) if rel not in REFUSING else (None, '')
        rows.append((unit, rel, detail, ok, words))
    return rows


REFUSING = (Relation.AHEAD, Relation.DIVERGED)   # the relations under which the held copy would lose something
UNPAIRED = 'unpaired - a staged unit is promoted where its record stands beside it'
INCOMPLETE = 'incomplete - {n} member(s) the record lists are not in the payload; corpus-yoga stage clean --apply removes it'


def incomplete() -> list[Unit]:
    """The staged units whose record or payload is absent, or whose payload lacks what the
    record lists - never a rehearsal's input, always the janitor's (#721)."""
    return [u for u in units(STAGE) if u.missing] if STAGE.is_dir() else []


def refuse_rehearsal() -> int:
    """The stage's word before a rehearsal: 1, with the units named and the janitor as the
    remedy, while any staged unit is incomplete; 0 where every unit is whole (#721)."""
    bad = incomplete()
    if not bad:
        return 0
    print(f'rehearse: NOT DONE - the stage holds {len(bad)} incomplete unit(s), which no pipeline is shown:')
    for u in bad:
        print(f'  {u.address}: missing {", ".join(u.missing)}')
    print('    → run: corpus-yoga stage clean --apply')
    return 1


def promotable(rel: Relation, ok: bool | None) -> bool:
    return rel not in REFUSING and ok is not False


def extent(noun: str, provider: str | None, everything: bool, unit_id: str | None) -> list[Unit]:
    """The staged units a noun's promote names: every unit under the noun's roots, or one
    provider's, or one unit of that provider by a prefix of a component of its address."""
    roots = roots_of(noun)
    if provider is not None:
        mine = [r for r in roots if r.parts[0] == provider]
        if not mine:
            sys.exit(f'error: {noun} captures nothing of {provider!r} - it captures: '
                     + ', '.join(sorted({r.parts[0] for r in roots})))
        roots = mine
    elif not everything and any(r.parts[0] in ('claude', 'gemini') for r in roots) and len({r.parts[0] for r in roots}) > 1:
        sys.exit(f'error: corpus-yoga {noun} promote names its extent: --all, --provider <p>, or --provider <p> --id <prefix>')
    chosen = [u for u in units(STAGE) if any(u.address.is_relative_to(r) for r in roots)]
    if unit_id is None:
        return chosen
    hits = [u for u in chosen if any(part.startswith(unit_id) for part in u.address.parts[1:])]
    if len(hits) != 1:
        names = ', '.join(str(u.address) for u in hits) or 'nothing'
        sys.exit(f'error: --id {unit_id!r} names {len(hits)} staged unit(s) of {provider}: {names} - '
                 f'--id names one; corpus-yoga {noun} lists them')
    return hits


def _tree_files(path: Path) -> dict[str, Path]:
    if path.is_file():
        return {'': path}
    if not path.is_dir():
        return {}
    return {f.relative_to(path).as_posix(): f for f in sorted(path.rglob('*')) if f.is_file() and f.name != '.DS_Store'}


def redundant(unit: Unit) -> bool:
    """Whether every member of the staged unit is byte-identical to the held one - a unit
    already promoted, which only the stage's janitor removes."""
    if not unit.members or unit.missing:
        return False
    for rel in unit.members:
        staged, held = _tree_files(STAGE / rel), _tree_files(STORE / rel)
        if not held or staged.keys() != held.keys():   # an empty staged member and an absent held one are not the same thing
            return False
        if any(staged[k].read_bytes() != held[k].read_bytes() for k in staged):
            return False
    return True


def _copy(unit: Unit) -> int:
    """Write the unit over the held one by address, member by member: a file whose bytes
    the store holds is left alone, a differing or missing file is written, a held file the
    member no longer has is removed - the member replaced whole, byte-equal being silence.
    The stage is not written. Returns the files written or removed."""
    changed = 0
    for rel in unit.members:
        staged, held = _tree_files(STAGE / rel), _tree_files(STORE / rel)
        for key, src in staged.items():
            dst = (STORE / rel) if key == '' else (STORE / rel / key)
            if key in held and held[key].read_bytes() == src.read_bytes():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_dir():
                shutil.rmtree(dst)
            shutil.copy2(src, dst)
            changed += 1
        for key, old in held.items():
            if key not in staged:
                old.unlink()
                changed += 1
    return changed


def remove(unit: Unit) -> None:
    """Take the unit out of the stage - the janitor's act (corpus-yoga stage clean), never
    promotion's. Its record goes with it."""
    for rel in unit.members + unit.record:
        s = STAGE / rel
        if s.is_dir():
            shutil.rmtree(s)
        elif s.exists():
            s.unlink()
    for d in sorted((p for p in STAGE.rglob('*') if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def say(groups: dict[str, list[str]]) -> None:
    """A verdict shared by many units is said once, with its count, and the units listed
    beneath it by address and relation: a stage of 121 units refused for one reason reads
    as one reason and 121 addresses, and a unit that differs stands alone under its own."""
    for heading, lines in groups.items():
        print(f'  {heading}: {len(lines)} unit' + ('' if len(lines) == 1 else 's'))
        for line in lines:
            print(f'    {line}')


def _unit_line(unit: Unit, rel: Relation, detail: str) -> str:
    name = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
            Relation.AHEAD: 'ahead', Relation.DIVERGED: 'diverged'}[rel]
    return f'{unit.address}: {name} ({detail})'


def _refusal(unit: Unit, rel: Relation, ok: bool | None, words: str) -> tuple[str, str]:
    """(the heading a refused unit stands under, what follows its line)."""
    remedy = '→ run: rm -r ' + ' '.join(shlex.quote(f'tmp/stage/input/{m.as_posix()}') for m in unit.members + unit.record)
    if unit.missing:
        return f'REFUSED - {words}', ''   # the janitor's, named in the words (#721)
    if rel in REFUSING:
        return f'{rel.name} - refused: {REMEDY[rel]}', f'\n      {remedy}'
    return f'REFUSED - {words}', ''


def promote(noun: str, selected: list[Unit], stamp: str | None = None) -> int:
    """Promote the units, their verdicts read from the named rehearsal (the newest unless
    stamp): each promotable one copied over the held one by address, the rest named; the
    stage is never written. The lines are grouped by what they share, the certified state
    follows as evidence, and the verdict is the last line. Exit 1 while anything was refused."""
    global REHEARSAL
    if stamp is not None:
        if not tier.rehearsal(stamp).is_dir():
            sys.exit(f'error: no rehearsal {stamp} under tmp/stage/rehearsal - corpus-yoga stage lists them')
        REHEARSAL = stamp
    rows = survey(selected)
    if not rows:
        print(f'{noun} promote: DONE - nothing staged')
        return 0
    groups: dict[str, list[str]] = {}
    written = unchanged = refused = 0
    for unit, rel, detail, ok, words in rows:
        line = _unit_line(unit, rel, detail)
        if promotable(rel, ok):
            n = _copy(unit)
            if n:
                groups.setdefault(f'promoted - {words}', []).append(f'{line} - {n} file' + ('' if n == 1 else 's') + ' written')
                written += 1
            else:
                groups.setdefault(f'held already, byte-equal - {words}', []).append(line)
                unchanged += 1
        else:
            heading, after = _refusal(unit, rel, ok, words)
            groups.setdefault(heading, []).append(line + after)
            refused += 1
    say(groups)
    # the noun's read-only status is the certified state after the act: evidence, beneath
    # the lines and above the verdict, informing and never gating
    print()
    stage_status()
    print()
    # one ask, one verdict, the last line: DONE only when nothing asked for was left undone
    print(f'{noun} promote: {"NOT DONE" if refused else "DONE"} - promoted {written}, held already {unchanged}, refused {refused}')
    return 1 if refused else 0


def size_of(p: Path) -> int:
    if p.is_file() or p.is_symlink():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob('*') if f.is_file() or f.is_symlink())


def human(n: float) -> str:
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024:
            return f'{n:.0f}{unit}'
        n /= 1024
    return f'{n:.1f}T'


def rehearsal_header(stamp: str) -> str:
    """The rehearsal's record: its log's header - time, room, commit - and the command as typed."""
    log = tier.TMP / 'logs' / 'pipeline' / 'rehearse' / f'{stamp}.log'
    if not log.is_file():
        return 'no log under tmp/logs/pipeline/rehearse - run by path, not by the launcher'
    return ' · '.join(log.read_text().splitlines()[:2])


def rehearsals() -> list[str]:
    return sorted(d.name for d in tier.REHEARSALS.iterdir() if d.is_dir()) if tier.REHEARSALS.is_dir() else []


def orphans() -> list[Path]:
    """What sits under tmp/stage and is neither the input nor the rehearsals."""
    stage = tier.TMP_STAGE
    return [e for e in sorted(stage.iterdir()) if e.name not in ('input', 'rehearsal')] if stage.is_dir() else []


def stage_status() -> int:
    """Bare corpus-yoga stage: the tier's state, read-only - the input's size, each orphan
    with the janitor as its remedy, each rehearsal with its record, the units' counts
    against the newest. Every effective stage verb ends by relaying it."""
    stage = tier.TMP_STAGE
    if not stage.is_dir():
        print('tmp/stage/: absent - nothing captured since the last clean, no rehearsal made')
        return 0
    print(f'tmp/stage/: input {human(size_of(tier.TMP_STAGE_INPUT)) if tier.TMP_STAGE_INPUT.exists() else "absent"}')
    for e in orphans():
        print(f'  orphan: {e.relative_to(REPO).as_posix()} ({human(size_of(e))}) - nothing reads it; corpus-yoga stage clean --apply removes it')
    stamps = rehearsals()
    if not stamps:
        print('  rehearsals: none - corpus-yoga pipeline rehearse makes one')
    for stamp in stamps:
        print(f'  rehearsal {stamp} ({human(size_of(tier.rehearsal(stamp)))}): {rehearsal_header(stamp)}')
    rows = survey()
    if not rows:
        print('  units: none staged')
        return 0
    held = sum(1 for u, rel, _d, ok, _w in rows if promotable(rel, ok) and redundant(u))
    ready = sum(1 for u, rel, _d, ok, _w in rows if promotable(rel, ok)) - held
    refused = len(rows) - held - ready
    print(f'  units: {len(rows)} staged - {ready} promotable, {held} held already (byte-equal), {refused} refused'
          + (f', judged by rehearsal {stamps[-1]}' if stamps else '') + '; the relations: corpus-yoga pipeline, or each capturing noun bare')
    # the counts by kind - pipeline and provider - so that a total says what it counts
    kinds: dict[str, list[int]] = {}
    for u, rel, _d, ok, _w in rows:
        kind = '/'.join(x for x in (u.pipeline or 'no pipeline', u.provider or u.address.parts[0]) if x)
        tally = kinds.setdefault(kind, [0, 0, 0])
        if promotable(rel, ok):
            tally[1 if redundant(u) else 0] += 1
        else:
            tally[2] += 1
    for kind, (k_ready, k_held, k_refused) in sorted(kinds.items()):
        print(f'    {kind}: {k_ready + k_held + k_refused} staged - {k_ready} promotable, {k_held} held already, {k_refused} refused')
    return 0


def _declares(noun: str, verb: str, flag: str) -> bool:
    declared = json.loads((CLI_ROOT / noun / f'{verb}.json').read_text())
    return any(arg['name'] == flag for arg in declared.get('args', []))


def _whole_extent(noun: str) -> str:
    """The words after `promote` that name everything the noun staged: --all where its
    promote declares the flag, nothing where the verb has no extent."""
    return ' --all' if _declares(noun, 'promote', '--all') else ''


def pairs(noun: str) -> int:
    """The noun's units named by a star: the held ones, a member each and a record where
    shared storage holds one from before the stage; the staged ones, each paired or
    unpaired, naming what is absent. Writes nothing."""
    roots = roots_of(noun)
    for store in stores():
        if '<star>' not in store['companion'] or not any(store['input'].is_relative_to(r) for r in roots):
            continue
        for unit in select(STORE, store):
            for path in unit.members:
                print(f'  held: {unit.address.name} - {path.name}/')
            for path in unit.record:
                print(f'  held: {unit.address.name} - {path.name}, which nothing reads: a record is the stage\'s')
        for unit in select(STAGE, store):
            present = ' and '.join(p.name + ('/' if (STAGE / p).is_dir() else '') for p in unit.members + unit.record)
            if not unit.missing:
                print(f'  staged: {unit.address.name} complete - {present}')
                continue
            if unit.members and unit.record:
                print(f'  staged: {unit.address.name} incomplete - {present}, missing {", ".join(unit.missing)}; '
                      'corpus-yoga stage clean --apply removes it')
                continue
            print(f'  staged: {unit.address.name} unpaired - {present} with no {", ".join(unit.missing)} beside it')
            if not unit.members and _declares(noun, 'capture', '--manifest'):
                where = (STAGE / unit.record[0]).relative_to(REPO)
                print('    to fetch its payload, where its URLs are unspent:')
                print(f'      → run: corpus-yoga {noun} capture --manifest {shlex.quote(str(where))}')
    return 0


def report(noun: str | None) -> int:
    """The stage as a noun's bare status shows it (its capture's units), or as bare
    `corpus-yoga pipeline` shows it (every unit). The lines are grouped by what they share.
    Writes nothing."""
    rows = survey([u for u in units(STAGE) if noun is None or noun_of(u) == noun])
    if not rows:
        print(f'stage: nothing {noun + " capture" if noun else "captured and"} staged in tmp/stage/input')
        return 0
    groups: dict[str, list[str]] = {}
    by_noun: dict[str, int] = {}
    unjudged = refused = held = 0
    for unit, rel, detail, ok, words in rows:
        line = _unit_line(unit, rel, detail)
        if promotable(rel, ok):
            if redundant(unit):
                held += 1
                groups.setdefault(f'held already, byte-equal - {words}', []).append(line)
            else:
                n = noun_of(unit) or '?'
                by_noun[n] = by_noun.get(n, 0) + 1
                groups.setdefault(f'promotable - {words}', []).append(line)
        else:
            refused += 1
            if ok is False and words.startswith(('no verdict', 'no rehearsal')):
                unjudged += 1
            heading, after = _refusal(unit, rel, ok, words)
            groups.setdefault(heading, []).append(line + after)
    say(groups)
    tail = ''.join(f'; corpus-yoga {n} promote{_whole_extent(n)} promotes {k}' for n, k in sorted(by_noun.items()))
    if unjudged:
        tail += f'; corpus-yoga pipeline rehearse judges {unjudged} without a verdict'
    if held:
        tail += f'; corpus-yoga stage clean removes {held} held byte-equal'
    print(f'stage: {len(rows)} unit(s) - {sum(by_noun.values())} promotable, {held} held already, {refused} refused{tail}')
    return 0


def main(argv: list[str]) -> int:
    """`corpus.py promote <noun> [--provider <p> | --all] [--id <prefix>]` - a capturing
    noun's promote verb, its argv already validated against the noun's declaration;
    `corpus.py report [<noun>]` - the stage as a status face shows it; `corpus.py pairs <noun>` -
    the noun's units named by a star, held and staged; `corpus.py count` - the staged units, a number."""
    ap = argparse.ArgumentParser(add_help=False)
    sub = ap.add_subparsers(dest='act', required=True)
    pr = sub.add_parser('promote', add_help=False)
    pr.add_argument('noun', choices=NOUNS)
    pr.add_argument('--provider', default=None)
    pr.add_argument('--all', action='store_true')
    pr.add_argument('--id', default=None)
    pr.add_argument('--rehearsal', default=None)
    rp = sub.add_parser('report', add_help=False)
    rp.add_argument('noun', nargs='?', choices=NOUNS, default=None)
    pa = sub.add_parser('pairs', add_help=False)
    pa.add_argument('noun', choices=NOUNS)
    sub.add_parser('count', add_help=False)
    args = ap.parse_args(argv)
    if args.act == 'promote':
        if args.id is not None and args.provider is None:
            sys.exit('error: --id names a unit within a provider - say which with --provider')
        return promote(args.noun, extent(args.noun, args.provider, args.all, args.id), args.rehearsal)
    if args.act == 'report':
        return report(args.noun)
    if args.act == 'pairs':
        return pairs(args.noun)
    print(len(units(STAGE)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
