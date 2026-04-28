#!/usr/bin/env python
"""
pre_commit.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/pre_commit.sh

As a git hook, install the wrapper:
    cp src/test/pre_commit.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Atomic diagnostic scripts live in src/test/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── Repo layout ───────────────────────────────────────────────────────────────
REPO_ROOT         = Path(__file__).resolve().parents[2]
SRC               = REPO_ROOT / 'src'
RSC               = REPO_ROOT / 'rsc'
GEN_CHAT_EXPORTS = REPO_ROOT / 'gen' / 'chat-exports'
GEN_CODE_PROJECTS = REPO_ROOT / 'gen' / 'code-projects'
DIAG_DIR          = SRC / 'test' / 'diagnostics'
SCHEMA_DIR        = RSC / 'schema'
CONVERSATIONS_DIR          = SCHEMA_DIR / 'conversations'
SESSIONS_DIR      = SCHEMA_DIR / 'sessions'

CONVERSATIONS_VERSIONS = ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']

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

NON_VERSIONED_SCHEMA_DIAGNOSTICS = {
    'naming.root_schema_title_matches_filename',
}

# Schemas (other than the versioned conversations schemas) against which
# NON_VERSIONED_SCHEMA_DIAGNOSTICS are run. Excludes external schemas (mcp.json,
# json-schema_draft-04.json) and special-purpose schemas (documenter.json,
# data-table.json) whose titles are prose rather than matching their stem.
NON_VERSIONED_SCHEMA_TARGETS = [
    SCHEMA_DIR / 'memories' / 'memories.json',
    SCHEMA_DIR / 'projects' / 'projects.json',
    SCHEMA_DIR / 'users'    / 'users.json',
    SCHEMA_DIR / 'model.json',
]

# Diagnostics in DIAG_DIR skipped for the sessions schema.
# composition.base_schemas_closed — justified deviation (TurnBase; see principles.md)
# NON_VERSIONED_SCHEMA_DIAGNOSTICS are also excluded — they apply only to non-versioned schemas.
SESSIONS_DIAGNOSTICS_SKIP = {
    'composition.base_schemas_closed',
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


# ── Checks ────────────────────────────────────────────────────────────────────

def check_required_files(run):
    print('\n── Required files ────────────────────────────────────────────────────────')
    required = [
        CONVERSATIONS_DIR     / 'principles.md',
        CONVERSATIONS_DIR     / 'workflow.md',
        SESSIONS_DIR / 'v1.json',
        SESSIONS_DIR / 'principles.md',
        SESSIONS_DIR / 'workflow.md',
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'chat-exports' / 'validate.sh',
        SRC  / 'test' / 'gen_model_candidate.py',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'test' / 'gen_model.py',
        SRC  / 'run_python_script.sh',
        RSC  / 'model.json',
        *[CONVERSATIONS_DIR / f'{v}.json' for v in CONVERSATIONS_VERSIONS],
        *[SCHEMA_DIR / s / f'{s}.json' for s in ('memories', 'projects', 'users')],
        *[DIAG_DIR / f'{d}.py' for d in NON_VERSIONED_SCHEMA_DIAGNOSTICS],
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists())


def check_conversations_schema_validity(run):
    print('\n── Schema validity ───────────────────────────────────────────────────────')
    for v in CONVERSATIONS_VERSIONS:
        path = CONVERSATIONS_DIR / f'{v}.json'
        if not path.exists():
            run(f'valid JSON: conversations/{v}', False, 'File missing')
            continue
        try:
            schema = json.loads(path.read_text())
            run(f'valid JSON + $schema: conversations/{v}', '$schema' in schema,
                'Missing $schema field' if '$schema' not in schema else None)
        except json.JSONDecodeError as e:
            run(f'valid JSON: conversations/{v}', False, str(e))


def check_chat_validation_outputs(run):
    print('\n── Validation outputs ────────────────────────────────────────────────────')
    for data_dir, version in sorted(CONVERSATIONS_EXPECTED_PASS):
        log = GEN_CHAT_EXPORTS / data_dir / 'validation' / 'conversations' / f'{version}.log'
        if not log.exists():
            run(f'validation log exists: {data_dir} × {version}', False,
                'Run: src/main/chat-exports/validate.sh --chat-exports ../chat-exports')
            continue
        content = log.read_text()
        passed = 'Valid!' in content
        detail = next((l for l in content.splitlines() if l.startswith('Validation error:')), None)
        run(f'validation passing: {data_dir} × {version}', passed, detail)

    # Closed-world complement: a surprise pass signals a regression or missing CONVERSATIONS_EXPECTED_PASS entry.
    for data_dir in sorted(d.name for d in GEN_CHAT_EXPORTS.iterdir() if d.is_dir() and d.name.startswith('data-')) if GEN_CHAT_EXPORTS.exists() else []:
        for version in CONVERSATIONS_VERSIONS:
            if (data_dir, version) in CONVERSATIONS_EXPECTED_PASS:
                continue
            log = GEN_CHAT_EXPORTS / data_dir / 'validation' / 'conversations' / f'{version}.log'
            if not log.exists():
                continue
            if 'Valid!' in log.read_text():
                run(f'unexpected pass (not in CONVERSATIONS_EXPECTED_PASS): {data_dir} × {version}', False,
                    'Add to CONVERSATIONS_EXPECTED_PASS or investigate regression')


def check_conversations_diagnostics(run):
    print('\n── Conversations schema diagnostics ──────────────────────────────────────')
    candidates = list(CONVERSATIONS_DIR.glob('v*.json'))
    if not candidates:
        run('conversations schema diagnostics', False,
            f'{CONVERSATIONS_DIR.relative_to(REPO_ROOT)} has no v*.json files')
        return None
    latest = max(candidates, key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
    for script in sorted(DIAG_DIR.glob('*.py')):
        diag = script.stem
        if diag in NON_VERSIONED_SCHEMA_DIAGNOSTICS:
            continue
        passed, output = _call(script, str(latest))
        run(diag, passed, _diag_detail(output) if not passed else None)
    return latest


def check_sessions_diagnostics(run):
    print('\n── Sessions schema diagnostics ──────────────────────────────────────────')
    sessions_schema = SESSIONS_DIR / 'v1.json'
    if not sessions_schema.exists():
        run('sessions schema diagnostics', False,
            f'{sessions_schema.relative_to(REPO_ROOT)} missing — skipping all')
        return
    for script in sorted(DIAG_DIR.glob('*.py')):
        diag = script.stem
        if diag in NON_VERSIONED_SCHEMA_DIAGNOSTICS or diag in SESSIONS_DIAGNOSTICS_SKIP:
            continue
        passed, output = _call(script, str(sessions_schema))
        run(f'sessions: {diag}', passed, _diag_detail(output) if not passed else None)


def check_sessions_validation_outputs(run):
    print('\n── Sessions validation outputs ──────────────────────────────────────────')
    for project, session, version in sorted(SESSIONS_EXPECTED_PASS):
        log = GEN_CODE_PROJECTS / project / session / 'validation' / 'sessions' / f'{version}.log'
        if not log.exists():
            run(f'sessions validation log exists: {project}/{session[:8]}… × {version}', False,
                'Run: src/main/code-projects/RUNME.sh')
            continue
        content = log.read_text()
        passed = 'Valid!' in content
        detail = next((l for l in content.splitlines() if l.startswith('Validation error:')), None)
        run(f'sessions validation passing: {project}/{session[:8]}… × {version}', passed, detail)


def check_non_versioned_schema_diagnostics(run):
    print('\n── Non-versioned schema diagnostics ─────────────────────────────────────')
    for schema_path in NON_VERSIONED_SCHEMA_TARGETS:
        if not schema_path.exists():
            run(f'exists: {schema_path.relative_to(REPO_ROOT)}', False)
            continue
        for diag in NON_VERSIONED_SCHEMA_DIAGNOSTICS:
            script = DIAG_DIR / f'{diag}.py'
            if not script.exists():
                run(f'{diag}: {schema_path.name}', False,
                    f'Diagnostic script missing: {script.relative_to(REPO_ROOT)}')
                continue
            passed, output = _call(script, str(schema_path))
            run(f'{diag}: {schema_path.relative_to(SCHEMA_DIR)}', passed,
                _diag_detail(output) if not passed else None)


def check_mcp_join_csv(run):
    print('\n── mcp_join.csv pointer validation ──────────────────────────────────────')
    mcp_join = CONVERSATIONS_DIR / 'mcp_join.csv'
    if not mcp_join.exists():
        run('mcp_join.csv exists', False)
        return
    fails: list[str] = []
    with mcp_join.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in ('conv_path', 'mcp_path'):
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (CONVERSATIONS_DIR / file_part).resolve()
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
    run('mcp_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


def check_sessions_join_csv(run):
    print('\n── cli_join.csv pointer validation ──────────────────────────────────────')
    cli_join = SESSIONS_DIR / 'cli_join.csv'
    if not cli_join.exists():
        run('cli_join.csv exists', False)
        return
    fails: list[str] = []
    with cli_join.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in ('cli_path', 'conv_path', 'mcp_path'):
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                # cli_path is relative to SESSIONS_DIR; conv/mcp paths to CONVERSATIONS_DIR
                base = SESSIONS_DIR if col == 'cli_path' else CONVERSATIONS_DIR
                f = (base / file_part).resolve()
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
    run('cli_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    results = []

    def run(label, passed, detail=None):
        results.append((label, passed))
        mark = '✓' if passed else '✗'
        print(f'{mark} {label}' + (f'\n    {detail}' if not passed and detail else ''))

    check_required_files(run)
    check_conversations_schema_validity(run)
    check_chat_validation_outputs(run)
    latest = check_conversations_diagnostics(run)
    check_sessions_diagnostics(run)
    check_sessions_validation_outputs(run)
    check_non_versioned_schema_diagnostics(run)
    check_mcp_join_csv(run)
    check_sessions_join_csv(run)

    print()
    passes   = sum(1 for _, p in results if p)
    failures = [n for n, p in results if not p]
    total    = len(results)
    print(f'Results: {passes}/{total} PASS')

    if failures:
        print(f'\n{len(failures)} check(s) failed. Commit blocked.')
        for name in failures:
            print(f'  ✗ {name}')
        print('\nRun failing diagnostics individually for details:')
        schema_hint = latest.relative_to(REPO_ROOT) if latest else '<schema.json>'
        print(f'  python src/test/diagnostics/<principle_id>.py {schema_hint}')
        print('Run repairs where available:')
        print(f'  python src/test/repairs/<principle_id>.py {schema_hint}')
        sys.exit(1)
    else:
        print('\nAll checks passed. Safe to commit.')
        sys.exit(0)


if __name__ == '__main__':
    main()
