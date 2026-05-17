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
EXT                      = REPO_ROOT / 'ext'
GEN                      = REPO_ROOT / 'gen'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
RSC_SCHEMA               = RSC / 'schema'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

# ── Pipeline model ────────────────────────────────────────────────────────────

@dataclass
class Pipeline:
    schemas:         list[str]
    changelog:       Path
    gen:             Path
    input:           Path
    input_glob:      str
    subject_depth:   int
    validate_cmd:    str
    # Extra diagnostics to skip beyond the universal versioned-schema skip set.
    # composition.base_schemas_closed — session deviation: TurnBase intentionally open (see principles.md).
    diagnostic_skip:    frozenset[str] = frozenset()
    gen_key_prefix:     str = ''
    slug_prefix:        str = ''
    subject_header:     str = ''
    dir_col:            str = ''
    uuid_col:           str = ''
    changelog_footer:   str = ''

PIPELINES: dict[str, Pipeline] = {
    'browser-captures': Pipeline(
        schemas           = ['apiConversation'],
        changelog         = RSC_SCHEMA / 'browser-captures' / 'apiConversation' / 'CHANGELOG.md',
        gen               = GEN / 'browser-captures',
        input             = EXT / 'browser-captures',
        input_glob        = 'data-*/*/',
        subject_depth     = 2,
        validate_cmd      = 'src/main/browser-captures/RUNME.sh --browser-captures',
        subject_header    = 'Export',
        dir_col           = 'Batch dir',
        uuid_col          = 'Conversation UUID',
        changelog_footer  = ('Export: batch directory name. Batch dir: same. '
                             'Conversation UUID: full conversation UUID. '
                             'Bytes: size of the captured JSON file at validation time.'),
    ),
    'chat-exports': Pipeline(
        schemas           = ['conversations', 'memories', 'projects', 'users'],
        changelog         = RSC_SCHEMA / 'chat-exports' / 'conversations' / 'CHANGELOG.md',
        gen               = GEN / 'chat-exports',
        input             = EXT / 'chat-exports',
        input_glob        = 'data-*/',
        subject_depth     = 1,
        validate_cmd      = 'src/main/chat-exports/RUNME.sh --chat-exports',
        subject_header    = 'Export',
        changelog_footer  = 'Bytes: size of `conversations.json` at validation time.',
    ),
    'code-projects': Pipeline(
        schemas           = ['session'],
        changelog         = RSC_SCHEMA / 'code-projects' / 'session' / 'CHANGELOG.md',
        gen               = GEN / 'code-projects',
        input             = EXT / 'code-projects',
        input_glob        = '-Users-*/*.jsonl',
        subject_depth     = 2,
        validate_cmd      = 'src/main/code-projects/RUNME.sh --code-projects',
        diagnostic_skip   = frozenset({'composition.base_schemas_closed'}),
        slug_prefix       = str(Path.home()).replace('/', '-'),
        subject_header    = 'Repo',
        dir_col           = 'Code project',
        uuid_col          = 'Session UUID',
        changelog_footer  = ('Repo: last component of the `~/.claude/projects/` slug. '
                             'Code project: full slug from `~/.claude/projects/`. '
                             'Session UUID: full session `.jsonl` filename stem. '
                             'Bytes: size of the `.jsonl` file at validation time.'),
    ),
}

# Map schema name → its directory, derived from PIPELINES.
SCHEMA_DIR: dict[str, Path] = {
    schema: RSC_SCHEMA / name / schema
    for name, pipeline in PIPELINES.items()
    for schema in pipeline.schemas
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


def _parse_changelog_matrix(pipeline: 'Pipeline') -> dict[tuple[str, str], bool]:
    """Parse the pass/fail matrix from a schema changelog markdown table.
    Returns {(subject, version): True=pass, False=fail}.

    When pipeline.dir_col and pipeline.uuid_col are set, those columns supply the
    subject as '{dir} / {uuid}'. Rows missing either value are skipped.
    Otherwise subject is cells[0].
    """
    use_path_cols = bool(pipeline.dir_col and pipeline.uuid_col)
    matrix: dict[tuple[str, str], bool] = {}
    version_cols:    list[tuple[int, str]] = []
    dir_col_idx:     int | None = None
    uuid_col_idx:    int | None = None
    for line in pipeline.changelog.read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if not version_cols:
            cols = [(i, m.group(1)) for i, c in enumerate(cells)
                    if (m := re.match(r'\[(v\d+)\]', c))]
            if cols:
                version_cols = cols
                if use_path_cols:
                    for i, c in enumerate(cells):
                        label = c.replace('`', '').strip()
                        if label == pipeline.dir_col:
                            dir_col_idx = i
                        elif label == pipeline.uuid_col:
                            uuid_col_idx = i
            continue
        if all(re.match(r'[-: ]+$', c) for c in cells if c):
            continue
        if use_path_cols and dir_col_idx is not None and uuid_col_idx is not None:
            cp  = cells[dir_col_idx].replace('`', '').strip()  if dir_col_idx  < len(cells) else ''
            uid = cells[uuid_col_idx].replace('`', '').strip() if uuid_col_idx < len(cells) else ''
            if not cp or not uid:
                continue
            if pipeline.slug_prefix and not cp.startswith(pipeline.slug_prefix):
                cp = pipeline.slug_prefix + cp
            subject = f'{cp} / {uid}'
        else:
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
    schema_versions = [v
                       for d in sorted(RSC_SCHEMA.iterdir())
                       if d.is_dir() and not d.name.startswith('_')
                       for schema_d in sorted(d.iterdir())
                       if schema_d.is_dir()
                       for v in _sorted_versions(schema_d)]
    required = [
        *[p.changelog.parent / doc
          for p in PIPELINES.values()
          for doc in ('principles.md', 'workflow.md')],
        *schema_versions,
        *[SRC / 'main' / name / 'validate.sh' for name in PIPELINES],
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'model' / 'gen_model_candidate.py',
        SRC  / 'main' / 'model' / 'gen_model.py',
        SRC  / 'test' / 'pre_commit_expected_score',
        SRC  / 'test' / 'xref_expected_score',
        SRC  / 'main' / 'schema_recommendations.py',
        SRC  / 'run_python_script.sh',
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
        versions = _sorted_versions(SCHEMA_DIR[schema_name])
        if not versions:
            run(f'{schema_name}: valid JSON', False,
                f'{SCHEMA_DIR[schema_name].relative_to(REPO_ROOT)} has no v*.json files')
            continue
        for path in versions:
            v = path.stem
            try:
                schema = json.loads(path.read_text())
                run(f'{schema_name}: valid JSON + $schema: {v}', '$schema' in schema,
                    'Missing $schema field' if '$schema' not in schema else None)
            except json.JSONDecodeError as e:
                run(f'{schema_name}: valid JSON: {v}', False, str(e))


def check_pipeline_workflow(run, fix, name: str, pipeline: Pipeline) -> None:
    schema  = pipeline.changelog.parent.name
    matrix  = _parse_changelog_matrix(pipeline)
    run_cmd = f'src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {name} --write'

    registered_versions = {version for _, version in matrix}
    changelog_text = pipeline.changelog.read_text() if pipeline.changelog.exists() else ''
    wf = (pipeline.changelog.parent / 'workflow.md').relative_to(REPO_ROOT)
    for path in _sorted_versions(SCHEMA_DIR[schema]):
        v = path.stem
        if v not in registered_versions:
            fix(f'Run: {pipeline.validate_cmd} {pipeline.input.relative_to(REPO_ROOT)}')
            fix(f'then: {run_cmd}')
        run(f'{schema}: workflow.changelog_entry: {v}', v in registered_versions)
        run(f'{schema}: workflow.changelog_narrative: {v}',
            f'## {v}' in changelog_text,
            f'Add a ## {v} section to {pipeline.changelog.relative_to(REPO_ROOT)} '
            f'(see {wf}#changelog-narrative)'
            if f'## {v}' not in changelog_text else None)
        schema_text = path.read_text()
        run(f'{schema}: workflow.no_todo: {v}',
            '"TODO' not in schema_text,
            f'Replace TODO descriptions in {path.relative_to(REPO_ROOT)} '
            f'(see {wf}#no-todo)'
            if '"TODO' in schema_text else None)


def check_pipeline_validation_outputs(run, fix, name: str, pipeline: Pipeline) -> None:
    schema  = pipeline.changelog.parent.name
    matrix  = _parse_changelog_matrix(pipeline)
    run_cmd = f'src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {name} --write'

    if pipeline.subject_depth == 1:
        _check_validation_outputs_depth1(run, fix, pipeline, schema, matrix, run_cmd)
    else:
        _check_validation_outputs_depth2(run, fix, pipeline, schema, matrix, run_cmd)


def _check_validation_outputs_depth1(run, fix, pipeline, schema, matrix, run_cmd):
    gen_dirs    = sorted(d.name for d in pipeline.gen.iterdir() if d.is_dir()) \
                  if pipeline.gen.exists() else []
    gen_rel     = pipeline.gen.relative_to(REPO_ROOT)
    input_rel   = pipeline.input.relative_to(REPO_ROOT)
    chlog_rel   = pipeline.changelog.relative_to(REPO_ROOT)

    print(f'\n  looking for {gen_rel}/<subject>/validation/{schema}/vN.log — one per entry in {chlog_rel}')
    for (subject, version), expected_pass in sorted(matrix.items()):
        log = pipeline.gen / subject / 'validation' / schema / f'{version}.log'
        if not log.exists():
            fix(f'Run: {pipeline.validate_cmd} {pipeline.input.relative_to(REPO_ROOT)}')
            run(f'{schema}: {subject} × {version}', False, str(log.relative_to(REPO_ROOT)))
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{schema}: validation {"passing" if expected_pass else "failing"}: {subject} × {version}'
        run(label, actual_pass == expected_pass,
            f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}'
            if actual_pass != expected_pass else None)

    registered = {subj for subj, _ in matrix}
    print(f'\n  every {schema} log in {gen_rel}/ should be registered in {chlog_rel}')
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

    print(f'\n  every {input_rel}/{pipeline.input_glob} entry should be registered in {chlog_rel}')
    for subject in _input_subjects(pipeline):
        if subject not in registered:
            fix(f'Run: {pipeline.validate_cmd} {pipeline.input.relative_to(REPO_ROOT)}')
            fix(f'then: {run_cmd}')
            run(f'{schema}: unregistered: {subject}', False)


def _check_validation_outputs_depth2(run, fix, pipeline, schema, matrix, run_cmd):
    registered: set[str] = {subject for subject, _ in matrix}

    gen_level1_dirs = sorted(d for d in pipeline.gen.iterdir() if d.is_dir()) \
                      if pipeline.gen.exists() else []
    gen_rel   = pipeline.gen.relative_to(REPO_ROOT)
    input_rel = pipeline.input.relative_to(REPO_ROOT)
    chlog_rel = pipeline.changelog.relative_to(REPO_ROOT)

    print(f'\n  looking for {gen_rel}/<code-project>/<uuid>/validation/{schema}/vN.log — one per entry in {chlog_rel}')
    for (subject, version), expected_pass in sorted(matrix.items()):
        code_project, _, uuid = subject.partition(' / ')
        log = pipeline.gen / code_project / uuid / 'validation' / schema / f'{version}.log'
        if not log.exists():
            fix(f'Run: {pipeline.validate_cmd} {pipeline.input.relative_to(REPO_ROOT)}')
            run(f'{schema}: {subject} × {version}', False, str(log.relative_to(REPO_ROOT)))
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{schema}: validation {"passing" if expected_pass else "failing"}: {subject} × {version}'
        run(label, actual_pass == expected_pass,
            f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}'
            if actual_pass != expected_pass else None)

    print(f'\n  every {schema} log in {gen_rel}/ should be registered in {chlog_rel}')
    for gen_level1 in gen_level1_dirs:
        code_project = gen_level1.name
        for uuid_dir in sorted(u for u in gen_level1.iterdir() if u.is_dir()):
            log_dir = uuid_dir / 'validation' / schema
            if not log_dir.exists():
                continue
            subject = f'{code_project} / {uuid_dir.name}'
            for log in sorted(log_dir.glob('v*.log')):
                version = log.stem
                if (subject, version) in matrix:
                    continue
                content = log.read_text()
                result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
                run(f'{schema}: unregistered: {subject} × {version} — {result}', False)

    print(f'\n  every {input_rel}/{pipeline.input_glob} entry should be registered in {chlog_rel}')
    for code_project, uuid in _input_subjects(pipeline):
        subject = f'{code_project} / {uuid}'
        if subject not in registered:
            fix(f'Run: {pipeline.validate_cmd} {pipeline.input.relative_to(REPO_ROOT)}')
            fix(f'then: {run_cmd}')
            run(f'{schema}: unregistered: {subject}', False)


_VERSIONED_SCHEMA_DIAGNOSTICS_SKIP = frozenset({'naming.root_schema_title_matches_filename'})

def check_versioned_schema_diagnostics(run):
    all_diagnostics = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
    schema_skips    = {s: p.diagnostic_skip for p in PIPELINES.values() for s in p.schemas}

    for schema_name in sorted(schema_skips):
        skip        = _VERSIONED_SCHEMA_DIAGNOSTICS_SKIP | schema_skips[schema_name]
        versions    = _sorted_versions(SCHEMA_DIR[schema_name])
        diagnostics = [s for s in all_diagnostics if s.stem not in skip]
        if not versions:
            run(f'{schema_name}: no versions', False,
                f'{SCHEMA_DIR[schema_name].relative_to(REPO_ROOT)} has no v*.json files')
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
                        {'conv_path':    SCHEMA_DIR['conversations'].parent,
                         'session_path': SCHEMA_DIR['session'],
                         'api_path':     SCHEMA_DIR['apiConversation'].parent,
                         'mcp_path':     RSC_SCHEMA},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


def check_xref(run):
    _, output = _call(SRC / 'test' / 'xref.py')
    summary = output.splitlines()[-1] if output else ''
    m_bad   = re.search(r'(\d+) bad-pointer',  summary)
    m_miss  = re.search(r'(\d+) missing-file', summary)
    m_unref = re.search(r'(\d+) unreferenced', summary)
    bad   = int(m_bad.group(1))   if m_bad   else 0
    miss  = int(m_miss.group(1))  if m_miss  else 0
    unref = int(m_unref.group(1)) if m_unref else 0

    score_file = SRC / 'test' / 'xref_expected_score'
    expected   = score_file.read_text().strip()
    actual     = f'{miss} missing-file, {bad} bad-pointer, {unref} unreferenced'

    run('xref: no bad pointers', bad == 0, summary if bad else None)
    run(f'xref: {actual}', actual == expected,
        f'expected: {expected}  →  consider updating {score_file.relative_to(REPO_ROOT)}'
        if actual != expected else None)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    results = []
    stdout_buffer = io.StringIO()

    def run(label, passed, detail=None):
        results.append((label, passed, detail))
        mark = '✓' if passed else '✗'
        print(f'  {mark} {label}' + (f'\n      {detail}' if not passed and detail else ''))

    fix_hints: list[str] = []
    fix_seen:  set[str]  = set()

    def fix(hint: str) -> None:
        if hint not in fix_seen:
            fix_hints.append(hint)
            fix_seen.add(hint)

    sections: list[str] = []

    def run_section(fn, label=None):
        name = label or fn.__name__
        print(f'\n── {name} {"─" * (74 - len(name))}')
        before = len(results)
        ret = fn(run)
        sections.extend([name] * (len(results) - before))
        return ret

    sys.stdout = stdout_buffer
    try:
        run_section(check_required_files)
        run_section(check_root_schema_diagnostics)

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, p=_pipeline: check_pipeline_validity(run, p),
                        label=f'check_{_slug}_validity')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline, _fix=fix: check_pipeline_workflow(run, _fix, n, p),
                        label=f'check_{_slug}_workflow')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline, _fix=fix: check_pipeline_validation_outputs(run, _fix, n, p),
                        label=f'check_{_slug}_validation_outputs')

        run_section(check_versioned_schema_diagnostics)

        run_section(check_schema_join)
        run_section(check_xref)
    finally:
        sys.stdout = sys.__stdout__

    passes   = sum(1 for _, p, _ in results if p)
    failures = [(n, d) for n, p, d in results if not p]
    total    = len(results)
    score    = f'{passes}/{total}'

    # Score check — appended after all checks so it can use the final passes/total.
    score_file = SRC / 'test' / 'pre_commit_expected_score'
    expected   = score_file.read_text().strip()

    perfection_achieved = passes == total
    expectation_met     = expected == score
    score_ok            = perfection_achieved and expectation_met

    score_detail = (
        f'Fix failures in other sections first'
        if not perfection_achieved else
        f'Consider updating {score_file.relative_to(REPO_ROOT)} to {score}'
        if not expectation_met else None
    )
    score_label = f'score: {score}; expected: {expected}'

    results.append((score_label, score_ok, score_detail))
    sections.append('check_score')
    if not score_ok:
        failures.append((score_label, score_detail))

    failed_sections = list(dict.fromkeys(
        sections[i] for i, (_, p, _) in enumerate(results) if not p
    ))

    # ── HEAD ──────────────────────────────────────────────────────────────────
    if failures:
        if not expectation_met:
            print(f'`src/test/pre_commit.py`: {score} (expected {expected}; failures in {len(failed_sections)} sections)')
        else:
            print(f'`src/test/pre_commit.py`: {score} (failures in {len(failed_sections)} sections)')
    else:
        print(f'pre_commit.py: {score}')

    # ── BODY ──────────────────────────────────────────────────────────────────
    print()
    print(stdout_buffer.getvalue(), end='')

    name = 'check_score'
    print(f'\n── {name} {"─" * (74 - len(name))}')
    print(f'  {"✓" if score_ok else "✗"} {score_label}' +
          (f'\n      {score_detail}' if not score_ok and score_detail else ''))

    # ── TAIL ──────────────────────────────────────────────────────────────────
    if failures:
        failure_counts = {s: sum(1 for i, (_, p, _) in enumerate(results) if not p and sections[i] == s)
                         for s in failed_sections}
        print(f'Failed sections ({len(failed_sections)}):')
        for s in failed_sections:
            print(f'  {s} ({failure_counts[s]})')
        print()

        fix_commands: list[str] = list(fix_hints)
        seen: set[str] = set(fix_hints)

        def _add(cmd: str) -> None:
            if cmd not in seen:
                fix_commands.append(cmd)
                seen.add(cmd)

        for name, detail in failures:
            parts = name.split(': ')
            if len(parts) == 3 and re.match(r'[a-z_]+\.[a-z_]+', parts[1]):
                diag = parts[1]
                _d = SCHEMA_DIR.get(parts[0])
                schema_path = (_d if _d is not None else RSC_SCHEMA / parts[0]) / f'{parts[2]}.json'
                repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                if repair.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                elif diagnostic.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                elif detail:
                    _add(detail)
            elif len(parts) == 2 and re.match(r'[a-z_]+\.[a-z_]+', parts[0]):
                diag, schema_path = parts[0], RSC_SCHEMA / parts[1]
                repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                if repair.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                elif diagnostic.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}')
                elif detail:
                    _add(detail)

        if fix_commands:
            print()
            print('To fix:')
            for cmd in fix_commands:
                if cmd.startswith('then: '):
                    print('then:')
                    print(f'  {cmd[len("then: "):]}')
                else:
                    print(f'  {cmd}')

        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
