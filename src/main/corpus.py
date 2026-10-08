"""
corpus.py - the corpus's units: what a unit is, where a staged one stands to the held one
of its address, whether the pipelines have found it valid, and its promotion into shared
storage (#687). The home rsc/CALCULUS.md's roadmap names for the Mergeable protocol; this is
its first face, promotion, and the four older comparisons it names stand as they are.

THE STAGE - the room's stage is one root, tmp/stage (src/main/tier.py, #702): tmp/stage/
input is what the captures write, at the address each unit will have under data/input;
tmp/stage/scratch is what the last rehearsal's run derived - a data tier whose input links
to tmp/stage/input and whose output is its preview, a tmp tier with the validation -
replaced whole by the next run; and tmp/stage/rehearsal.json is the rehearsal record, one
file, what the last rehearsal saw and judged (src/main/rehearsal.py, #815). A capture writes the
stage's input and reads nothing (L10). `corpus-yoga pipeline rehearse`
(src/main/cli/pipeline/rehearse.sh) is the checkout's own code run with
CORPUS_YOGA_REHEARSAL=<stamp>, the one name the contract resolves to the scratch tiers, so
it judges the staged units alone and writes the scratch and the record alone.

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
stage: each datum's verdict is what the validation step wrote under the scratch's cache
at the unit's cache address (src/main/validation_verdict.py, #701), at the family's latest
version, and the rehearsal record holds it with the digests of every unit the run began
over. Every verb reads the record, so the last rehearsal is the judgement of every unit.
Against it a unit is unseen (absent from the record), changed since (its digests are not
the record's), seen without verdict, or judged; and it is promotable when every family
judged it green - its datum digest one of the staged unit's own files (or, for a
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
`corpus-yoga stage clean` is its one janitor, removing the units the store holds
byte-equal. A promoted unit's verdict stays in the record and the scratch, and the plain
run judges the promoted datum again from the same bytes - two hands on tmp/cache would
break L6 as effects.writers_disjoint holds it. Each noun's bare status,
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
from enum import Enum
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
import facts  # noqa: E402 - the one printer of a status's facts (#740)
import rehearsal  # noqa: E402 - the rehearsal record, one home (#815)
import tier  # noqa: E402 — the tiers, one home (#702)

STAGE = tier.TMP_STAGE_INPUT                 # what the captures write
MEMBERS_CSV = REPO / 'rsc' / 'naming' / 'export_archive_members.csv'   # what a bulk export's deposit holds, per archive category (#721)
STORE = tier.DATA / 'input'
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
    kind: str = 'file'            # what its selection's declaration calls it; what no pipeline selects is a file

    @property
    def path(self) -> Path:
        """Where the pipeline's datum lies, relative to the input root."""
        return self.datum if self.datum is not None else self.address

    @property
    def cache(self) -> Path | None:
        """The datum's address under the scratch tiers' cache, where the last run wrote its
        validation: what the rehearsal record reduces from."""
        if self.pipeline is None:
            return None
        rel = Path(cache_io.path_for(self.pipeline)).relative_to('tmp/cache')
        return tier.SCRATCH_TMP / 'cache' / rel / (self.provider or '') / Path(*self.subject)


def pipelines() -> dict[str, dict]:
    return {d.name: json.loads((d / 'pipeline.json').read_text())
            for d in sorted(PIPELINE_ROOT.iterdir()) if (d / 'pipeline.json').is_file()}


def resolve(template: str, provider: str | None, facts: dict) -> str:
    """A declared input with <provider> and <qualifier> the provider's own."""
    if provider is None:
        return template
    return (template.replace('<provider>', provider)
            .replace('<qualifier>', facts['provider'][provider].get('qualifier', '')))


@dataclass(frozen=True)
class Glob:
    """One selection a store declares: what it matches, and what a unit it selects is."""
    pattern: str                  # the glob under the store's input; a trailing / selects directories
    measure: str                  # a row of MEASURE
    kind: str                     # what the declaration calls a unit it selects


@dataclass(frozen=True)
class Store:
    """One store a pipeline reads, as its declaration states it (#751): every reader of a
    row reads these fields, held to them by the dev gate's type check."""
    pipeline: str
    provider: str | None
    input: Path                   # relative to data/input
    globs: tuple[Glob, ...]       # the pipeline's selection first, then its second where it declares one
    companion: str                # what stands beside a selected datum, by <stem> or <star>; '' where nothing does
    depth: int                    # the path parts a unit's subject is cut to


def stores(declared: dict[str, dict] | None = None) -> list[Store]:
    """One row per store a pipeline reads - one, or one per provider where the input carries
    <provider>."""
    out = []
    for name, facts in (declared if declared is not None else pipelines()).items():
        forms = sorted(facts['provider'].items()) if 'provider' in facts else [(None, facts)]
        for provider, f in forms:
            out.append(Store(
                pipeline=name, provider=provider,
                input=Path(resolve(facts['input'], provider, facts).removeprefix('data/input/')),
                globs=tuple(Glob(g, m, k) for g, m, k in ((f['input_glob'], f['measure'], f['unit']),
                                                          (f['extra_input_glob'], f['extra_measure'], f['extra_unit'])) if g),
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


def _select_pairs(root: Path, store: Store) -> list[Unit]:
    """The units of a store whose companion names <star>: one per star, found from the
    datum or the companion, the datum its member, the companion its record, and its
    missing whichever is absent."""
    base = root / store.input
    first = store.globs[0]
    pattern, measure, kind = first.pattern, first.measure, first.kind
    datum_form, companion_form = pattern.rstrip('/'), store.companion
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
        out.append(Unit((base / star).relative_to(root), members, files, list(members), measure, store.pipeline,
                        store.provider, (datum.name,), datum.relative_to(root), record, missing, kind))
    return out


def select(root: Path, store: Store) -> list[Unit]:
    """The units one store's declaration selects under root."""
    base = root / store.input
    if not base.is_dir():
        return []
    if '<star>' in store.companion:
        return _select_pairs(root, store)
    units: dict[Path, Unit] = {}
    for selection in store.globs:
        pattern, measure, kind = selection.pattern, selection.measure, selection.kind
        glob, dirs_only = pattern.rstrip('/'), pattern.endswith('/')
        for item in sorted(base.glob(glob)):
            if item.is_dir() != dirs_only:
                continue
            rel = item.relative_to(base)
            depth = store.depth
            subject = (rel.parts[:-1] + (item.name if dirs_only else item.stem,))[:depth]
            unit_path = base.joinpath(*rel.parts[:depth]) if (len(rel.parts) > depth or item.is_dir()) else item
            address = unit_path.relative_to(root)
            unit = units.get(address)
            if unit is None:
                members = [address]
                if store.companion and unit_path.is_file():
                    companion = unit_path.parent / store.companion.replace('<stem>', unit_path.stem).rstrip('/')
                    if companion.exists():
                        members.append(companion.relative_to(root))
                files = [f for m in members for f in _files_under(root, root / m)]
                unit = Unit(address, members, files, [], measure, store.pipeline, store.provider, subject, kind=kind)
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
    return f'{len(held or ())} -> {len(staged)} file(s) mirrored, {removed} removed'


def _words_whole(staged, held, unit: Unit) -> str:
    return 'held whole or not at all'


def _export_atoms():
    """The bulk export's measure, src/main/pipeline/chat-export/atoms.py, loaded where it lives (#743)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('chat_export_atoms', PIPELINE_ROOT / 'chat-export' / 'atoms.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _atoms_of(root: Path, unit: Unit):
    return _export_atoms().value(root, unit)


def _leq_atoms(a, b) -> bool:
    return _export_atoms().leq(a, b)


def _words_atoms(staged, held, unit: Unit) -> str:
    return _export_atoms().words(staged, held, unit)


# measure name: (value under a root, the order, the words) - a new kind of unit adds a row
MEASURE: dict[str, tuple[Callable, Callable, Callable]] = {
    'prefix':        (_bytes_of,  _leq_prefix, _words_bytes),
    'message-uuids': (_uuids_of,  _leq_subset, _words_count('message(s)')),
    'turn-extent':   (_extent_of, _leq_pair,   _words_extent),
    'mirror':        (_tree_of,   _leq_any,    _words_mirror),
    'whole':         (_tree_of,   _leq_equal,  _words_whole),
    'atoms':         (_atoms_of,  _leq_atoms,  _words_atoms),
}
ACROSS_THE_KIND = {'atoms'}   # measures whose units are compared with every other of their kind, not with the same-named alone


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


def own_digests(unit: Unit) -> set[str]:
    """What a verdict on this staged unit can name as its datum: each file's digest, and
    the digest of the unit's tree as run.sh records a converted directory's source."""
    own = {_digest((STAGE / rel).read_bytes()) for rel in unit.files}
    root = STAGE / unit.path
    if root.is_dir():
        lines = ''.join(f'{rel.relative_to(unit.path).as_posix()} {_digest((STAGE / rel).read_bytes())}\n'
                        for rel in unit.files if rel.is_relative_to(unit.path))
        own.add(_digest(lines.encode()))
    return own


class Judgement(Enum):
    VALID = 'valid'          # every family judged it, green, at origin/main's versions
    REFUSED = 'refused'      # a family gave its verdict against it
    UNSEEN = 'unseen'        # staged since the rehearsal began: absent from its record
    CHANGED = 'changed'      # seen by the rehearsal with other digests than it has now
    UNJUDGED = 'unjudged'    # no verdict stands on these bytes: the state before one, a rehearsal its remedy
    NONE = 'none'            # no family judges it: promoted on its relation alone


REMEDY_REHEARSE = 'corpus-yoga pipeline rehearse judges it'


def judges_of(unit: Unit) -> list[str]:
    """The families of the unit's pipeline that judge its provider's units."""
    schemas = pipelines()[unit.pipeline]['schemas'] if unit.pipeline else []
    return [s for s in schemas if unit.provider is None or '/' not in s or s.startswith(unit.provider + '/')]


def family_of(unit: Unit, leaf: str) -> str:
    """The family, as the pipeline declares it, whose validation wrote under the leaf
    directory of the unit's cache; the leaf itself where none is declared."""
    return next((s for s in judges_of(unit) if s.rsplit('/', 1)[-1] == leaf.split('/')[0]), leaf)


def verdict(unit: Unit, record: dict | str | None = None, own: set[str] | None = None,
            main_digest: Callable[[str, str], tuple[str | None, str | None]] | None = None) -> tuple[Judgement, str]:
    """What the pipelines have found of the staged unit at origin/main's versions, read
    from the rehearsal record (src/main/rehearsal.py), and the words for it. The record,
    the unit's own digests and origin/main's schema digests are read where not given."""
    if unit.pipeline is None:
        return Judgement.NONE, 'no pipeline selects it - promoted on its relation alone'
    judges = judges_of(unit)
    if not judges:
        return Judgement.NONE, f'no family of {unit.pipeline} validates {unit.provider}\'s - promoted on its relation alone'
    record = rehearsal.read() if record is None else record
    if record is None:
        return Judgement.UNJUDGED, f'no rehearsal - {REMEDY_REHEARSE}'
    if isinstance(record, str):
        return Judgement.UNJUDGED, record
    stamp = record['stamp']
    seen = record['units'].get(unit.address.as_posix())
    if seen is None:
        return Judgement.UNSEEN, f'unseen by rehearsal {stamp} - {REMEDY_REHEARSE}'
    own = own_digests(unit) if own is None else own
    if set(seen['digests']) != own:
        return Judgement.CHANGED, f'changed since rehearsal {stamp} - {REMEDY_REHEARSE}'
    if not seen['verdicts']:
        return Judgement.UNJUDGED, f'seen by rehearsal {stamp}, no verdict written - {REMEDY_REHEARSE}'
    converted = seen.get('source') in own
    main_digest = _main_schema_digest if main_digest is None else main_digest
    words = []
    for family, one in sorted(seen['verdicts'].items()):
        version = one['version']
        if one['datum_sha256'] not in own and not converted:
            return Judgement.CHANGED, f'the verdict at {family} is on other bytes than this staged unit - {REMEDY_REHEARSE}'
        digest, main_version = main_digest(unit.pipeline, family)
        if digest is None or one['schema_sha256'] != digest:
            if main_version == version:
                return Judgement.UNJUDGED, (f'the verdict at {family} {version} is against a schema origin/main does not hold - '
                               'corpus-yoga pipeline rehearse re-judges it')
            return Judgement.REFUSED, (f'the verdict at {family} is at {version} of this checkout, which origin/main does not hold '
                           f'({main_version} there) - the mint\'s merge licenses the promotion')
        if one['verdict'] != 'valid':
            return Judgement.REFUSED, f'fails {family} {version} - a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)'
        words.append(f'{family} {version}')
    return Judgement.VALID, 'validates at ' + ', '.join(words) + f' (origin/main; rehearsal {stamp})'


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
    Relation.AHEAD:    'the held unit holds more - a recapture replaces the staged copy',
    Relation.DIVERGED: 'each holds what the other lacks - the reader reconciles the two',
}


@dataclass(frozen=True)
class Judged:
    """A staged unit as the survey reads it: where it stands to the held one, and its verdict."""
    unit: Unit
    relation: Relation
    detail: str                   # the measure's words for the relation
    judgement: Judgement
    words: str                    # the judgement's words

    @property
    def state(self) -> str:
        """The one of STATES the unit is in."""
        return state(self.unit, self.relation, self.judgement)

    @property
    def promotable(self) -> bool:
        return promotable(self.relation, self.judgement) and not self.unit.missing


def survey(selected: list[Unit] | None = None) -> list[Judged]:
    """Each unit given, or everything staged, with its relation and its verdict. Every unit
    gets its verdict: an identical capture in a form the family refuses is refused like any
    other, and a unit whose relation refuses it is still judged, so that the rehearsal's
    counts are of every unit."""
    rows = []
    for unit in (units(STAGE) if selected is None else selected):
        rel, detail = relation(unit)
        if unit.missing:
            whole = bool(unit.members and unit.record)   # both stand, and the record says what is owed
            rows.append(Judged(unit, Relation.ABSENT if not unit.members else rel,
                               f'no {", ".join(unit.missing)} staged', Judgement.UNJUDGED,
                               INCOMPLETE.format(n=len(unit.missing)) if whole else UNPAIRED))
            continue
        ok, words = verdict(unit)
        rows.append(Judged(unit, rel, detail, ok, words))
    return rows


REFUSING = (Relation.AHEAD, Relation.DIVERGED)   # the relations under which the held copy would lose something
UNPAIRED = 'unpaired, its record or its payload absent; corpus-yoga stage clean --apply removes it'
INCOMPLETE = '{n} member(s) the record lists are not in the payload; corpus-yoga stage clean --apply removes it'


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


STATES: tuple[str, ...] = ('promotable', 'held already', 'refused', 'incomplete', 'unjudged')
JUDGED = {Judgement.VALID: 'valid', Judgement.REFUSED: 'refused'}                     # a verdict the rehearsal gave
NOT_JUDGED = {Judgement.CHANGED: 'changed since', Judgement.UNSEEN: 'unseen',          # none stands: why, or no family at all,
              Judgement.UNJUDGED: 'seen without verdict', Judgement.NONE: 'no family'}   # which promotes on the relation alone


def state(unit: Unit, rel: Relation, judgement: Judgement) -> str:
    """The one of STATES a staged unit is in. Refused is a verdict given against it, by its
    relation or by a family; unjudged is the state before any verdict."""
    if unit.missing:
        return 'incomplete'
    if rel in REFUSING or judgement is Judgement.REFUSED:
        return 'refused'
    if judgement in (Judgement.UNSEEN, Judgement.CHANGED, Judgement.UNJUDGED):
        return 'unjudged'
    return 'held already' if redundant(unit) else 'promotable'


def tally(rows: list[Judged]) -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in STATES}
    for row in rows:
        counts[row.state] += 1
    return counts


def counted(counts: dict[str, int]) -> str:
    """The counts in words, every state named, so that a total's parts are the states the
    units are in."""
    return ', '.join(f'{counts[s]} {s}' for s in STATES)


def promotable(rel: Relation, ok: Judgement) -> bool:
    return rel not in REFUSING and ok in (Judgement.VALID, Judgement.NONE)


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


PASSES = 3   # the Finder writes into a directory being emptied; a second pass is the whole remedy


def dispose(path: Path) -> str | None:
    """Remove the entry as it stands at the act - a janitor's one act. None when it is
    gone, else why it is not."""
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


def shadow(unit: Unit) -> Path | None:
    """The unit's derivation under the checkout's cache, at the address the pipeline writes
    it - what only the unit feeds, and goes with it (#744)."""
    if unit.pipeline is None:
        return None
    rel = Path(cache_io.path_for(unit.pipeline)).relative_to('tmp/cache')
    return tier.TMP / 'cache' / rel / (unit.provider or '') / Path(*unit.subject)


def orphaned_shadows() -> list[Path]:
    """Every directory under the cache at a held kind's depth that is no held unit's shadow:
    the derivation of a unit the store no longer holds, which would pass for one (#744)."""
    held = [u for u in units(STORE) if u.pipeline is not None]
    shadows = {shadow(u) for u in held}
    depths: dict[tuple, int] = {}
    for u in held:
        depths[(u.pipeline, u.provider)] = len(u.subject)
    out: list[Path] = []
    for (pipeline, provider), depth in sorted(depths.items(), key=lambda kv: (kv[0][0], kv[0][1] or '')):
        root = tier.TMP / 'cache' / Path(cache_io.path_for(pipeline)).relative_to('tmp/cache') / (provider or '')
        if not root.is_dir():
            continue
        out += [d for d in sorted(root.glob('/'.join(['*'] * depth))) if d.is_dir() and d not in shadows]
    return out


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


RELATION_NAME = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
                 Relation.AHEAD: 'ahead', Relation.DIVERGED: 'diverged'}


def _unit_line(unit: Unit, rel: Relation, detail: str) -> str:
    return f'{unit.address}: {RELATION_NAME[rel]} ({detail})'


def _heading(unit: Unit, rel: Relation, ok: Judgement, words: str) -> str:
    """The heading a unit that is not promoted stands under: its state, then why. No
    heading prescribes a removal - an incomplete unit is the janitor's, named in its
    words (#721), and a refused one the reader's to reconcile."""
    if rel in REFUSING and not unit.missing:
        return f'REFUSED - {rel.name.lower()}: {REMEDY[rel]}'
    return f'{state(unit, rel, ok).upper()} - {words}'


def promote(noun: str, selected: list[Unit]) -> int:
    """Promote the units, their verdicts read from the rehearsal record: each promotable
    one copied over the held one by address, the rest named; the stage is never written.
    The lines are grouped by what they share, the certified state follows as evidence, and
    the verdict is the last line. Exit 1 while anything was refused."""
    rows = survey(selected)
    if not rows:
        print(f'{noun} promote: DONE - nothing staged')
        return 0
    groups: dict[str, list[str]] = {}
    written = unchanged = 0
    left: dict[str, int] = {s: 0 for s in STATES[2:]}
    for row in rows:
        line = _unit_line(row.unit, row.relation, row.detail)
        if row.promotable:
            n = _copy(row.unit)
            if n:
                groups.setdefault(f'promoted - {row.words}', []).append(f'{line} - {n} file' + ('' if n == 1 else 's') + ' written')
                written += 1
            else:
                groups.setdefault(f'held already, byte-equal - {row.words}', []).append(line)
                unchanged += 1
        else:
            groups.setdefault(_heading(row.unit, row.relation, row.judgement, row.words), []).append(line)
            left[row.state] += 1
    say(groups)
    # the noun's read-only status is the certified state after the act: evidence, beneath
    # the lines and above the verdict, informing and never gating
    print()
    stage_status()
    print()
    # one ask, one verdict, the last line: DONE only when nothing asked for was left undone
    undone = sum(left.values())
    print(f'{noun} promote: {"NOT DONE" if undone else "DONE"} - promoted {written}, held already {unchanged}, '
          + ', '.join(f'{s} {left[s]}' for s in left))
    return 1 if undone else 0


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


BEFORE_815 = tier.TMP_STAGE / 'rehearsal'   # what the layout before #815 left: stamped rehearsals, or the record before its extension
MIGRATION_815 = 'rsc/migration/815.sh'      # the moves it owes, which corpus-yoga migration sync takes


def orphans() -> list[Path]:
    """What sits under tmp/stage and is neither the input, the scratch, the record nor the
    directory the layout before #815 left, which is the migration's."""
    stage = tier.TMP_STAGE
    kept = ('input', 'scratch', tier.TMP_STAGE_REHEARSAL.name, BEFORE_815.name)
    return [e for e in sorted(stage.iterdir()) if e.name not in kept] if stage.is_dir() else []


@dataclass
class Orphan:
    size: str
    why: str
    remedy: facts.Command


@dataclass
class Rehearsal:
    """The rehearsal record as the stage says it: its anchor, and the staged units by what
    it found of them - judged, valid or refused; not judged, and why."""
    stamp: str
    commit: str
    tree: str                     # clean, or dirty with the count
    signature: str
    exit: int
    extent: str                   # how many units the run began over
    judged: dict[str, int]
    not_judged: dict[str, int]


@dataclass
class StageTier:
    input: str                    # the staged input's size, or that it is absent
    scratch: str                  # the last run's derived tiers' size, or that they are absent
    orphans: dict[str, Orphan]    # by path
    record: Rehearsal | str = facts.named('rehearsal.json')   # the record, or why there is none
    rehearsal: Orphan | None = None                           # what the layout before #815 left, while it stands


@dataclass
class Kind:
    """One kind of staged unit - pipeline, provider, the unit's declared name (#736): how
    many are staged, how many in each of STATES that any is in, each refusal's words once
    with how many carry them, and each command that acts on them with how many."""
    staged: int
    promotable: int | None
    held_already: int | None
    refused: int | None
    incomplete: int | None
    unjudged: int | None
    refused_by: dict[str, int] | None
    remedy: dict[str, str] | None

    @classmethod
    def of(cls, rows: list[Judged]) -> 'Kind':
        counts = tally(rows)
        n = {state: counts[state] or None for state in STATES}
        return cls(len(rows), n['promotable'], n['held already'], n['refused'], n['incomplete'], n['unjudged'],
                   refused_by(rows) or None, {command: f'{verb} {n}' for command, (verb, n) in remedies(rows, counts).items()} or None)


@dataclass
class StageStatus:
    """Bare corpus-yoga stage: the tier's state."""
    tmp_stage: StageTier | str = facts.named('tmp/stage')
    units: dict[str, Kind] | str | None = None
    stage: str | None = None      # the verdict


def rehearsal_facts(record: dict, rows: list[Judged]) -> Rehearsal:
    """The record's anchor, and the whole units by what it found of them."""
    judged = {name: 0 for name in JUDGED.values()}
    not_judged = {name: 0 for name in NOT_JUDGED.values()}
    for row in rows:
        if row.unit.missing:
            continue                          # the janitor's, counted among the units
        if row.judgement in JUDGED:
            judged[JUDGED[row.judgement]] += 1
        else:
            not_judged[NOT_JUDGED[row.judgement]] += 1
    return Rehearsal(record['stamp'], record['commit'], 'clean' if not record['dirty'] else f'dirty ({record["dirty"]})',
                     record['signature'], record['exit'], f'{len(record["units"])} unit(s)', judged, not_judged)


def stage_facts() -> StageStatus:
    """Bare corpus-yoga stage as facts (#741, #759, #822): the input's size, the scratch's,
    each orphan with the janitor as its remedy, the rehearsal record's anchor with the units
    by what it found of them, the units by kind - each kind's counts, its refusals by their
    words and the commands that act on it - and the verdict last: what to run and how many
    it acts on, and what is refused and why, so that the tail is never a dead end."""
    stage = tier.TMP_STAGE
    if not stage.is_dir():
        return StageStatus('absent - nothing captured since the last clean, no rehearsal made')
    rows = survey()
    record = rehearsal.read()
    out = StageStatus(StageTier(
        input=human(size_of(tier.TMP_STAGE_INPUT)) if tier.TMP_STAGE_INPUT.exists() else 'absent',
        scratch=human(size_of(tier.TMP_STAGE_SCRATCH)) if tier.TMP_STAGE_SCRATCH.exists() else 'absent',
        orphans={e.relative_to(REPO).as_posix(): Orphan(human(size_of(e)), 'nothing reads it',
                                                         facts.Command('corpus-yoga stage clean --apply', 'removes it'))
                 for e in orphans()},
        record=(rehearsal_facts(record, rows) if isinstance(record, dict)
                else 'none - corpus-yoga pipeline rehearse makes one' if record is None else record),
        rehearsal=(Orphan(human(size_of(BEFORE_815)),
                          ('a directory of stamped rehearsals, the layout before #815' if BEFORE_815.is_dir()
                           else 'the record before its name carried its extension, which a record at its name supersedes')
                          + f' - {MIGRATION_815} removes it',
                          facts.Command('corpus-yoga migration sync --apply', 'takes the move'))
                   if BEFORE_815.exists() else None)))
    if not rows:
        out.units, out.stage = 'none staged', 'nothing staged'
        return out
    kinds: dict[str, list[Judged]] = {}
    for row in rows:
        kinds.setdefault(counted_as(row.unit), []).append(row)
    counts = tally(rows)
    out.units = {kind: Kind.of(of_kind) for kind, of_kind in sorted(kinds.items())}
    out.stage = stage_verdict(kinds, counts)
    return out


def stage_verdict(kinds: dict[str, list[Judged]], counts: dict[str, int]) -> str:
    """The last line: each command to run with the kinds it acts on and how many of each,
    and what is refused and why - each refusal's words up to their first dash, with how
    many carry them - every count by kind, never summed across kinds."""
    by_command: dict[str, tuple[str, dict[str, int]]] = {}
    for kind, rows in sorted(kinds.items()):
        for command, (verb, n) in remedies(rows, tally(rows)).items():
            by_command.setdefault(command, (verb, {}))[1][kind] = n
    parts = [f'{command} {verb} ' + ', '.join(f'{kind} ({n})' for kind, n in of.items()) for command, (verb, of) in by_command.items()]
    if counts['refused']:
        refused = {kind: refused_by(rows) for kind, rows in sorted(kinds.items()) if any(row.state == 'refused' for row in rows)}
        parts.append(f'{counts["refused"]} refused - ' + ', '.join(
            f'{kind} {words.split(" - ")[0]} ({n})' for kind, each in refused.items() for words, n in each.items()))
    total = sum(len(rows) for rows in kinds.values())
    return f'{total} unit(s) staged - ' + ('; '.join(parts) if parts else 'nothing to do')


def stage_status() -> int:
    """Bare corpus-yoga stage: the tier's state, read-only, as facts (#741). Every effective
    stage verb ends by relaying it."""
    facts.say(stage_facts())
    return 0


def remedies(rows: list[Judged], counts: dict[str, int]) -> dict[str, tuple[str, int]]:
    """Each command that acts on what the counts count, with its verb and how many: a
    capturing noun's promote for its promotable units, the janitor for the held-already and
    incomplete, the rehearsal for the unjudged - each only while its count is not zero."""
    out: dict[str, tuple[str, int]] = {}
    by_noun: dict[str, int] = {}
    for row in rows:
        noun = noun_of(row.unit) if row.state == 'promotable' else None
        if noun is not None:
            by_noun[noun] = by_noun.get(noun, 0) + 1
    for noun, n in sorted(by_noun.items()):
        out[f'corpus-yoga {noun} promote --all'] = ('promotes', n)
    if counts['held already'] + counts['incomplete']:
        out['corpus-yoga stage clean --apply'] = ('removes', counts['held already'] + counts['incomplete'])
    if counts['unjudged']:
        out['corpus-yoga pipeline rehearse'] = ('judges', counts['unjudged'])
    return out


def refused_by(rows: list[Judged]) -> dict[str, int]:
    """Each refusal's words once - the relation's where it refuses, the verdict's otherwise -
    with how many units carry them, the most first."""
    out: dict[str, int] = {}
    for row in rows:
        if row.state == 'refused':
            words = REMEDY[row.relation] if row.relation in REFUSING else row.words
            out[words] = out.get(words, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def counted_as(unit: Unit) -> str:
    """What a count of the unit is a count of: its pipeline and provider, then the name its
    selection's declaration gives it (#736)."""
    where = '/'.join(x for x in (unit.pipeline or 'no pipeline', unit.provider or unit.address.parts[0]) if x)
    return f'{where} {unit.kind}'


@dataclass(frozen=True)
class Duplicate:
    """A unit whose content another unit of its kind holds."""
    unit: Unit
    holder: Unit                  # the unit that holds it
    how: str                      # 'identical', the same at two addresses, or 'contained', whole within the holder's
    by: str                       # the measure's words for the two


def held_twice(root: Path, live: frozenset[Path] = frozenset(), newest: frozenset[Path] = frozenset()) -> list[Duplicate]:
    """Every duplicate under root - a unit whose content another unit of its kind holds, the
    same at two addresses or whole within the other's by the kind's measure (#738, #743).
    Two units are compared where they share a kind and - unless the kind's measure relates
    every unit of the kind, as the export's atoms do - a name, by the measure their pipeline
    declares; a measure whose order relates everything - mirror's - holds only what is
    equal. Of identical units the holder is the newest: the one at an address `newest`
    names - a live directory that is a link, since a link is made from the newer to the
    older - then one a live store still writes, `live`, so that the copy a capture renews
    is the one kept, and failing both the one at the first address; a unit a fuller one
    contains is named with the fullest."""
    groups: dict[tuple, list[Unit]] = {}
    for unit in units(root):
        if unit.pipeline is not None:
            name = '' if unit.measure in ACROSS_THE_KIND else unit.path.name
            groups.setdefault((unit.pipeline, unit.provider, unit.kind, name), []).append(unit)
    out: list[Duplicate] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        value, leq, words = MEASURE[group[0].measure]
        values = [(u, value(root, u)) for u in group]
        for unit, mine in values:
            if mine is None:
                continue
            containers = [o for o, theirs in values if o is not unit and theirs is not None and theirs != mine
                          and leq is not _leq_any and leq(mine, theirs)]
            equals = [o for o, theirs in values if o is not unit and theirs == mine]
            # among identical copies one is the holder: a live one, else the first address
            keeper = min(equals + [unit], key=lambda o: (o.address not in newest, o.address not in live, o.address)) if equals else unit
            if containers:
                holder, how = max(containers, key=lambda o: size_of(root / o.path)), 'contained'
            elif equals and keeper is not unit:
                holder, how = keeper, 'identical'
            else:
                continue
            out.append(Duplicate(unit, holder, how, words(mine, next(v for o, v in values if o is holder), unit)))
    return sorted(out, key=lambda duplicate: duplicate.unit.address)


@dataclass
class Held:
    size: str
    files: int
    units: int


@dataclass
class Stray:
    size: str
    why: str


@dataclass
class HeldTwice:
    """A duplicate as the status states it: its kind and size, and the unit that holds it
    under how it does."""
    duplicate: Duplicate
    size: str
    holder_size: str

    def facts(self) -> dict:
        d = self.duplicate
        return {'kind': d.unit.kind, 'size': self.size,
                ('identical to' if d.how == 'identical' else 'contained by'): d.holder.address,
                'holder size': self.holder_size, 'by': d.by}


@dataclass
class StoreStatus:
    """Bare corpus-yoga store: shared storage in the stage's terms."""
    data_input: Held | str = facts.named('data/input')
    held: dict[str, int] | None = None        # the units by what each count is of
    stray: dict[str, Stray] | None = None     # by path: what no pipeline selects and no capturing noun writes
    duplicates: dict[str, HeldTwice] | None = None   # by the duplicate's address
    ahead: dict | str | None = None           # what this room's live stores hold beyond it - the store noun's reading
    store: str | None = None                  # the verdict


def store_facts(live: frozenset[Path] = frozenset(), newest: frozenset[Path] = frozenset()) -> tuple[StoreStatus, int, int]:
    """Bare corpus-yoga store, its first two readings as facts (#738, #741, #759): the units
    shared storage holds, by what each count is of, with anything no pipeline selects and
    no capturing noun writes; then every duplicate with the unit that holds it. Writes
    nothing. Returns (the facts, units held, duplicates)."""
    if not STORE.is_dir():
        return StoreStatus('absent - this workspace holds no store'), 0, 0
    held = units(STORE)
    kinds: dict[str, int] = {}
    for unit in held:
        kinds[counted_as(unit)] = kinds.get(counted_as(unit), 0) + 1
    stray: dict[str, Stray] = {}
    for unit in held:
        if unit.pipeline is None and noun_of(unit) is None:
            stray[unit.address.as_posix()] = Stray(human(size_of(STORE / unit.address)),
                                                   'no pipeline selects it and no capturing noun writes there')
        elif not unit.members and unit.record:
            stray[unit.record[0].as_posix()] = Stray(human(size_of(STORE / unit.record[0])),
                                                     'the record of a unit the store does not hold')
    twice = held_twice(STORE, live, newest)
    return StoreStatus(
        Held(human(size_of(STORE)), sum(len(u.files) for u in held), len(held)),
        held=dict(sorted(kinds.items())), stray=stray,
        duplicates={d.unit.address.as_posix(): HeldTwice(d, human(size_of(STORE / d.unit.path)), human(size_of(STORE / d.holder.path)))
                    for d in twice},
    ), len(held), len(twice)


def _declares(noun: str, verb: str, flag: str) -> bool:
    declared = json.loads((CLI_ROOT / noun / f'{verb}.json').read_text())
    return any(arg['name'] == flag for arg in declared.get('args', []))


@dataclass
class Paired:
    """An export named by a star, as the status states it: what stands of it, held or
    staged, and what would complete it."""
    payload: str | None = None    # its data directory
    record: str | None = None     # its capture's manifest
    standing: str | None = None   # a staged one: complete, incomplete or unpaired
    note: str | None = None
    remedy: facts.Command | None = None


@dataclass
class Pairs:
    held: dict[str, Paired]       # by the export's name
    staged: dict[str, Paired]


def pairs_facts(noun: str) -> Pairs:
    """The noun's units named by a star, as facts (#753, #759): the held ones, a member each
    and a record where shared storage holds one from before the stage; the staged ones, each
    paired or unpaired, naming what is absent. Writes nothing."""
    roots = roots_of(noun)
    out = Pairs({}, {})
    for store in stores():
        if '<star>' not in store.companion or not any(store.input.is_relative_to(r) for r in roots):
            continue
        for unit in select(STORE, store):
            out.held[unit.address.name] = Paired(
                payload=f'{unit.members[0].name}/' if unit.members else None,
                record=unit.record[0].name if unit.record else None,
                note='nothing reads the record: a record is the stage\'s' if unit.record else None)
        for unit in select(STAGE, store):
            present = ' and '.join(p.name + ('/' if (STAGE / p).is_dir() else '') for p in unit.members + unit.record)
            if not unit.missing:
                out.staged[unit.address.name] = Paired(standing=f'complete - {present}')
                continue
            if unit.members and unit.record:
                out.staged[unit.address.name] = Paired(standing=f'incomplete - {present}, missing {", ".join(unit.missing)}',
                                                       remedy=facts.Command('corpus-yoga stage clean --apply', 'removes it'))
                continue
            item = Paired(standing=f'unpaired - {present} with no {", ".join(unit.missing)} beside it')
            if not unit.members and _declares(noun, 'capture', '--manifest'):
                where = (STAGE / unit.record[0]).relative_to(REPO)
                item.remedy = facts.Command(f'corpus-yoga {noun} capture --manifest {shlex.quote(str(where))}',
                                            'fetches its payload, where its URLs are unspent')
            out.staged[unit.address.name] = item
    return out


@dataclass(frozen=True)
class Staged:
    """A staged unit as a status says it: its relation to the held one and the measure's
    words for it, the state it is in, the verdict's words, and the rehearsal that saw it."""
    relation: str
    measure: str
    judged: str
    verdict: str | None = None
    rehearsal: str | None = None
    remedy: dict[str, str] | None = None     # beside the unit whose state is a fault, and nowhere else


@dataclass
class StageReport:
    """The stage as a noun's bare status shows it: each unit under its address, with its
    facts and, where its state is a fault, the command that acts on it."""
    staged: dict[str, Staged]


def report_facts(noun: str | None) -> StageReport:
    """The stage as a noun's bare status shows it (its capture's units), or as bare
    `corpus-yoga pipeline` shows it (every unit), as facts (#753, #759, #800): each unit by
    its address with its facts beneath, and a remedy where a unit's state is one - unjudged,
    incomplete or held already. A promotable unit is no fault, so no command is named for
    it: what follows a capture is its noun's to say (#767). The counts are
    `corpus-yoga stage`'s to say. Writes nothing."""
    rows = survey([u for u in units(STAGE) if noun is None or noun_of(u) == noun])
    record = rehearsal.read()
    staged: dict[str, Staged] = {}
    for row in rows:
        verdict = REMEDY[row.relation] if row.relation in REFUSING and not row.unit.missing else (row.words or None)
        remedy = ({'corpus-yoga pipeline rehearse': 'judges it'} if row.state == 'unjudged'
                  else {'corpus-yoga stage clean --apply': 'removes it'} if row.state in ('held already', 'incomplete') else None)
        address = row.unit.address.as_posix()
        staged[address] = Staged(RELATION_NAME[row.relation], row.detail, row.state, verdict,
                                 record['stamp'] if isinstance(record, dict) and address in record['units'] else None, remedy)
    return StageReport(staged)


def held_rows() -> list[tuple[str, str, str, int, str, str]]:
    """What each pipeline holds, a row per store and kind it declares: pipeline, provider,
    kind, the units held, the store's address, and the capturing noun that writes there.
    The store's own reading, for a reader in another language (#771)."""
    found = units(STORE) if STORE.is_dir() else []
    out = []
    for store in stores():
        noun = next((n for n in NOUNS if any(store.input.is_relative_to(r) for r in roots_of(n))), '')
        for selection in store.globs:
            count = sum(1 for u in found if (u.pipeline, u.provider, u.kind) == (store.pipeline, store.provider, selection.kind))
            out.append((store.pipeline, store.provider or store.input.parts[0], selection.kind, count,
                        f'data/input/{store.input.as_posix()}', noun))
    return out


def main(argv: list[str]) -> int:
    """`corpus.py promote <noun> [--provider <p> | --all] [--id <prefix>]` - a capturing
    noun's promote verb, its argv already validated against the noun's declaration;
    `corpus.py count` - the staged units, a number; `corpus.py held` - what each pipeline
    holds, tab-separated rows."""
    ap = argparse.ArgumentParser(add_help=False)
    sub = ap.add_subparsers(dest='act', required=True)
    pr = sub.add_parser('promote', add_help=False)
    pr.add_argument('noun', choices=NOUNS)
    pr.add_argument('--provider', default=None)
    pr.add_argument('--all', action='store_true')
    pr.add_argument('--id', default=None)
    sub.add_parser('count', add_help=False)
    sub.add_parser('held', add_help=False)
    args = ap.parse_args(argv)
    if args.act == 'promote':
        if args.id is not None and args.provider is None:
            sys.exit('error: --id names a unit within a provider - say which with --provider')
        return promote(args.noun, extent(args.noun, args.provider, args.all, args.id))
    if args.act == 'held':
        for row in held_rows():
            print('\t'.join(str(cell) for cell in row))
        return 0
    print(len(units(STAGE)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
