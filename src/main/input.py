"""
input.py - the room's input, tmp/input: what a captured unit is, where it stands to the
held one of its address, and whether the pipelines have found it valid (#687).

A capture writes what its source returned under tmp/input, at the address it will have
under data/input - tmp/input/<provider>/<channel>/<capture>/... - and reads nothing (L10).
Promotion is the one reduce over the room's input against the store, in three parts, each
with one home:

UNIT - what a pipeline's declaration selects (src/main/pipeline/<pipeline>/pipeline.json):
under the declared input of each provider, every match of input_glob or extra_input_glob,
cut to subject_depth, is one unit - a directory with everything under it, or a file with
its declared companion (<stem> standing for the file's stem: claude's workspace <stem>/
beside <stem>.jsonl). One selection names the stage's units, the overlay's links, the
audit's subjects (src/main/validation_audit.py) and the datum's cache address,
<cache root>[/<provider>]/<subject>. A file no declaration selects is a unit of its own,
measured by its bytes and validated by nothing.

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

VERDICT - the pipelines are the one validator; corpus-yoga pipeline run --overlay runs
them over the store with the room's input laid over it, and each datum's verdict is the
log the pipeline cached at the unit's cache address, at the family's latest version.
Promotion reads those logs: a unit is promotable when every family judged there has a
current green verdict - the log's datum digest one of the staged unit's own files (or,
for a converted datum, the recorded digest of its source one of them), and the log's
schema digest that of origin/main's version of the family, so that a form only a branch's
schema admits waits for the merge that licenses it. A unit no pipeline selects is
promoted on its relation alone, and says so.

PROMOTE - each capturing noun has the verb: what `corpus-yoga browser capture` staged,
`corpus-yoga browser promote` promotes, over the same extent words (--provider <p> |
--all, --id <prefix>); agent, export and forge likewise. A noun's units are the staged
units under the roots its capture declares it writes (src/main/cli/<noun>/capture.json's
w rows under tmp/input). `corpus-yoga input`, bare, is the report over every noun's.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SELF = 'src/main/input.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'cache'))
from append_only import Relation, may_replace  # noqa: E402
from markdown_projection import turn_extent  # noqa: E402
import cache_io  # noqa: E402

STAGE = REPO / 'tmp' / 'input'
STORE = REPO / 'data' / 'input'
PIPELINE_ROOT = REPO / 'src' / 'main' / 'pipeline'
CLI_ROOT = REPO / 'src' / 'main' / 'cli'
NOUNS = ('browser', 'agent', 'export', 'forge')      # the capturing nouns, each with promote


# -- unit ----------------------------------------------------------------------------------

@dataclass
class Unit:
    address: Path                 # relative to the input root (data/input, tmp/input, the overlay)
    members: list[Path]           # the paths that make it: its directory, or its file and companion
    files: list[Path]             # every file under the members
    selected: list[Path]          # the files the glob selected - what the measure reads
    measure: str                  # a row of MEASURE
    pipeline: str | None          # the pipeline whose declaration selected it, or None
    provider: str | None
    subject: tuple[str, ...] = field(default_factory=tuple)   # its cache address under the pipeline's root[/provider]

    @property
    def cache(self) -> Path | None:
        if self.pipeline is None:
            return None
        return REPO / cache_io.path_for(self.pipeline) / (self.provider or '') / Path(*self.subject)


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


def select(root: Path, store: dict) -> list[Unit]:
    """The units one store's declaration selects under root."""
    base = root / store['input']
    if not base.is_dir():
        return []
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
    conv = root / unit.address / f'{unit.address.name}.json'
    if not conv.is_file():
        return None
    try:
        return {m['uuid'] for m in json.loads(conv.read_text()).get('chat_messages', []) if m.get('uuid')}
    except ValueError:
        return None


def _extent_of(root: Path, unit: Unit):
    mds = sorted((root / unit.address).glob('*.md')) if (root / unit.address).is_dir() else []
    return max((turn_extent(m.read_text()) for m in mds), default=None)


def _tree_of(root: Path, unit: Unit):
    path = root / unit.address
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
    root = STAGE / unit.address
    if root.is_dir():
        lines = ''.join(f'{rel.relative_to(unit.address).as_posix()} {_digest((STAGE / rel).read_bytes())}\n'
                        for rel in unit.files if rel.is_relative_to(unit.address))
        own.add(_digest(lines.encode()))
    return own


def verdict(unit: Unit) -> tuple[bool | None, str]:
    """Whether the pipelines have found the staged unit valid at origin/main's versions:
    True, False with the reason, or None where no pipeline selects the unit."""
    if unit.pipeline is None or unit.cache is None:
        return None, 'no pipeline selects it - promoted on its relation alone'
    schemas = pipelines()[unit.pipeline]['schemas']
    judges = [s for s in schemas if unit.provider is None or '/' not in s or s.startswith(unit.provider + '/')]
    if not judges:
        return None, f'no family of {unit.pipeline} validates {unit.provider}\'s - promoted on its relation alone'
    cache = unit.cache
    remedy = f'corpus-yoga pipeline run {unit.pipeline} --overlay validates it'
    by_family: dict[str, list[Path]] = {}
    for log in (cache / 'validation').rglob('v*.log'):
        by_family.setdefault(log.parent.relative_to(cache / 'validation').as_posix(), []).append(log)
    if not by_family:
        return False, f'no verdict - {remedy}'
    own = _own_digests(unit)
    recorded = cache / 'source.sha256'
    converted = recorded.is_file() and recorded.read_text().strip() in own
    words = []
    for leaf, logs in sorted(by_family.items()):
        log = max(logs, key=lambda f: int(''.join(c for c in f.stem if c.isdigit()) or 0))
        family = next((s for s in judges if s.rsplit('/', 1)[-1] == leaf.split('/')[0]), leaf)
        text = log.read_text().splitlines()
        if len(text) < 3:
            return False, f'no verdict at {family} - {remedy}'
        datum = text[1].rsplit('sha256 ', 1)[-1].strip()
        if datum not in own and not converted:
            return False, f'the verdict at {family} is not on this staged unit - {remedy}'
        main_digest, main_version = _main_schema_digest(unit.pipeline, family)
        if main_digest is None or not text[2].rstrip().endswith(f'sha256 {main_digest}'):
            if main_version == log.stem:
                return False, (f'the verdict at {family} {log.stem} is against a schema origin/main does not hold - '
                               f'corpus-yoga pipeline run {unit.pipeline} --overlay re-judges it')
            return False, (f'the verdict at {family} is at {log.stem} of this checkout, which origin/main does not hold '
                           f'({main_version} there) - the mint\'s merge licenses the promotion')
        if 'Valid!' not in log.read_text():
            return False, f'fails {family} {log.stem} - a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)'
        words.append(f'{family} {log.stem}')
    return True, 'validates at ' + ', '.join(words) + ' (origin/main)'


# -- overlay -------------------------------------------------------------------------------

def overlay(out: Path) -> tuple[int, int]:
    """A view of data/input with this room's input laid over it, as a tree of links under
    out: every unit of the store linked by its members at their addresses, then every
    staged unit linked over it. The pipelines read the view where they would read
    data/input, so a mint is tested over what the room has captured before the merge that
    licenses its promotion. Returns (units of data/input, units of tmp/input) linked."""
    if out.exists():
        shutil.rmtree(out)
    counts = []
    for root in (STORE, STAGE):
        n = 0
        for unit in units(root):
            for rel in unit.members:
                link = out / rel
                if link.is_symlink() or link.is_file():
                    link.unlink()
                elif link.is_dir():
                    shutil.rmtree(link)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(root / rel)
            n += 1
        counts.append(n)
    return counts[0], counts[1]


# -- promote -------------------------------------------------------------------------------

def roots_of(noun: str) -> list[Path]:
    """The stage roots a noun's capture declares it writes, relative to tmp/input."""
    decl = json.loads((CLI_ROOT / noun / 'capture.json').read_text())
    return [Path(w.removeprefix('tmp/input/')) for w in decl.get('w', []) if w.startswith('tmp/input/')]


def noun_of(unit: Unit) -> str | None:
    """The capturing noun whose promote verb reaches the unit, or None."""
    for noun in NOUNS:
        if any(unit.address.is_relative_to(root) for root in roots_of(noun)):
            return noun
    return None


REMEDY = {
    Relation.AHEAD:    'the held unit holds more - recapture, or remove the staged copy: rm -r tmp/input/{unit}',
    Relation.DIVERGED: 'each holds what the other lacks - inspect both, then keep one: rm -r tmp/input/{unit} keeps the held',
}


def survey(selected: list[Unit] | None = None) -> list[tuple[Unit, Relation, str, bool | None, str]]:
    """(unit, relation, the relation's words, verdict, the verdict's words), for the units
    given or for everything staged."""
    rows = []
    for unit in (units(STAGE) if selected is None else selected):
        rel, detail = relation(unit)
        ok, words = verdict(unit) if may_replace(rel) else (None, '')
        rows.append((unit, rel, detail, ok, words))
    return rows


def promotable(rel: Relation, ok: bool | None) -> bool:
    return may_replace(rel) and ok is not False


def word(unit: Unit, rel: Relation, detail: str, ok: bool | None, words: str) -> str:
    verb = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
            Relation.AHEAD: 'AHEAD - refused', Relation.DIVERGED: 'DIVERGED - refused'}[rel]
    line = f'  {unit.address}: {verb} ({detail})'
    if may_replace(rel):
        line += f'; {words}' if ok is not False else f'; REFUSED - {words}'
    return line


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
                 f'--id names one; corpus-yoga input lists them')
    return hits


def _place(unit: Unit) -> None:
    """Write the unit into the store: each of its members - its directory, or its file and
    the companion that moves with it - replaces the held one whole."""
    for rel in unit.members:
        s, h = STAGE / rel, STORE / rel
        h.parent.mkdir(parents=True, exist_ok=True)
        if h.is_symlink() or h.is_file():
            h.unlink()
        elif h.is_dir():
            shutil.rmtree(h)
        shutil.move(str(s), str(h))


def _clear(unit: Unit) -> None:
    for rel in unit.members:
        s = STAGE / rel
        if s.is_dir():
            shutil.rmtree(s)
        elif s.exists():
            s.unlink()


def _prune_empty(root: Path) -> None:
    if not root.is_dir():
        return
    for d in sorted((p for p in root.rglob('*') if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def promote(noun: str, selected: list[Unit]) -> int:
    """Promote the units: each promotable one written into the store and taken out of
    tmp/input, each identical one taken out unwritten, the rest named and left. Exit 1
    while anything was refused."""
    rows = survey(selected)
    if not rows:
        print(f'{noun} promote: nothing staged')
        return 0
    written = cleared = refused = 0
    for unit, rel, detail, ok, words in rows:
        if rel is Relation.IDENTICAL:
            print(word(unit, rel, detail, ok, words) + ' - cleared from tmp/input')
            _clear(unit)
            cleared += 1
        elif promotable(rel, ok):
            print(word(unit, rel, detail, ok, words) + ' - promoted')
            _place(unit)
            written += 1
        else:
            print(word(unit, rel, detail, ok, words))
            if rel in REMEDY:
                print('    ' + REMEDY[rel].format(unit=unit.address))
            refused += 1
    _prune_empty(STAGE)
    print(f'{noun} promote: DONE - {written} promoted, {cleared} identical cleared, {refused} refused and left staged')
    return 1 if refused else 0


def main(argv: list[str]) -> int:
    """`input.py <noun> [--provider <p> | --all] [--id <prefix>]` - the promote verb of a
    capturing noun, its argv already validated against the noun's declaration."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('noun', choices=NOUNS)
    ap.add_argument('--provider', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--id', default=None)
    args = ap.parse_args(argv)
    if args.id is not None and args.provider is None:
        sys.exit('error: --id names a unit within a provider - say which with --provider')
    return promote(args.noun, extent(args.noun, args.provider, args.all, args.id))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
