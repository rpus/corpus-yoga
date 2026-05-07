#!/usr/bin/env python
"""
pre_commit.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/pre_commit.sh

As a git hook, install the wrapper:
    ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Atomic diagnostic scripts live in src/test/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import csv
import io
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Repo layout ───────────────────────────────────────────────────────────────
REPO_ROOT                = Path(__file__).resolve().parents[2]
REPO_PARENT              = REPO_ROOT.parent
GEN                      = REPO_ROOT / 'gen'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
RSC_SCHEMA               = RSC / 'schema'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

# Prefix for converting bare project names to ~/.claude/projects/ slugs and back.
# slug = _PROJECT_PREFIX + name;  name = slug.removeprefix(_PROJECT_PREFIX)
_PROJECT_PREFIX = str(REPO_PARENT).replace('/', '-') + '-'

# naming.root_schema_title_matches_filename — universal: versioned files named v*.json, not by title.
# composition.base_schemas_closed — session deviation: TurnBase intentionally open (see principles.md).
_SKIP_BASE = frozenset({'naming.root_schema_title_matches_filename'})

# ── Pipeline model ────────────────────────────────────────────────────────────

@dataclass
class Pipeline:
    schemas:        list[str]
    changelog:      Path
    gen:            Path
    input:          Path
    input_glob:     str
    subject_depth:  int
    validate_cmd:   str
    diagnostic_skip:dict[str, frozenset[str]] | None = None  # schema → diagnostic ids to skip; None = _SKIP_BASE for all schemas
    gen_key_prefix: str = ''

    def __post_init__(self):
        if self.diagnostic_skip is None:
            self.diagnostic_skip = {s: _SKIP_BASE for s in self.schemas}

PIPELINES: dict[str, Pipeline] = {
    'browser-captures': Pipeline(
        schemas        = ['apiConversation'],
        changelog      = RSC_SCHEMA / 'apiConversation' / 'CHANGELOG.md',
        gen            = GEN / 'browser-captures',
        input          = REPO_PARENT / 'browser-captures',
        input_glob     = 'data-*/*/',
        subject_depth  = 2,
        validate_cmd   = 'src/main/browser-captures/validate.sh --batches',
    ),
    'chat-exports': Pipeline(
        schemas        = ['conversations', 'memories', 'projects', 'users'],
        changelog      = RSC_SCHEMA / 'conversations' / 'CHANGELOG.md',
        gen            = GEN / 'chat-exports',
        input          = REPO_PARENT / 'chat-exports',
        input_glob     = 'data-*/',
        subject_depth  = 1,
        validate_cmd   = 'src/main/chat-exports/RUNME.sh --chat-exports',
    ),
    'code-projects': Pipeline(
        schemas        = ['session'],
        changelog      = RSC_SCHEMA / 'session' / 'CHANGELOG.md',
        gen            = GEN / 'code-projects',
        input          = REPO_PARENT / 'code-projects',
        input_glob     = '-Users-*/*.jsonl',
        subject_depth  = 2,
        validate_cmd   = 'src/main/code-projects/RUNME.sh --code-projects',
        diagnostic_skip= {'session': _SKIP_BASE | {'composition.base_schemas_closed'}},
        gen_key_prefix = _PROJECT_PREFIX,
    ),
}

VERSIONED_SCHEMA_DIAGNOSTICS_SKIP = {
    schema: skip
    for pipeline in PIPELINES.values()
    for schema, skip in (pipeline.diagnostic_skip or {}).items()
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _call(script, *args):
    result = subprocess.run(
        [sys.executable, str(script)] + list(args),
        capture_output=True, text=True
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def _walk_pointer(doc: object, pointer: str) -> bool:
    node: Any = doc
    for tok in pointer.lstrip('/').split('/'):
        tok = tok.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(node, dict):
                node = node[tok]
            elif isinstance(node, list):
                node = node[int(tok)]
            else:
                return False
        except (KeyError, IndexError, ValueError):
            return False
    return True


def _diag_detail(output):
    lines = output.splitlines()
    if len(lines) > 1:
        return '\n    '.join(lines[1:])
    return lines[0] if lines else None


def _parse_changelog_matrix(changelog: Path) -> dict[tuple[str, str], bool]:
    """Parse the pass/fail matrix from a schema changelog markdown table.
    Returns {(subject, version): True=pass, False=fail}."""
    matrix: dict[tuple[str, str], bool] = {}
    version_cols: list[tuple[int, str]] = []
    for line in changelog.read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not version_cols:
            cols = [(i, m.group(1)) for i, c in enumerate(cells)
                    if (m := re.match(r'\[(v\d+)\]', c))]
            if cols:
                version_cols = cols
            continue
        if all(re.match(r'[-: ]+$', c) for c in cells if c):
            continue
        subject = cells[0].replace('`', '').strip()
        if not subject:
            continue
        for col_i, version in version_cols:
            if col_i < len(cells):
                if '✓' in cells[col_i]:
                    matrix[(subject, version)] = True
                elif '✗' in cells[col_i]:
                    matrix[(subject, version)] = False
    return matrix


def _sorted_versions(schema_dir: Path) -> list[Path]:
    """Return all v*.json in schema_dir sorted by version number ascending."""
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )



def _abbrev(s: str, n: int = 8) -> str:
    return s[:n] + '…' if len(s) > n else s


def _input_subjects(pipeline: Pipeline) -> list:
    if not pipeline.input.exists():
        return []
    glob      = pipeline.input_glob.rstrip('/')
    dirs_only = pipeline.input_glob.endswith('/')
    if pipeline.subject_depth == 1:
        return sorted(d.name for d in pipeline.input.glob(glob) if d.is_dir())
    result = []
    for item in sorted(pipeline.input.glob(glob)):
        if item.is_dir() and dirs_only:
            result.append((item.parent.name, item.name))
        elif not item.is_dir() and not dirs_only:
            result.append((item.parent.name.removeprefix(pipeline.gen_key_prefix), item.stem))
    return result


def _check_csv_pointers(csv_path: Path, columns: tuple, base_for: dict, fails: list) -> None:
    """Validate JSON Pointer fragments in a join CSV. base_for maps column name → base dir."""
    with csv_path.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in columns:
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (base_for.get(col, RSC_SCHEMA / 'conversations') / file_part).resolve()
                if not f.exists():
                    fails.append(f'row {i} {col}: file not found: {file_part}')
                    continue
                if pointer and f.suffix == '.json':
                    try:
                        doc = json.loads(f.read_text())
                    except json.JSONDecodeError:
                        fails.append(f'row {i} {col}: invalid JSON: {file_part}')
                        continue
                    if not _walk_pointer(doc, pointer):
                        fails.append(f'row {i} {col}: bad pointer: {ref}')


# ── Checks ────────────────────────────────────────────────────────────────────

def check_required_files(run):
    schema_versions = [v for d in sorted(RSC_SCHEMA.iterdir())
                       if d.is_dir() and not d.name.startswith('_')
                       for v in _sorted_versions(d)]
    required = [
        RSC_SCHEMA / 'conversations' / 'principles.md',
        RSC_SCHEMA / 'conversations' / 'workflow.md',
        RSC_SCHEMA / 'session'       / 'principles.md',
        RSC_SCHEMA / 'session'       / 'workflow.md',
        *schema_versions,
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'chat-exports'    / 'validate.sh',
        SRC  / 'main' / 'browser-captures' / 'validate.sh',
        SRC  / 'test' / 'gen_model_candidate.py',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'test' / 'gen_model.py',
        SRC  / 'run_python_script.sh',
        RSC  / 'model.json',
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists())


def check_root_schema_diagnostics(run):
    root_schemas = sorted(RSC_SCHEMA.glob('*.json'))
    diagnostics  = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))

    for schema_path in root_schemas:
        for script in diagnostics:
            diag = script.stem
            passed, output = _call(script, str(schema_path))
            run(f'{diag}: {schema_path.relative_to(RSC_SCHEMA)}', passed,
                _diag_detail(output) if not passed else None)


def check_pipeline_validity(run, pipeline: Pipeline) -> None:
    for schema_name in pipeline.schemas:
        versions = _sorted_versions(RSC_SCHEMA / schema_name)
        if not versions:
            run(f'{schema_name}: valid JSON', False,
                f'{(RSC_SCHEMA / schema_name).relative_to(REPO_ROOT)} has no v*.json files')
            continue
        for path in versions:
            v = path.stem
            try:
                schema = json.loads(path.read_text())
                run(f'{schema_name}: valid JSON + $schema: {v}', '$schema' in schema,
                    'Missing $schema field' if '$schema' not in schema else None)
            except json.JSONDecodeError as e:
                run(f'{schema_name}: valid JSON: {v}', False, str(e))


def check_pipeline_validation_outputs(run, name: str, pipeline: Pipeline) -> None:
    schema   = pipeline.changelog.parent.name
    matrix   = _parse_changelog_matrix(pipeline.changelog)
    run_cmd  = f'src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {name} --write'
    if pipeline.subject_depth == 1:
        _check_validation_outputs_depth1(run, name, pipeline, schema, matrix, run_cmd)
    else:
        _check_validation_outputs_depth2(run, name, pipeline, schema, matrix, run_cmd)


def _check_validation_outputs_depth1(run, name, pipeline, schema, matrix, run_cmd):
    gen_dirs = sorted(d.name for d in pipeline.gen.iterdir() if d.is_dir()) \
               if pipeline.gen.exists() else []

    for (subject, version), expected_pass in sorted(matrix.items()):
        log = pipeline.gen / subject / 'validation' / schema / f'{version}.log'
        if not log.exists():
            run(f'{schema}: validation log exists: {subject} × {version}', False,
                f'Run: {pipeline.validate_cmd} ../{name}')
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{schema}: validation {"passing" if expected_pass else "failing"}: {subject} × {version}'
        run(label, actual_pass == expected_pass,
            f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}'
            if actual_pass != expected_pass else None)

    registered = {subj for subj, _ in matrix}
    for subject in gen_dirs:
        log_dir = pipeline.gen / subject / 'validation' / schema
        if not log_dir.exists():
            continue
        for log in sorted(log_dir.glob('v*.log')):
            version = log.stem
            if (subject, version) in matrix:
                continue
            content = log.read_text()
            result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
            run(f'{schema}: unregistered: {subject} × {version} — {result}', False,
                str(log.relative_to(REPO_ROOT)))

    for subject in _input_subjects(pipeline):
        if subject not in registered:
            run(f'{schema}: unregistered: {subject}', False,
                f'Run: {pipeline.validate_cmd} ../{name}, then: {run_cmd}')


def _check_validation_outputs_depth2(run, name, pipeline, schema, matrix, run_cmd):
    registered: dict[str, list[tuple[str, str]]] = {}  # part1 → [(prefix, subject), ...]
    for (subject, _) in matrix:
        part1, _, prefix = subject.partition(' / ')
        registered.setdefault(part1.strip(), []).append((prefix.strip(), subject))

    gen_level1_dirs = sorted(d for d in pipeline.gen.iterdir() if d.is_dir()) \
                      if pipeline.gen.exists() else []

    for (subject, version), expected_pass in sorted(matrix.items()):
        part1, _, part2_prefix = subject.partition(' / ')
        part1, part2_prefix = part1.strip(), part2_prefix.strip()
        gen_level1 = pipeline.gen / (pipeline.gen_key_prefix + part1)
        matches = [u for u in (sorted(gen_level1.iterdir()) if gen_level1.exists() else [])
                   if u.is_dir() and u.name.startswith(part2_prefix)]
        lp = f'{_abbrev(part1)}/{part2_prefix}…'
        if not matches:
            run(f'{schema}: validation log exists: {lp} × {version}', False,
                f'Run: {pipeline.validate_cmd} ../{name}')
            continue
        log = matches[0] / 'validation' / schema / f'{version}.log'
        if not log.exists():
            run(f'{schema}: validation log exists: {lp} × {version}', False,
                f'Run: {pipeline.validate_cmd} ../{name}')
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{schema}: validation {"passing" if expected_pass else "failing"}: {lp} × {version}'
        run(label, actual_pass == expected_pass,
            f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}'
            if actual_pass != expected_pass else None)

    for gen_level1 in gen_level1_dirs:
        part1 = gen_level1.name.removeprefix(pipeline.gen_key_prefix)
        ps    = registered.get(part1, [])
        for uuid_dir in sorted(u for u in gen_level1.iterdir() if u.is_dir()):
            log_dir = uuid_dir / 'validation' / schema
            if not log_dir.exists():
                continue
            match          = next(((p, s) for p, s in ps if uuid_dir.name.startswith(p)), (None, None))
            prefix, subject = match
            for log in sorted(log_dir.glob('v*.log')):
                version = log.stem
                if prefix and (subject, version) in matrix:
                    continue
                content = log.read_text()
                result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
                run(f'{schema}: unregistered: {_abbrev(part1)}/{uuid_dir.name[:8]}… × {version} — {result}', False)

    for part1, part2 in _input_subjects(pipeline):
        ps = registered.get(part1, [])
        if not any(part2.startswith(p) for p, _ in ps):
            run(f'{schema}: unregistered: {_abbrev(part1)}/{part2[:8]}…', False,
                f'Run: {pipeline.validate_cmd} ../{name}, then: {run_cmd}')


def check_versioned_schema_diagnostics(run):
    all_diagnostics = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))

    for schema_name, skip in sorted(VERSIONED_SCHEMA_DIAGNOSTICS_SKIP.items()):
        versions    = _sorted_versions(RSC_SCHEMA / schema_name)
        diagnostics = [s for s in all_diagnostics if s.stem not in skip]
        if not versions:
            run(f'{schema_name}: no versions', False,
                f'{(RSC_SCHEMA / schema_name).relative_to(REPO_ROOT)} has no v*.json files')
            continue
        for version in versions:
            for script in diagnostics:
                passed, output = _call(script, str(version))
                run(f'{schema_name}: {script.stem}: {version.stem}', passed,
                    _diag_detail(output) if not passed else None)


def check_schema_join(run):
    join = RSC_SCHEMA / 'model_join.csv'
    if not join.exists():
        run('schema model_join.csv exists', False)
        return
    fails: list[str] = []
    _check_csv_pointers(join,
                        ('conv_path', 'session_path', 'api_path', 'mcp_path'),
                        {'conv_path':    RSC_SCHEMA,
                         'session_path': RSC_SCHEMA / 'session',
                         'api_path':     RSC_SCHEMA,
                         'mcp_path':     RSC_SCHEMA},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


def check_xref(run):
    _, output = _call(SRC / 'test' / 'xref.py')
    summary = output.splitlines()[-1] if output else ''
    m_bad  = re.search(r'(\d+) bad-pointer',   summary)
    m_miss = re.search(r'(\d+) missing-file',  summary)
    bad    = int(m_bad.group(1))  if m_bad  else 0
    miss   = int(m_miss.group(1)) if m_miss else 0
    run('xref: no bad pointers',        bad  == 0, summary if bad  else None)
    run(f'xref: {miss} missing-file references', True)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    results = []
    buf = io.StringIO()

    def run(label, passed, detail=None):
        results.append((label, passed, detail))
        mark = '✓' if passed else '✗'
        print(f'  {mark} {label}' + (f'\n      {detail}' if not passed and detail else ''))

    section_of: list[str] = []

    def run_section(fn, label=None):
        name = label or fn.__name__
        print(f'\n── {name} {"─" * (74 - len(name))}')
        before = len(results)
        ret = fn(run)
        section_of.extend([name] * (len(results) - before))
        return ret

    sys.stdout = buf
    try:
        run_section(check_required_files)
        run_section(check_root_schema_diagnostics)

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, p=_pipeline: check_pipeline_validity(run, p),
                        label=f'check_{_slug}_validity')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline: check_pipeline_validation_outputs(run, n, p),
                        label=f'check_{_slug}_validation_outputs')

        run_section(check_versioned_schema_diagnostics)

        run_section(check_schema_join)
        run_section(check_xref)
    finally:
        sys.stdout = sys.__stdout__

    passes   = sum(1 for _, p, _ in results if p)
    failures = [(n, d) for n, p, d in results if not p]
    total    = len(results)

    failed_sections = list(dict.fromkeys(
        section_of[i] for i, (_, p, _) in enumerate(results) if not p
    ))

    # ── HEAD ──────────────────────────────────────────────────────────────────
    if failures:
        print(f'`src/test/pre_commit.py`: {passes}/{total} (failures in {len(failed_sections)} sections)')
    else:
        print(f'pre_commit.py: {total}/{total}')

    # ── BODY ──────────────────────────────────────────────────────────────────
    print()
    print(buf.getvalue(), end='')

    # ── TAIL ──────────────────────────────────────────────────────────────────
    if failures:
        failure_counts = {s: sum(1 for i, (_, p, _) in enumerate(results) if not p and section_of[i] == s)
                         for s in failed_sections}
        print(f'Failed sections ({len(failed_sections)}):')
        for s in failed_sections:
            print(f'  {s} ({failure_counts[s]})')
        print()

        fix_commands: list[str] = []
        seen: set[str] = set()

        def _add(cmd: str) -> None:
            if cmd not in seen:
                fix_commands.append(cmd)
                seen.add(cmd)

        for name, detail in failures:
            if detail and detail.startswith('Run: '):
                _add(detail[len('Run: '):])
            else:
                parts = name.split(': ')
                if len(parts) == 3 and re.match(r'[a-z_]+\.[a-z_]+', parts[1]):
                    diag, schema_path = parts[1], RSC_SCHEMA / parts[0] / f'{parts[2]}.json'
                    repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                    diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                    if repair.exists() and schema_path.exists():
                        _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                    elif diagnostic.exists() and schema_path.exists():
                        _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                elif len(parts) == 2 and re.match(r'[a-z_]+\.[a-z_]+', parts[0]):
                    diag, schema_path = parts[0], RSC_SCHEMA / parts[1]
                    repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                    diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                    if repair.exists() and schema_path.exists():
                        _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                    elif diagnostic.exists() and schema_path.exists():
                        _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')

        if fix_commands:
            print()
            print('To fix:')
            for cmd in fix_commands:
                print(f'  {cmd}')

        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
