"""
input.py - the room's input, tmp/input: where a captured unit stands to the held one of
its address, and whether the pipelines have found it valid (#687).

A capture writes what its source returned under tmp/input, at the address it will have
under data/input - tmp/input/<provider>/<channel>/<capture>/... - and reads nothing (L10).
Promotion is the one reduce over the room's input against the store, in two halves:

RELATION - one vocabulary, src/main/append_only.py's five relations, taken over a
measure per kind of unit; what differs per kind is the measure alone:

    claude session   the log's bytes, by prefix; the workspace beside it moves with it,
                     each file by prefix
    gemini session   its directory, measured by the full transcript's bytes by prefix;
                     the database and the summary move with it
    memory           a project's memory directory, a mirror of the room's own live
                     memory (single-writer by construction): identical, or replaced whole
    api capture      the set of message uuids the conversation holds
    dom capture      (human turns, total turns) of the rendered markdown
    export           a whole directory, held or not: never merged
    anything else    the bytes

VERDICT - the pipelines are the one validator; corpus-yoga pipeline run --overlay runs
them over the store with the room's input laid over it, and each datum's verdict is the
log the pipeline cached, at the family's latest version. Promotion reads those logs: a
unit is promotable when every family its pipeline declares for it has a current green
verdict - the log's datum digest the staged unit's own (or, for a converted datum, the
recorded digest of its source), and the log's schema digest that of origin/main's
version of the family, so that a form only a branch's schema admits waits for the merge
that licenses it. A unit no pipeline validates (a dom capture, a forge ledger) is
promoted on its relation alone, and says so.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SELF = 'src/main/input.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
from append_only import Relation, relate  # noqa: E402
from markdown_projection import turn_extent  # noqa: E402

STAGE = REPO / 'tmp' / 'input'
STORE = REPO / 'data' / 'input'
PIPELINE_ROOT = REPO / 'src' / 'main' / 'pipeline'
CACHE = REPO / 'tmp' / 'cache'


# -- units ---------------------------------------------------------------------------------

def kind(rel: Path) -> str:
    """The kind of unit at an address relative to data/input: <provider>/<channel>/<capture>/..."""
    parts = rel.parts
    if len(parts) >= 3:
        channel, capture = parts[1], parts[2]
        if channel == 'code':
            if len(parts) >= 6 and parts[5] == 'memory':
                return 'memory'
            return 'session'
        if capture == 'API-capture':
            return 'api'
        if capture == 'DOM-capture':
            return 'dom'
        if capture == 'bulk-export':
            return 'export'
    return 'bytes'


def units(root: Path) -> dict[Path, list[Path]]:
    """{unit address: its files' addresses}, both relative to root (tmp/input or
    data/input). A claude session's unit is <machine>/<project>/<session-id>, covering
    <session-id>.jsonl and the workspace <session-id>/; a gemini session's is its
    directory; a memory's is <project>/memory; an api or dom capture's is its
    conversation directory; an export's is its data-* directory; a file at a unit's
    address (an ordering capture, a manifest) and anything else is a unit of its own."""
    out: dict[Path, list[Path]] = {}
    for f in sorted(p for p in root.rglob('*') if p.is_file() and p.name != '.DS_Store'):
        rel = f.relative_to(root); parts = rel.parts; k = kind(rel)
        if k == 'memory':
            unit = Path(*parts[:6])
        elif k == 'session':
            if len(parts) == 6 and parts[5].endswith('.jsonl'):
                unit = Path(*parts[:5]) / parts[5][:-len('.jsonl')]      # the log names the unit
            elif len(parts) >= 6:
                unit = Path(*parts[:6])                                  # a workspace or a gemini session dir
            else:
                unit = rel
        elif k in ('api', 'dom', 'export') and len(parts) > 4:
            unit = Path(*parts[:4])
        else:
            unit = rel
        out.setdefault(unit, []).append(rel)
    return out


# -- relation ------------------------------------------------------------------------------

def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tree(root: Path, unit: Path) -> dict[str, bytes]:
    return {f.relative_to(root / unit).as_posix() if (root / unit).is_dir() else f.name: f.read_bytes()
            for f in sorted((root / unit).rglob('*')) if f.is_file()} if (root / unit).is_dir() else {}


def _log_of(root: Path, unit: Path) -> Path | None:
    """The append-only stream a session unit is measured by: claude's <unit>.jsonl, gemini's
    full transcript else its transcript."""
    if (root / unit).with_suffix('.jsonl').is_file():
        return (root / unit).with_suffix('.jsonl')
    for name in ('transcript_full.jsonl', 'transcript.jsonl'):
        if (root / unit / name).is_file():
            return root / unit / name
    return None


def _api_measure(unit_dir: Path):
    j = unit_dir / f'{unit_dir.name}.json'
    if not j.is_file():
        return None
    try:
        return {m['uuid'] for m in json.loads(j.read_text()).get('chat_messages', []) if m.get('uuid')}
    except ValueError:
        return None


def _by_set(incoming: set, existing: set | None) -> Relation:
    if existing is None:
        return Relation.ABSENT
    if incoming == existing:
        return Relation.IDENTICAL
    if existing <= incoming:
        return Relation.EXTENDS
    if incoming <= existing:
        return Relation.AHEAD
    return Relation.DIVERGED


def _by_extent(incoming, existing) -> Relation:
    """A scrape's (human turns, total turns) against the held one: an append-only
    conversation's extent only grows."""
    if existing is None:
        return Relation.ABSENT
    if incoming == existing:
        return Relation.IDENTICAL
    if incoming[0] >= existing[0] and incoming[1] >= existing[1]:
        return Relation.EXTENDS
    if incoming[0] <= existing[0] and incoming[1] <= existing[1]:
        return Relation.AHEAD
    return Relation.DIVERGED


def relation(unit: Path) -> tuple[Relation, str]:
    """Where the staged unit stands to the held one, and the measure's own words."""
    k = kind(unit)
    s, h = STAGE / unit, STORE / unit
    if k == 'session':
        log = _log_of(STAGE, unit)
        if log is None:
            if s.is_file():
                k = 'bytes'
            else:
                return Relation.DIVERGED, 'the staged session holds no log'
        else:
            held = _log_of(STORE, unit)
            incoming, existing = log.read_bytes(), (held.read_bytes() if held else None)
            r = relate(incoming, existing)
            return r, f'{len(existing or b"")} -> {len(incoming)} bytes of {log.name}'
    if k == 'memory':
        incoming, existing = _tree(STAGE, unit), _tree(STORE, unit)
        if not existing:
            return Relation.ABSENT, f'{len(incoming)} file(s)'
        if incoming == existing:
            return Relation.IDENTICAL, f'{len(incoming)} file(s)'
        removed = len(set(existing) - set(incoming))
        return Relation.EXTENDS, f"a mirror of this room's live memory: {len(existing)} -> {len(incoming)} file(s), {removed} removed"
    if s.is_file() and k in ('api', 'dom', 'export'):
        k = 'bytes'
    if k == 'export':
        if not h.exists():
            return Relation.ABSENT, 'a new export'
        return (Relation.IDENTICAL if _tree(STAGE, unit) == _tree(STORE, unit) else Relation.DIVERGED,
                'an export is held whole or not at all')
    if k == 'api':
        incoming, existing = _api_measure(s), (_api_measure(h) if h.exists() else None)
        if incoming is None:
            return Relation.DIVERGED, 'the staged capture holds no readable conversation json'
        return _by_set(incoming, existing), f'{len(existing or ())} -> {len(incoming)} message(s)'
    if k == 'dom':
        mds = sorted(s.glob('*.md'))
        if not mds:
            return Relation.DIVERGED, 'the staged scrape holds no markdown'
        incoming = max(turn_extent(m.read_text()) for m in mds)
        held_mds = sorted(h.glob('*.md')) if h.is_dir() else []
        existing = max(turn_extent(m.read_text()) for m in held_mds) if held_mds else None
        words = lambda m: f'{m[0]} human turns of {m[1]}'
        return _by_extent(incoming, existing), f'{words(existing) if existing else "nothing"} -> {words(incoming)}'
    incoming, existing = s.read_bytes(), (h.read_bytes() if h.exists() else None)
    return relate(incoming, existing), f'{len(existing or b"")} -> {len(incoming)} bytes'


# -- verdict -------------------------------------------------------------------------------

def pipelines() -> dict[str, dict]:
    return {d.name: json.loads((d / 'pipeline.json').read_text())
            for d in sorted(PIPELINE_ROOT.iterdir()) if (d / 'pipeline.json').is_file()}


def pipeline_of(unit: Path) -> str | None:
    """The pipeline whose declared input holds the unit's address, or None: the input
    with the unit's provider in place of <provider>, where the declaration's provider
    member names that provider."""
    provider = unit.parts[0]
    for name, facts in pipelines().items():
        if '<provider>' in facts['input'] and provider not in facts.get('provider', {}):
            continue
        rel = facts['input'].replace('<provider>', provider).removeprefix('data/input/')
        if unit.as_posix().startswith(rel + '/'):
            return name
    return None


def datum(unit: Path, pipeline: str) -> tuple[Path, dict[str, Path]]:
    """The cache directory the pipeline gives the unit's datum, and {family address:
    the file the family's log judged} - the pipelines' own cache layouts (run.sh of each),
    stated here once until #691 declares them."""
    k = kind(unit); p = unit.parts
    if pipeline == 'chat-capture':
        d = CACHE / 'chat-capture' / p[0] / p[3]
        return d, {f'{p[0]}/apiConversation': STAGE / unit / f'{p[3]}.json'}
    if pipeline == 'chat-export':
        d = CACHE / 'chat-export' / p[3]
        fams = {}
        for f in sorted((STAGE / unit).glob('*.json')):
            fams[f'{p[0]}/{f.stem}'] = f
        for f in sorted((STAGE / unit / 'projects').glob('*.json')):
            fams[f'{p[0]}/projects/{f.stem}'] = f
        return d, fams
    if pipeline == 'code-transport':
        if k == 'memory':
            d = CACHE / 'code-transport' / p[0] / p[3] / p[4] / 'memory'
            return d, {f'{p[0]}/projectMemory': d / 'memory.json'}
        d = CACHE / 'code-transport' / p[0] / p[3] / p[4] / p[5]
        return d, {f'{p[0]}/session': d / 'session.json', 'sessionConversation': d / 'conversation.json'}
    return CACHE / pipeline, {}


def _main_schema_digest(pipeline: str, family: str) -> tuple[str | None, str]:
    """The digest of origin/main's latest version file of a family, and its name."""
    fam_dir = f'rsc/schema/pipeline/{pipeline}/{family.split("/projects/")[0] if "/projects/" in family else family}'
    if '/projects/' in family:
        fam_dir = f'rsc/schema/pipeline/{pipeline}/{family.split("/")[0]}/projects'
    ls = subprocess.run(['git', '-C', str(REPO), 'ls-tree', '--name-only', 'origin/main', fam_dir + '/'], capture_output=True, text=True).stdout.split()
    versions = sorted((v for v in ls if v.rsplit('/', 1)[-1].startswith('v') and v.endswith('.json')),
                      key=lambda v: int(''.join(c for c in v.rsplit('/', 1)[-1] if c.isdigit()) or 0))
    if not versions:
        return None, '(no version at origin/main)'
    blob = subprocess.run(['git', '-C', str(REPO), 'show', f'origin/main:{versions[-1]}'], capture_output=True).stdout
    return _digest(blob), versions[-1].rsplit('/', 1)[-1][:-5]


def _source_digest(unit: Path) -> str | None:
    """What the pipeline converted a code unit from, digested as run.sh records it."""
    k = kind(unit)
    if k == 'memory':
        root = STAGE / unit
        lines = ''.join(f'{f.relative_to(root).as_posix()} {_digest(f.read_bytes())}\n'
                        for f in sorted(root.rglob('*')) if f.is_file() and f.name != '.DS_Store')
        return _digest(lines.encode())
    log = _log_of(STAGE, unit)
    return _digest(log.read_bytes()) if log else None


def verdict(unit: Path) -> tuple[bool | None, str]:
    """Whether the pipelines have found the staged unit valid at origin/main's versions:
    True, False with the reason, or None where no pipeline validates the unit's kind."""
    pipeline = pipeline_of(unit)
    if pipeline is None or kind(unit) in ('dom', 'bytes'):
        return None, 'no family validates it - promoted on its relation alone'
    d, families = datum(unit, pipeline)
    if not families:
        return False, f'no verdict - corpus-yoga pipeline run {pipeline} --overlay validates it'
    source = _source_digest(unit) if pipeline == 'code-transport' else None
    if pipeline == 'code-transport':
        recorded = (d / 'source.sha256')
        if not recorded.is_file() or recorded.read_text().strip() != source:
            return False, f'no verdict on this staged unit - corpus-yoga pipeline run {pipeline} --overlay converts and validates it'
    words = []
    for family, judged in families.items():
        leaf = family.rsplit('/', 1)[-1] if '/projects/' not in family else 'projects/' + family.rsplit('/', 1)[-1]
        logs = sorted((d / 'validation' / leaf).glob('v*.log'), key=lambda f: int(''.join(c for c in f.stem if c.isdigit()) or 0))
        if not logs or not judged.is_file():
            return False, f'no verdict at {family} - corpus-yoga pipeline run {pipeline} --overlay validates it'
        text = logs[-1].read_text().splitlines()
        if len(text) < 3 or not text[1].rstrip().endswith(f'sha256 {_digest(judged.read_bytes())}'):
            return False, f'the verdict at {family} is not on this staged unit - corpus-yoga pipeline run {pipeline} --overlay validates it'
        main_digest, main_version = _main_schema_digest(pipeline, family)
        if main_digest is None or not text[2].rstrip().endswith(f'sha256 {main_digest}'):
            return False, (f'the verdict at {family} is at {logs[-1].stem} of this checkout, which origin/main does not hold '
                           f'({main_version} there) - the mint\'s merge licenses the promotion')
        if 'Valid!' not in logs[-1].read_text():
            return False, f'fails {family} {logs[-1].stem} - a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)'
        words.append(f'{family} {logs[-1].stem}')
    return True, 'validates at ' + ', '.join(words) + ' (origin/main)'


# -- overlay -------------------------------------------------------------------------------

def overlay(out: Path) -> tuple[int, int]:
    """A view of data/input with this room's input laid over it, as a tree of links under
    out: every unit of the store linked at its address, then every staged unit linked over
    it. The pipelines read the view where they would read data/input, so a mint is tested
    over what the room has captured before the merge that licenses its promotion.
    Returns (units of data/input, units of tmp/input) linked."""
    if out.exists():
        shutil.rmtree(out)
    counts = []
    for root in (STORE, STAGE):
        n = 0
        if root.is_dir():
            for unit, files in units(root).items():
                for rel in (files if (root / unit).is_file() or not (root / unit).exists() else [unit]):
                    link = out / rel
                    if link.is_symlink() or link.exists():
                        link.unlink() if link.is_symlink() or link.is_file() else shutil.rmtree(link)
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(root / rel)
                n += 1
        counts.append(n)
    return counts[0], counts[1]
