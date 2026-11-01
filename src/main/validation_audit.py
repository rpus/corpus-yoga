#!/usr/bin/env python3
"""The validation-output judgments, spoken by the data gate (issues/535, issues/557): every
datum validates at each of its families' latest versions, its matrix.md agrees with
those logs, and every input entry has validation output. The latest version is the
schema; older versions are the CHANGELOG's history and are judged by nothing. One home - the dev gate held a
copy of these as its data tier and the two could disagree; now the commit gate
vets a commit's content and this verb vets the corpus, as `corpus-yoga pipeline
audit` and as the corpus tail's step. A violated property is a FAIL: atom,
counted by the run's stage table; the exit is 1 iff any FAIL was stated.
"""
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/validation_audit.py'
REPO = next(p for p in Path(__file__).resolve().parents if (p / SELF).is_file())
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main - the tier's shared modules
import tier  # noqa: E402 — the tiers, one home (issues/702)
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'model'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'cache'))
from validation_matrix import rows_from_records  # noqa: E402
import cache_io  # noqa: E402
import frontier  # noqa: E402
import corpus  # noqa: E402 — the one selection of units (issues/687)
import spell  # noqa: E402

SCHEMA_ROOT = REPO / 'rsc' / 'schema'


def parse_matrix_file(path: Path) -> dict[tuple[str, str, str], str]:
    """(schema, item, version) -> checkmark/cross/question parsed from a datum's matrix.md table."""
    rows: dict[tuple[str, str, str], str] = {}
    for line in path.read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 4:
            continue
        m = re.search(r'v\d+', cells[2])
        if not m or cells[3] not in ('✓', '✗', '?'):
            continue
        rows[(cells[0].strip('`'), cells[1].strip('`'), m.group())] = cells[3]
    return rows


def leaf(subject: str) -> str:
    """The subject's leaf (uuid/name) - labels never carry machine-derived slugs."""
    return subject.split(' / ')[-1]


def datum_dirs(cache_root: Path, depth: int) -> list[Path]:
    """Each datum directory under the cache root (the dirs holding a validation/ subdir)."""
    glob = '/'.join(['*'] * depth) + '/validation'
    return sorted(v.parent for v in cache_root.glob(glob) if v.is_dir())


def input_subjects(store: corpus.Store, root: Path | None = None) -> list:
    """Each input entry of a store as its cache subject - the units src/main/corpus.py
    selects for it under data/input (issues/687): a bare name at depth 1, where a datum is a
    directory, else the tuple of path parts the subject is cut to. An incomplete unit is
    passed over by the rehearsal and owes no output (issues/996)."""
    root = tier.DATA / 'input' if root is None else root
    units = [u for u in corpus.select(root, store) if not u.missing]
    if store.depth == 1:
        return sorted(u.subject[0] for u in units if (root / u.path).is_dir())
    return sorted({u.subject for u in units})


def _recorded(cache_dir: Path) -> str | None:
    """The digest an output records of what it was built from - source.sha256 beside it: one
    digest for a file, the listing of a directory's files with theirs - or None."""
    source = cache_dir / 'source.sha256'
    return source.read_text().strip() if source.is_file() else None


def _present(root: Path, unit: corpus.Unit) -> set[str]:
    """What the input is now, in every form an output may have recorded it: each selected
    file's digest, a directory's listing of its files with theirs, and that listing's digest."""
    import hashlib
    out: set[str] = set()
    for rel in unit.files:                # every file under the unit: a directory unit selects its directory
        if (root / rel).is_file():
            out.add(hashlib.sha256((root / rel).read_bytes()).hexdigest())
    top = root / unit.path
    if top.is_dir():
        lines = ''.join(f'{f.relative_to(top).as_posix()} {hashlib.sha256(f.read_bytes()).hexdigest()}\n'
                        for f in sorted(p for p in top.rglob('*') if p.is_file() and p.name != '.DS_Store'))
        out.add(lines.strip()); out.add(hashlib.sha256(lines.encode()).hexdigest())
    return out


def owed_units(store: corpus.Store, root: Path | None = None, cache_root: Path | None = None) -> dict[str, str]:
    """The inputs of a store a run is owed for (issues/1005), by subject: `unprocessed` where no
    output stands, `changed since its output` where the output records a digest the input no
    longer has. An incomplete unit is passed over (issues/996)."""
    root = tier.DATA / 'input' if root is None else root
    cache_root = (tier.path(cache_io.path_for(store.pipeline)) / (store.provider or '')) if cache_root is None else cache_root
    out: dict[str, str] = {}
    for unit in corpus.select(root, store):
        if unit.missing or (store.depth == 1 and not (root / unit.path).is_dir()):
            continue                      # passed over (issues/996), or no datum of the store's depth - as input_subjects counts
        subject = unit.subject[0] if store.depth == 1 else ' / '.join(unit.subject)
        cache_dir = cache_root / Path(*unit.subject)
        if not (cache_dir / 'validation').is_dir():
            out[subject] = 'unprocessed'
            continue
        recorded = _recorded(cache_dir)
        if recorded is not None and recorded not in _present(root, unit):
            out[subject] = 'changed since its output'
    return out


def owed_by_selection(name: str, facts: dict) -> dict[str, int]:
    """What a run of the pipeline would process, by the selection it declares (issues/1005): the
    count of inputs owed a run under each - the pipeline noun's standing."""
    counts: dict[str, int] = {}
    for source in sources(name, facts):
        owed = owed_units(source.store)
        if owed:
            key = f'{source.store.input.as_posix()}/{source.store.globs[0].pattern}'
            counts[key] = counts.get(key, 0) + len(owed)
    return counts


@dataclass(frozen=True)
class Source:
    """One store a pipeline reads, with where its validation output lies."""
    label: str                    # the pipeline, with the provider where the declared input carries one
    store: corpus.Store
    cache_root: Path              # the pipeline's cache root, a directory per provider under it


def sources(name: str, facts: dict) -> list[Source]:
    """Each store a pipeline reads: one, or one per provider where the declared input
    carries <provider> (issues/635) - the cache then holds a directory per provider under the
    pipeline's root. The stores are src/main/corpus.py's rows over the same declaration (issues/687)."""
    cache_root = tier.path(cache_io.path_for(name))
    return [Source(name if s.provider is None else f'{name}/{s.provider}', s, cache_root / (s.provider or ''))
            for s in corpus.stores({name: facts})]


def audit(name: str, facts: dict) -> int:
    """Every store the pipeline reads, judged alike; returns the number of FAIL atoms."""
    return sum(audit_source(name, source) for source in sources(name, facts))


def audit_source(pipeline: str, source: Source) -> int:
    """One pipeline's judgments over one store; returns the number of FAIL atoms stated. The
    latest version is the schema (issues/557): every datum validates at each family's latest, its
    matrix agrees with that log, and every input entry has validation output."""
    name, cache_root, depth = source.label, source.cache_root, source.store.depth
    schema_parent = SCHEMA_ROOT / 'pipeline' / pipeline
    fails = 0
    if not cache_root.is_dir() or not any(cache_root.iterdir()):
        print(f'{name}: no validation output in this room - nothing to audit')
        return 0
    print(f'{name}: each {cache_root.relative_to(REPO)}/<datum> against its families\' latest versions')
    processed: set[str] = set()
    matrices = [0, 0]; inputs = [0, 0]; at_latest = [0, 0]
    for datum_dir in datum_dirs(cache_root, depth):
        subject = ' / '.join(datum_dir.relative_to(cache_root).parts)
        expected = rows_from_records(datum_dir, schema_parent)
        if not expected:
            continue   # logs without records (issues/701): no judgment here - the input reads unprocessed below
        processed.add(subject)
        matrices[1] += 1
        for (family, item, version), (symbol, _bytes) in expected.items():
            at_latest[1] += 1
            if symbol == '✓':
                at_latest[0] += 1
            else:
                where = f'{leaf(subject)}' + (f' / {item}' if item else '')
                print(f'FAIL: {where}: {name}/{family} does not validate at latest {version} - '
                      f'a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)')
                fails += 1
        mfile = datum_dir / 'matrix.md'
        if not mfile.exists():
            print(f'FAIL: {name}: matrix missing: {leaf(subject)} - {mfile.relative_to(REPO)}; '
                  f'to regenerate: {spell.line("pipeline", "sync", pipeline)}')
            fails += 1
            continue
        if parse_matrix_file(mfile) != {k: sym for k, (sym, _) in expected.items()}:
            print(f'FAIL: {name}: matrix stale: {leaf(subject)} - matrix.md disagrees with its '
                  f'latest-version logs; to regenerate: {spell.line("pipeline", "sync", pipeline)}')
            fails += 1
            continue
        matrices[0] += 1
    raw = input_subjects(source.store)
    owed = owed_units(source.store)
    for subject in sorted(raw if depth == 1 else [' / '.join(parts) for parts in raw]):
        inputs[1] += 1
        if subject not in processed:
            print(f'FAIL: {name}: input unprocessed: {leaf(subject)} - no validation output under '
                  f'{cache_root.relative_to(REPO)}/; {spell.line("pipeline", "run", pipeline)}')
            fails += 1
        elif owed.get(subject) == 'changed since its output':
            # the output records the digest it was built from, and the input no longer has it (issues/1005)
            print(f'FAIL: {name}: input changed since its output: {leaf(subject)} - the output under '
                  f'{cache_root.relative_to(REPO)}/ was built from other bytes; {spell.line("pipeline", "run", pipeline)}')
            fails += 1
        else:
            inputs[0] += 1
    print(f'{name}: matrices current {matrices[0]}/{matrices[1]} · '
          f'inputs processed {inputs[0]}/{inputs[1]} · '
          f'validates at latest {at_latest[0]}/{at_latest[1]}')
    return fails


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for name, facts in frontier.pipelines():
        if only and name != only:
            continue
        total += audit(name, facts)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
