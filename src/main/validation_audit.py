#!/usr/bin/env python3
"""The validation-output judgments, spoken by the data gate (#535): each datum's
matrix.md exists and agrees with the vN.log files beside it; every schema version
is registered by some datum; every input entry has validation output; every
datum validates against at least one version. One home - the dev gate held a
copy of these as its data tier and the two could disagree; now the commit gate
vets a commit's content and this verb vets the corpus, as `corpus-yoga pipeline
audit` and as the corpus tail's step. A violated property is a FAIL: atom,
counted by the run's stage table; the exit is 1 iff any FAIL was stated.
"""
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/validation_audit.py'
REPO = next(p for p in Path(__file__).resolve().parents if (p / SELF).is_file())
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'model'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'cache'))
from validation_matrix import rows_from_logs  # noqa: E402
import cache_io  # noqa: E402
import frontier  # noqa: E402

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


def input_subjects(input_root: Path, globs: list[str], depth: int) -> list:
    """Each input entry as its cache subject: a bare name at depth 1, else the tuple of
    path parts relative to the input root (files contribute their stem)."""
    if not input_root.exists():
        return []
    if depth == 1:
        return sorted(d.name for g in globs for d in input_root.glob(g.rstrip('/')) if d.is_dir())
    result = []
    for pattern in globs:
        glob, dirs_only = pattern.rstrip('/'), pattern.endswith('/')
        for item in sorted(input_root.glob(glob)):
            if item.is_dir() != dirs_only:
                continue
            rel = item.relative_to(input_root)
            result.append(rel.parts[:-1] + (item.name if dirs_only else item.stem,))
    return sorted(result)


def audit(name: str, facts: dict) -> int:
    """One pipeline's judgments; returns the number of FAIL atoms stated."""
    cache_root = REPO / cache_io.path_for(name)
    input_root = REPO / facts['input']
    depth = facts['subject_depth']
    fails = 0
    if not cache_root.is_dir() or not any(cache_root.iterdir()):
        print(f'{name}: no validation output in this room - nothing to audit')
        return 0
    print(f'{name}: each {cache_root.relative_to(REPO)}/<datum>/matrix.md against the vN.log files beside it')
    seen_versions: dict[str, set[str]] = {}
    processed: set[str] = set()
    for datum_dir in datum_dirs(cache_root, depth):
        subject = ' / '.join(datum_dir.relative_to(cache_root).parts)
        processed.add(subject)
        expected = rows_from_logs(datum_dir)
        for (schema, _item, version) in expected:
            seen_versions.setdefault(schema, set()).add(version)
        mfile = datum_dir / 'matrix.md'
        if not mfile.exists():
            print(f'FAIL: {name}: matrix missing: {leaf(subject)} - {mfile.relative_to(REPO)}; '
                  f'to regenerate: corpus-yoga pipeline sync {name}')
            fails += 1
            continue
        if parse_matrix_file(mfile) != {k: sym for k, (sym, _) in expected.items()}:
            print(f'FAIL: {name}: matrix stale: {leaf(subject)} - matrix.md disagrees with its '
                  f'validation logs; to regenerate: corpus-yoga pipeline sync {name}')
            fails += 1
    for family in facts['schemas']:
        for vpath in frontier.sorted_versions(SCHEMA_ROOT / name / family):
            if vpath.stem not in seen_versions.get(family, set()):
                print(f'FAIL: {name}/{family}: version unregistered: {vpath.stem} - no datum in '
                      f'this room has validated against it; corpus-yoga pipeline run {name}')
                fails += 1
    globs = [g for g in (facts['input_glob'], facts.get('extra_input_glob', '')) if g]
    raw = input_subjects(input_root, globs, depth)
    for subject in sorted(raw if depth == 1 else [' / '.join(parts) for parts in raw]):
        if subject not in processed:
            print(f'FAIL: {name}: input unprocessed: {leaf(subject)} - no validation output under '
                  f'{cache_root.relative_to(REPO)}/; corpus-yoga pipeline run {name}')
            fails += 1
    primary = facts['schemas'][0]
    versions = frontier.sorted_versions(SCHEMA_ROOT / name / primary)
    for subject, leaf_dir in frontier.subject_dirs(cache_root, depth):
        logs = [leaf_dir / 'validation' / primary / f'{v.stem}.log' for v in versions]
        logs = [l for l in logs if l.exists()]
        if logs and not any('Valid!' in l.read_text() for l in logs):
            print(f'FAIL: {name}/{primary}: unmodelled: {leaf(subject)} - validates against no '
                  f'schema version; a version is owed (rsc/schema/WORKFLOW.md)')
            fails += 1
    print(f'{name}: {len(processed)} datum(s) audited, {fails} finding(s)')
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
