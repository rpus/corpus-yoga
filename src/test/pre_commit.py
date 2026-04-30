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
GEN                      = REPO_ROOT / 'gen'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
GEN_CHAT_EXPORTS         = GEN / 'chat-exports'
GEN_CODE_PROJECTS        = GEN / 'code-projects'
RSC_SCHEMA               = RSC / 'schema'
RSC_SCHEMA_CONVERSATIONS = RSC_SCHEMA / 'conversations'
RSC_SCHEMA_SESSIONS      = RSC_SCHEMA / 'sessions'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

# Slug for this repo: absolute path with / replaced by - (matches ~/.claude/projects/ naming).
REPO_SLUG = str(REPO_ROOT).replace('/', '-')
# Slug for the sibling Yoga project, derived from the same HOME to avoid hardcoding a username.
YOGA_SLUG = str(REPO_ROOT.parent / 'Yoga').replace('/', '-')

# Expected-passing combinations from CHANGELOG matrix: (data_dir_basename, version)
CONVERSATIONS_EXPECTED_PASS = {
    ('data-2026-03-19-22-47-05-batch-0000',                                      'v1'),
    ('data-2026-03-30-14-51-46-batch-0000',                                      'v1'),
    ('data-2026-03-30-14-51-46-batch-0000',                                      'v2'),
    ('data-2026-04-03-14-15-13-batch-0000',                                      'v1'),
    ('data-2026-04-03-14-15-13-batch-0000',                                      'v2'),
    ('data-2026-04-05-10-33-48-batch-0000',                                      'v1'),
    ('data-2026-04-05-10-33-48-batch-0000',                                      'v2'),
    ('data-2026-04-07-07-52-05-batch-0000',                                      'v1'),
    ('data-2026-04-07-07-52-05-batch-0000',                                      'v2'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000', 'v3'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000', 'v4'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000', 'v5'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000', 'v6'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000', 'v4'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000', 'v5'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000', 'v6'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000', 'v4'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000', 'v5'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000', 'v6'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000', 'v5'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000', 'v6'),
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1777127504-a3d8c71b-batch-0000', 'v6'),
}

# Diagnostics skipped for the conversations schema (versioned; stem != title by design).
CONVERSATIONS_DIAGNOSTICS_SKIP = {
    'naming.root_schema_title_matches_filename',
}

# Diagnostics skipped for the sessions schema.
# composition.base_schemas_closed — justified deviation (TurnBase; see principles.md)
SESSIONS_DIAGNOSTICS_SKIP = {
    'composition.base_schemas_closed',
    'naming.root_schema_title_matches_filename',
}

# Expected-passing (project, session, schema-version) triples for the sessions schema.
# Parallel to CONVERSATIONS_EXPECTED_PASS for conversations.
# Project name is the ~/.claude/projects/ slug: absolute path with / replaced by -.
# Derived from REPO_SLUG so no username is hardcoded here.
SESSIONS_EXPECTED_PASS = {
    (YOGA_SLUG, '816816d2-799b-441a-9aeb-5b7222418f1d', 'v1'),
    (REPO_SLUG, '60c07575-359d-4484-aaa1-6068f03d5297', 'v1'),
    (REPO_SLUG, 'a40a0813-8a53-4503-a2ca-0b52b95e6406', 'v1'),
    (REPO_SLUG, '7d59d8ef-0ccb-4ffa-8bd5-12c157ec9492', 'v1'),
    (REPO_SLUG, 'd58db402-6597-4f96-a2c7-ba3da7ac5bf5', 'v1'),
    (REPO_SLUG, '1bc20fc3-edf2-46fd-89db-b5481f112ef0', 'v1'),
    (REPO_SLUG, 'a2605476-5569-4640-8386-cf7f466578ae', 'v1'),
    (REPO_SLUG, '73f51bc1-229b-413f-9907-8376b4e6e9c2', 'v1'),
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


def _sorted_versions(schema_dir: Path) -> list[Path]:
    """Return all v*.json in schema_dir sorted by version number ascending."""
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )


def _latest_version(schema_dir: Path) -> Path | None:
    """Return the highest v*.json in schema_dir, or None if none exist."""
    vs = _sorted_versions(schema_dir)
    return vs[-1] if vs else None


def _check_csv_pointers(csv_path: Path, columns: tuple, base_for: dict, fails: list) -> None:
    """Validate JSON Pointer fragments in a join CSV. base_for maps column name → base dir."""
    with csv_path.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in columns:
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (base_for.get(col, RSC_SCHEMA_CONVERSATIONS) / file_part).resolve()
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
        RSC_SCHEMA_CONVERSATIONS / 'principles.md',
        RSC_SCHEMA_CONVERSATIONS / 'workflow.md',
        RSC_SCHEMA_SESSIONS      / 'principles.md',
        RSC_SCHEMA_SESSIONS      / 'workflow.md',
        *schema_versions,
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'chat-exports' / 'validate.sh',
        SRC  / 'test' / 'gen_model_candidate.py',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'test' / 'gen_model.py',
        SRC  / 'run_python_script.sh',
        RSC  / 'model.json',
        GEN  / 'xref.csv',
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists())


def check_chat_exports_validity(run):
    schema_dirs  = (d for d in sorted(RSC_SCHEMA.iterdir())
                    if d.is_dir() and not d.name.startswith('_') and d != RSC_SCHEMA_SESSIONS)
    root_schemas = sorted(RSC_SCHEMA.glob('*.json'))
    diagnostics  = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))

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

    for schema_path in root_schemas:
        for script in diagnostics:
            diag = script.stem
            passed, output = _call(script, str(schema_path))
            run(f'{diag}: {schema_path.relative_to(RSC_SCHEMA)}', passed,
                _diag_detail(output) if not passed else None)


def check_code_projects_validity(run):
    versions = _sorted_versions(RSC_SCHEMA_SESSIONS)

    if not versions:
        run('sessions: valid JSON', False, f'{RSC_SCHEMA_SESSIONS.relative_to(REPO_ROOT)} has no v*.json files')
        return
    for path in versions:
        v = path.stem
        try:
            schema = json.loads(path.read_text())
            run(f'sessions: valid JSON + $schema: {v}', '$schema' in schema,
                'Missing $schema field' if '$schema' not in schema else None)
        except json.JSONDecodeError as e:
            run(f'sessions: valid JSON: {v}', False, str(e))


def check_chat_exports_validation_outputs(run):
    expected        = sorted(CONVERSATIONS_EXPECTED_PASS)
    gen_data_dirs   = sorted(d.name for d in GEN_CHAT_EXPORTS.iterdir()
                             if d.is_dir() and d.name.startswith('data-')) \
                      if GEN_CHAT_EXPORTS.exists() else []
    conv_versions   = [v.stem for v in _sorted_versions(RSC_SCHEMA_CONVERSATIONS)]

    for data_dir, version in expected:
        log = GEN_CHAT_EXPORTS / data_dir / 'validation' / 'conversations' / f'{version}.log'
        if not log.exists():
            run(f'chat: validation log exists: {data_dir} × {version}', False,
                'Run: src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports')
            continue
        content = log.read_text()
        passed = 'Valid!' in content
        detail = next((line for line in content.splitlines() if line.startswith('Validation error:')), None)
        run(f'chat: validation passing: {data_dir} × {version}', passed, detail)

    # Closed-world complement: a surprise pass signals a regression or missing CONVERSATIONS_EXPECTED_PASS entry.
    # Only passes are flagged here (not failures) because chat exports are added manually and
    # intentionally — an unexpected failure is impossible by construction.
    for data_dir in gen_data_dirs:
        for version in conv_versions:
            if (data_dir, version) in CONVERSATIONS_EXPECTED_PASS:
                continue
            log = GEN_CHAT_EXPORTS / data_dir / 'validation' / 'conversations' / f'{version}.log'
            if not log.exists():
                continue
            if 'Valid!' in log.read_text():
                run(f'chat: unexpected pass (not in CONVERSATIONS_EXPECTED_PASS): {data_dir} × {version}', False,
                    'Add to CONVERSATIONS_EXPECTED_PASS or investigate regression')


def check_code_projects_validation_outputs(run):
    expected     = sorted(SESSIONS_EXPECTED_PASS)
    project_dirs = sorted(p for p in GEN_CODE_PROJECTS.iterdir() if p.is_dir()) \
                   if GEN_CODE_PROJECTS.exists() else []

    for project, session, version in expected:
        log = GEN_CODE_PROJECTS / project / session / 'validation' / 'sessions' / f'{version}.log'
        if not log.exists():
            run(f'sessions: validation log exists: {project}/{session[:8]}… × {version}', False,
                'Run: src/main/code-projects/RUNME.sh --code-projects ../code-projects')
            continue
        content = log.read_text()
        passed = 'Valid!' in content
        detail = next((line for line in content.splitlines() if line.startswith('Validation error:')), None)
        run(f'sessions: validation passing: {project}/{session[:8]}… × {version}', passed, detail)

    # Closed-world complement: scan gen/code-projects/ for logs not in SESSIONS_EXPECTED_PASS.
    # Unregistered failures must be investigated; unregistered passes must be added.
    for project_dir in project_dirs:
        session_dirs = sorted(s for s in project_dir.iterdir() if s.is_dir())
        for session_dir in session_dirs:
            log = session_dir / 'validation' / 'sessions' / 'v1.log'
            if not log.exists():
                continue
            key = (project_dir.name, session_dir.name, 'v1')
            if key in SESSIONS_EXPECTED_PASS:
                continue
            content = log.read_text()
            label = f'sessions: unregistered: {project_dir.name}/{session_dir.name[:8]}…'
            if 'Validation error' in content:
                run(label, False, 'Session fails validation and is absent from SESSIONS_EXPECTED_PASS — investigate')
            elif 'Valid!' in content:
                run(label, False, 'Session passes but is absent from SESSIONS_EXPECTED_PASS — add it')


def check_chat_exports_diagnostics(run):
    latest      = _latest_version(RSC_SCHEMA_CONVERSATIONS)
    diagnostics = [s for s in sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
                   if s.stem not in CONVERSATIONS_DIAGNOSTICS_SKIP]

    if latest is None:
        run('chat: conversations schema diagnostics', False,
            f'{RSC_SCHEMA_CONVERSATIONS.relative_to(REPO_ROOT)} has no v*.json files')
        return None
    for script in diagnostics:
        passed, output = _call(script, str(latest))
        run(f'chat: {script.stem}', passed, _diag_detail(output) if not passed else None)
    return latest


def check_code_projects_diagnostics(run):
    latest      = _latest_version(RSC_SCHEMA_SESSIONS)
    diagnostics = [s for s in sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
                   if s.stem not in SESSIONS_DIAGNOSTICS_SKIP]

    if latest is None:
        run('sessions: schema diagnostics', False,
            f'{RSC_SCHEMA_SESSIONS.relative_to(REPO_ROOT)} has no v*.json files')
        return None
    for script in diagnostics:
        passed, output = _call(script, str(latest))
        run(f'sessions: {script.stem}', passed, _diag_detail(output) if not passed else None)
    return latest


def check_chat_exports_join_csv(run):
    mcp_join = RSC_SCHEMA_CONVERSATIONS / 'mcp_join.csv'
    if not mcp_join.exists():
        run('chat: mcp_join.csv exists', False)
        return
    fails: list[str] = []
    _check_csv_pointers(mcp_join, ('conv_path', 'mcp_path'),
                        {'conv_path': RSC_SCHEMA_CONVERSATIONS, 'mcp_path': RSC_SCHEMA_CONVERSATIONS}, fails)
    run('chat: mcp_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


def check_code_projects_join_csv(run):
    cli_join = RSC_SCHEMA_SESSIONS / 'cli_join.csv'
    if not cli_join.exists():
        run('sessions: cli_join.csv exists', False)
        return
    fails: list[str] = []
    _check_csv_pointers(cli_join, ('cli_path', 'conv_path', 'mcp_path'),
                        {'cli_path': RSC_SCHEMA_SESSIONS, 'conv_path': RSC_SCHEMA_CONVERSATIONS, 'mcp_path': RSC_SCHEMA_CONVERSATIONS},
                        fails)
    run('sessions: cli_join.csv: all pointers valid', not fails,
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

        run_section(check_chat_exports_validity)
        run_section(check_code_projects_validity)

        run_section(check_chat_exports_validation_outputs)
        run_section(check_code_projects_validation_outputs)

        latest_chat_exports  = run_section(check_chat_exports_diagnostics)
        latest_code_projects = run_section(check_code_projects_diagnostics)

        run_section(check_chat_exports_join_csv)
        run_section(check_code_projects_join_csv)
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
        print(f'Failed sections ({len(failed_sections)}):')
        for s in failed_sections:
            print(f'  {s}')
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
            elif name.startswith('chat: ') and latest_chat_exports:
                diag = name[len('chat: '):]
                if re.match(r'[a-z_]+\.[a-z_]+', diag):
                    _add(f'python src/test/diagnostics/{diag}.py {latest_chat_exports.relative_to(REPO_ROOT)}')
            elif name.startswith('sessions: ') and latest_code_projects:
                diag = name[len('sessions: '):]
                if re.match(r'[a-z_]+\.[a-z_]+', diag):
                    _add(f'python src/test/diagnostics/{diag}.py {latest_code_projects.relative_to(REPO_ROOT)}')
            elif ': ' in name:
                diag, _, filename = name.partition(': ')
                if re.match(r'[a-z_]+\.[a-z_]+', diag):
                    path = RSC_SCHEMA / filename
                    if path.exists():
                        _add(f'python src/test/diagnostics/{diag}.py {path.relative_to(REPO_ROOT)}')

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
