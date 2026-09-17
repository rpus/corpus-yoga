#!/usr/bin/env python3
"""The validation-output judgments, spoken by the data gate (#535, #557): every
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
    path parts relative to the input root (files contribute their stem), cut to the
    subject's depth - a glob may select a file inside the subject's directory (a gemini
    session's transcript), and several such files are one subject."""
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
            result.append((rel.parts[:-1] + (item.name if dirs_only else item.stem,))[:depth])
    return sorted(set(result))


def sources(name: str, facts: dict) -> list[tuple[str, Path, Path, list[str]]]:
    """(label, input root, cache root, globs) for each store a pipeline reads: one, or one
    per provider where the declared input carries <provider> (#635) - the cache then
    holds a directory per provider under the pipeline's root."""
    cache_root = REPO / cache_io.path_for(name)
    if '<provider>' not in facts['input']:
        globs = [g for g in (facts['input_glob'], facts.get('extra_input_glob', '')) if g]
        return [(name, REPO / facts['input'], cache_root, globs)]
    return [(f'{name}/{p}', REPO / facts['input'].replace('<provider>', p), cache_root / p,
             [g for g in (f['input_glob'], f.get('extra_input_glob', '')) if g])
            for p, f in sorted(facts['provider'].items())]


def audit(name: str, facts: dict) -> int:
    """Every store the pipeline reads, judged alike; returns the number of FAIL atoms."""
    return sum(audit_source(name, label, input_root, cache_root, globs, facts['subject_depth'])
               for label, input_root, cache_root, globs in sources(name, facts))


def audit_source(pipeline: str, name: str, input_root: Path, cache_root: Path, globs: list[str], depth: int) -> int:
    """One pipeline's judgments; returns the number of FAIL atoms stated. The latest
    version is the schema (#557): every datum validates at each family's latest, its
    matrix agrees with that log, and every input entry has validation output."""
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
        processed.add(subject)
        matrices[1] += 1
        expected = rows_from_logs(datum_dir, schema_parent)
        for (family, item, version), (symbol, _bytes) in expected.items():
            at_latest[1] += 1
            if symbol == '✓':
                at_latest[0] += 1
            else:
                where = f'{leaf(subject)}' + (f' / {item}' if item else '')
                print(f'FAIL: {name}/{family}: does not validate at latest {version}: {where} - '
                      f'a version is owed, or the datum is ruled out (rsc/schema/WORKFLOW.md)')
                fails += 1
        mfile = datum_dir / 'matrix.md'
        if not mfile.exists():
            print(f'FAIL: {name}: matrix missing: {leaf(subject)} - {mfile.relative_to(REPO)}; '
                  f'to regenerate: corpus-yoga pipeline sync {pipeline}')
            fails += 1
            continue
        if parse_matrix_file(mfile) != {k: sym for k, (sym, _) in expected.items()}:
            print(f'FAIL: {name}: matrix stale: {leaf(subject)} - matrix.md disagrees with its '
                  f'latest-version logs; to regenerate: corpus-yoga pipeline sync {pipeline}')
            fails += 1
            continue
        matrices[0] += 1
    raw = input_subjects(input_root, globs, depth)
    for subject in sorted(raw if depth == 1 else [' / '.join(parts) for parts in raw]):
        inputs[1] += 1
        if subject not in processed:
            print(f'FAIL: {name}: input unprocessed: {leaf(subject)} - no validation output under '
                  f'{cache_root.relative_to(REPO)}/; corpus-yoga pipeline run {pipeline}')
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
