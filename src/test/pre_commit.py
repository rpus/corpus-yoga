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
from pathlib import Path
from typing import Any

# ── Repo layout ───────────────────────────────────────────────────────────────
REPO_ROOT                = Path(__file__).resolve().parents[2]
REPO_PARENT              = REPO_ROOT.parent
GEN                      = REPO_ROOT / 'gen'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
BROWSER_CAPTURES         = 'browser-captures'
CHAT_EXPORTS             = 'chat-exports'
CODE_PROJECTS            = 'code-projects'
RSC_SCHEMA               = RSC / 'schema'
APICONVERSATION          = 'apiConversation'
CONVERSATIONS            = 'conversations'
MEMORIES                 = 'memories'
PROJECTS                 = 'projects'
USERS                    = 'users'
SESSION                  = 'session'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

# All versioned schema directories, each with the diagnostics to skip.
# naming.root_schema_title_matches_filename — universal: versioned files are named v*.json, not by title.
# composition.base_schemas_closed — session deviation: TurnBase is intentionally open (see principles.md).
_SKIP_BASE = {'naming.root_schema_title_matches_filename'}
VERSIONED_SCHEMA_DIAGNOSTICS_SKIP = {
    APICONVERSATION: _SKIP_BASE,
    CONVERSATIONS:   _SKIP_BASE,
    MEMORIES:        _SKIP_BASE,
    PROJECTS:        _SKIP_BASE,
    USERS:           _SKIP_BASE,
    SESSION:         _SKIP_BASE | {'composition.base_schemas_closed'},
}

# Prefix for converting bare project names to ~/.claude/projects/ slugs and back.
# slug = _PROJECT_PREFIX + name;  name = slug.removeprefix(_PROJECT_PREFIX)
_PROJECT_PREFIX = str(REPO_PARENT).replace('/', '-') + '-'


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



def _check_csv_pointers(csv_path: Path, columns: tuple, base_for: dict, fails: list) -> None:
    """Validate JSON Pointer fragments in a join CSV. base_for maps column name → base dir."""
    with csv_path.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in columns:
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (base_for.get(col, RSC_SCHEMA / CONVERSATIONS) / file_part).resolve()
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
        RSC_SCHEMA / CONVERSATIONS / 'principles.md',
        RSC_SCHEMA / CONVERSATIONS / 'workflow.md',
        RSC_SCHEMA / SESSION       / 'principles.md',
        RSC_SCHEMA / SESSION       / 'workflow.md',
        *schema_versions,
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / CHAT_EXPORTS    / 'validate.sh',
        SRC  / 'main' / BROWSER_CAPTURES / 'validate.sh',
        SRC  / 'test' / 'gen_model_candidate.py',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'test' / 'gen_model.py',
        SRC  / 'run_python_script.sh',
        RSC  / 'model.json',
        GEN  / 'xref.csv',
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


def check_browser_captures_validity(run):
    versions = _sorted_versions(RSC_SCHEMA / APICONVERSATION)

    if not versions:
        run(f'{APICONVERSATION}: valid JSON', False, f'{(RSC_SCHEMA / APICONVERSATION).relative_to(REPO_ROOT)} has no v*.json files')
        return
    for path in versions:
        v = path.stem
        try:
            schema = json.loads(path.read_text())
            run(f'{APICONVERSATION}: valid JSON + $schema: {v}', '$schema' in schema,
                'Missing $schema field' if '$schema' not in schema else None)
        except json.JSONDecodeError as e:
            run(f'{APICONVERSATION}: valid JSON: {v}', False, str(e))


def check_chat_exports_validity(run):
    schema_dirs = (RSC_SCHEMA / name for name in [CONVERSATIONS, MEMORIES, PROJECTS, USERS])

    for d in schema_dirs:
        versions = _sorted_versions(d)
        if not versions:
            run(f'{d.name}: valid JSON', False, f'{d.relative_to(RSC_SCHEMA)} has no v*.json files')
            continue
        for path in versions:
            v = path.stem
            try:
                schema = json.loads(path.read_text())
                run(f'{d.name}: valid JSON + $schema: {v}', '$schema' in schema,
                    'Missing $schema field' if '$schema' not in schema else None)
            except json.JSONDecodeError as e:
                run(f'{d.name}: valid JSON: {v}', False, str(e))


def check_code_projects_validity(run):
    versions = _sorted_versions(RSC_SCHEMA / SESSION)

    if not versions:
        run(f'{SESSION}: valid JSON', False, f'{(RSC_SCHEMA / SESSION).relative_to(REPO_ROOT)} has no v*.json files')
        return
    for path in versions:
        v = path.stem
        try:
            schema = json.loads(path.read_text())
            run(f'{SESSION}: valid JSON + $schema: {v}', '$schema' in schema,
                'Missing $schema field' if '$schema' not in schema else None)
        except json.JSONDecodeError as e:
            run(f'{SESSION}: valid JSON: {v}', False, str(e))


def check_chat_exports_validation_outputs(run):
    matrix          = _parse_changelog_matrix(RSC_SCHEMA / CONVERSATIONS / 'CHANGELOG.md')
    gen_data_dirs   = sorted(d.name for d in (GEN / CHAT_EXPORTS).iterdir()
                             if d.is_dir() and d.name.startswith('data-')) \
                      if (GEN / CHAT_EXPORTS).exists() else []
    input_data_dirs = sorted(d.name for d in (REPO_PARENT / CHAT_EXPORTS).iterdir()
                             if d.is_dir() and d.name.startswith('data-')) \
                      if (REPO_PARENT / CHAT_EXPORTS).exists() else []

    for (data_dir, version), expected_pass in sorted(matrix.items()):
        log = GEN / CHAT_EXPORTS / data_dir / 'validation' / CONVERSATIONS / f'{version}.log'
        if not log.exists():
            run(f'{CONVERSATIONS}: validation log exists: {data_dir} × {version}', False,
                f'Run: src/main/{CHAT_EXPORTS}/RUNME.sh --{CHAT_EXPORTS} ../{CHAT_EXPORTS}')
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{CONVERSATIONS}: validation {"passing" if expected_pass else "failing"}: {data_dir} × {version}'
        if actual_pass == expected_pass:
            run(label, True)
        else:
            run(label, False,
                f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}')

    # Closed-world complement: flag any (data_dir, version) with a log but no matrix entry.
    for data_dir in gen_data_dirs:
        log_dir = GEN / CHAT_EXPORTS / data_dir / 'validation' / CONVERSATIONS
        if not log_dir.exists():
            continue
        for log in sorted(log_dir.glob('v*.log')):
            version = log.stem
            if (data_dir, version) in matrix:
                continue
            content = log.read_text()
            result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
            run(f'{CONVERSATIONS}: unregistered: {data_dir} × {version} — {result}', False,
                str(log.relative_to(REPO_ROOT)))

    # Input scan: flag data dirs in ../chat-exports/ with no matrix entry at all.
    registered_dirs = {data_dir for data_dir, _ in matrix}
    for data_dir in input_data_dirs:
        if data_dir not in registered_dirs:
            run(f'{CONVERSATIONS}: unregistered: {data_dir}', False,
                f'Run: src/main/{CHAT_EXPORTS}/RUNME.sh --{CHAT_EXPORTS} ../{CHAT_EXPORTS}, then update CHANGELOG.md')


def check_browser_captures_validation_outputs(run):
    matrix      = _parse_changelog_matrix(RSC_SCHEMA / APICONVERSATION / 'CHANGELOG.md')
    gen_batches = sorted(b for b in (GEN / BROWSER_CAPTURES).iterdir() if b.is_dir()) \
                  if (GEN / BROWSER_CAPTURES).exists() else []
    input_convs = [(b.name, u.name)
                   for b in sorted((REPO_PARENT / BROWSER_CAPTURES).glob('data-*/')) if b.is_dir()
                   for u in sorted(b.iterdir()) if u.is_dir()] \
                  if (REPO_PARENT / BROWSER_CAPTURES).exists() else []

    registered: dict[str, list[tuple[str, str]]] = {}  # batch → [(uuid_prefix, subject), ...]
    for (subject, _) in matrix:
        batch, _, prefix = subject.partition(' / ')
        batch, prefix = batch.strip(), prefix.strip()
        registered.setdefault(batch, []).append((prefix, subject))

    for (subject, version), expected_pass in sorted(matrix.items()):
        batch, _, uuid_prefix = subject.partition(' / ')
        batch, uuid_prefix = batch.strip(), uuid_prefix.strip()
        gen_batch = GEN / BROWSER_CAPTURES / batch
        matches = [u for u in (sorted(gen_batch.iterdir()) if gen_batch.exists() else [])
                   if u.is_dir() and u.name.startswith(uuid_prefix)]
        if not matches:
            run(f'{APICONVERSATION}: validation log exists: {batch[:8]}…/{uuid_prefix}… × {version}', False,
                f'Run: src/main/{BROWSER_CAPTURES}/validate.sh --batches ../{BROWSER_CAPTURES}')
            continue
        log = matches[0] / 'validation' / APICONVERSATION / f'{version}.log'
        if not log.exists():
            run(f'{APICONVERSATION}: validation log exists: {batch[:8]}…/{uuid_prefix}… × {version}', False,
                f'Run: src/main/{BROWSER_CAPTURES}/validate.sh --batches ../{BROWSER_CAPTURES}')
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{APICONVERSATION}: validation {"passing" if expected_pass else "failing"}: {batch[:8]}…/{uuid_prefix}… × {version}'
        if actual_pass == expected_pass:
            run(label, True)
        else:
            run(label, False,
                f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}')

    # Closed-world complement: scan gen/ for (batch, uuid, version) with no CHANGELOG entry.
    for gen_batch in gen_batches:
        batch = gen_batch.name
        ps = registered.get(batch, [])
        for uuid_dir in sorted(u for u in gen_batch.iterdir() if u.is_dir()):
            log_dir = uuid_dir / 'validation' / APICONVERSATION
            if not log_dir.exists():
                continue
            match = next(((p, s) for p, s in ps if uuid_dir.name.startswith(p)), (None, None))
            prefix, subject = match
            for log in sorted(log_dir.glob('v*.log')):
                version = log.stem
                if prefix and (subject, version) in matrix:
                    continue
                content = log.read_text()
                result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
                run(f'{APICONVERSATION}: unregistered: {batch[:8]}…/{uuid_dir.name[:8]}… × {version} — {result}', False)

    # Input scan: flag (batch, uuid) pairs in ../browser-captures/ with no CHANGELOG entry.
    for batch, uuid in input_convs:
        ps = registered.get(batch, [])
        if not any(uuid.startswith(p) for p, _ in ps):
            run(f'{APICONVERSATION}: unregistered: {batch[:8]}…/{uuid[:8]}…', False,
                f'Run: src/main/{BROWSER_CAPTURES}/validate.sh --batches ../{BROWSER_CAPTURES}, then update CHANGELOG.md')


def check_code_projects_validation_outputs(run):
    matrix         = _parse_changelog_matrix(RSC_SCHEMA / SESSION / 'CHANGELOG.md')
    project_dirs   = sorted(p for p in (GEN / CODE_PROJECTS).iterdir() if p.is_dir()) \
                     if (GEN / CODE_PROJECTS).exists() else []
    input_sessions = [(f.parent.name.removeprefix(_PROJECT_PREFIX), f.stem)
                      for f in sorted((REPO_PARENT / CODE_PROJECTS).glob('-Users-*/*.jsonl'))] \
                     if (REPO_PARENT / CODE_PROJECTS).exists() else []

    # matrix keys: ('project / uuid_prefix', version)
    registered: dict[str, list[tuple[str, str]]] = {}  # project → [(uuid_prefix, subject), ...]
    for (subject, _) in matrix:
        project, _, prefix = subject.partition(' / ')
        project, prefix = project.strip(), prefix.strip()
        registered.setdefault(project, []).append((prefix, subject))

    for (subject, version), expected_pass in sorted(matrix.items()):
        project, _, uuid_prefix = subject.partition(' / ')
        project, uuid_prefix = project.strip(), uuid_prefix.strip()
        slug = _PROJECT_PREFIX + project
        gen_project = GEN / CODE_PROJECTS / slug
        matches = [s for s in (sorted(gen_project.iterdir()) if gen_project.exists() else [])
                   if s.is_dir() and s.name.startswith(uuid_prefix)]
        if not matches:
            run(f'{SESSION}: validation log exists: {project}/{uuid_prefix}… × {version}', False,
                f'Run: src/main/{CODE_PROJECTS}/RUNME.sh --{CODE_PROJECTS} ../{CODE_PROJECTS}')
            continue
        log = matches[0] / 'validation' / SESSION / f'{version}.log'
        if not log.exists():
            run(f'{SESSION}: validation log exists: {project}/{uuid_prefix}… × {version}', False,
                f'Run: src/main/{CODE_PROJECTS}/RUNME.sh --{CODE_PROJECTS} ../{CODE_PROJECTS}')
            continue
        content     = log.read_text()
        actual_pass = 'Valid!' in content
        label       = f'{SESSION}: validation {"passing" if expected_pass else "failing"}: {project}/{uuid_prefix}… × {version}'
        if actual_pass == expected_pass:
            run(label, True)
        else:
            run(label, False,
                f'expected {"pass" if expected_pass else "fail"}, got {"pass" if actual_pass else "fail"}')

    # Closed-world complement: scan gen/ for (session, version) pairs with no CHANGELOG entry.
    for project_dir in project_dirs:
        project  = project_dir.name.removeprefix(_PROJECT_PREFIX)
        ps = registered.get(project, [])
        for session_dir in sorted(s for s in project_dir.iterdir() if s.is_dir()):
            log_dir = session_dir / 'validation' / SESSION
            if not log_dir.exists():
                continue
            match = next(((p, s) for p, s in ps if session_dir.name.startswith(p)), (None, None))
            prefix, subject = match
            for log in sorted(log_dir.glob('v*.log')):
                version = log.stem
                if prefix and (subject, version) in matrix:
                    continue
                content = log.read_text()
                result  = 'Valid!' if 'Valid!' in content else 'Validation error' if 'Validation error' in content else 'unknown'
                run(f'{SESSION}: unregistered: {project}/{session_dir.name[:8]}… × {version} — {result}', False)

    # Input scan: flag sessions in ../code-projects/ with no CHANGELOG entry.
    for project, session in input_sessions:
        ps = registered.get(project, [])
        if not any(session.startswith(p) for p, _ in ps):
            run(f'{SESSION}: unregistered: {project}/{session[:8]}…', False,
                f'Run: src/main/{CODE_PROJECTS}/RUNME.sh --{CODE_PROJECTS} ../{CODE_PROJECTS}, then update CHANGELOG.md')


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
                         'session_path': RSC_SCHEMA / SESSION,
                         'api_path':     RSC_SCHEMA,
                         'mcp_path':     RSC_SCHEMA},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    results = []
    buf = io.StringIO()

    def run(label, passed, detail=None):
        results.append((label, passed, detail))
        mark = '✓' if passed else '✗'
        print(f'  {mark} {label}' + (f'\n      {detail}' if not passed and detail else ''))

    section_of: list[str] = []

    def run_section(fn):
        print(f'\n── {fn.__name__} {"─" * (74 - len(fn.__name__))}')
        before = len(results)
        ret = fn(run)
        section_of.extend([fn.__name__] * (len(results) - before))
        return ret

    sys.stdout = buf
    try:
        run_section(check_required_files)
        run_section(check_root_schema_diagnostics)

        run_section(check_browser_captures_validity)
        run_section(check_chat_exports_validity)
        run_section(check_code_projects_validity)

        run_section(check_browser_captures_validation_outputs)
        run_section(check_chat_exports_validation_outputs)
        run_section(check_code_projects_validation_outputs)

        run_section(check_versioned_schema_diagnostics)

        run_section(check_schema_join)
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
