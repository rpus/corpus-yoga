#!/usr/bin/env python
"""
pre_commit.py — Pre-commit checks for the repo.

Usage (direct):
    source ~/venvs/general/bin/activate
    python src/test/pre_commit.py
    deactivate

As a git hook, install the wrapper:
    cp src/test/pre_commit.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Atomic diagnostic scripts live in src/test/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import json
import subprocess
import sys
from pathlib import Path

# ── Repo layout ───────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).parents[2]
SRC        = REPO_ROOT / 'src'
RSC        = REPO_ROOT / 'rsc'
GEN        = REPO_ROOT / 'gen'
DIAG_DIR   = SRC / 'test' / 'diagnostics'
SCHEMA_DIR = RSC / 'schema'
CONV_DIR   = SCHEMA_DIR / 'conversations'

CONV_VERSIONS = ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']

# Expected-passing combinations from CHANGELOG matrix: (data_dir_basename, version)
EXPECTED_PASS = {
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

ALL_SCHEMA_DIAGNOSTICS = [
    'naming.root_schema_title_matches_filename',
]

# Schemas (other than the versioned conversations schemas) against which
# ALL_SCHEMA_DIAGNOSTICS are run. Excludes external schemas (mcp.json,
# json-schema_draft-04.json) and special-purpose schemas (documenter.json,
# data-table.json) whose titles are prose rather than matching their stem.
ALL_SCHEMA_TARGETS = [
    SCHEMA_DIR / 'memories'  / 'memories.json',
    SCHEMA_DIR / 'projects'  / 'projects.json',
    SCHEMA_DIR / 'users'     / 'users.json',
    SCHEMA_DIR / 'model.json',
]

CONVERSATIONS_DIAGNOSTICS = [
    'naming.upper_camel_case',
    'naming.title_matches_key',
    'naming.property_keys_lowercase',
    'structure.field_order',
    'structure.bfs_order',
    'structure.definitions_at_bottom',
    'structure.required_subset_of_properties',
    'structure.no_redundant_additional_properties_true',
    'structure.pattern_constraints_enforced',
    'structure.property_order_matches_data',
    'structure.all_definitions_reachable',
    'structure.no_dangling_refs',
    'structure.minItems_on_non_empty_arrays',
    'documentation.every_definition_has_title_and_description',
    'documentation.descriptions_end_with_full_stop',
    'documentation.null_only_fields_documented',
    'documentation.open_set_enums_documented',
    'documentation.discriminator_fields_annotated',
    'composition.discriminated_union_pattern',
    'composition.discriminator_values_disjoint',
    'composition.base_schemas_closed',
    'composition.wrapper_has_five_fields',
    'composition.no_additional_properties_on_subtypes',
    'composition.base_not_used_directly',
    'empirical.oneOf_branches_evidenced',
    'empirical.nullable_fields_surveyed',
]

# ── Result tracking ────────────────────────────────────────────────────────────
results = []

def run(label, passed, detail=None):
    results.append((label, passed))
    mark = '✓' if passed else '✗'
    print(f'{mark} {label}' + (f'\n    {detail}' if not passed and detail else ''))

def call(script, *args):
    result = subprocess.run(
        [sys.executable, str(script)] + list(args),
        capture_output=True, text=True
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output

# ── Section 1: Required files ──────────────────────────────────────────────────
print('\n── Required files ────────────────────────────────────────────────────────')

required = [
    CONV_DIR  / 'principles.md',
    CONV_DIR  / 'workflow.md',
    SRC  / 'main' / 'validate.py',
    SRC  / 'main' / 'validate.sh',
    SRC  / 'test' / 'gen_model_candidate.py',
    RSC  / 'model.json',
    *[CONV_DIR / f'{v}.json' for v in CONV_VERSIONS],
    *[SCHEMA_DIR / s / f'{s}.json' for s in ('memories', 'projects', 'users')],
    *[DIAG_DIR / f'{d}.py'  for d in ALL_SCHEMA_DIAGNOSTICS],
    *[DIAG_DIR / f'{d}.py'  for d in CONVERSATIONS_DIAGNOSTICS],
]
for path in required:
    run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists())

# ── Section 2: Schema validity ─────────────────────────────────────────────────
print('\n── Schema validity ───────────────────────────────────────────────────────')

for v in CONV_VERSIONS:
    path = CONV_DIR / f'{v}.json'
    if not path.exists():
        run(f'valid JSON: conversations/{v}', False, 'File missing')
        continue
    try:
        schema = json.loads(path.read_text())
        run(f'valid JSON + $schema: conversations/{v}', '$schema' in schema,
            'Missing $schema field' if '$schema' not in schema else None)
    except json.JSONDecodeError as e:
        run(f'valid JSON: conversations/{v}', False, str(e))

# ── Section 3: Validation outputs ─────────────────────────────────────────────
print('\n── Validation outputs ────────────────────────────────────────────────────')

for data_dir, version in sorted(EXPECTED_PASS):
    log = GEN / data_dir / 'validation' / 'conversations' / f'{version}.log'
    if not log.exists():
        run(f'validation log exists: {data_dir} × {version}', False,
            'Run: src/main/validate.sh --data-root ../data-exports')
        continue
    content = log.read_text()
    passed = 'Valid!' in content
    detail = next((l for l in content.splitlines() if l.startswith('Validation error:')), None)
    run(f'validation passing: {data_dir} × {version}', passed, detail)

# Check the closed-world complement: every (export, version) pair that is NOT in
# EXPECTED_PASS must not be passing. A surprise pass signals either a regression
# (the schema was accidentally relaxed) or a missing EXPECTED_PASS entry.
for data_dir in sorted(d.name for d in GEN.iterdir() if d.is_dir() and d.name.startswith('data-')):
    for version in CONV_VERSIONS:
        if (data_dir, version) in EXPECTED_PASS:
            continue
        log = GEN / data_dir / 'validation' / 'conversations' / f'{version}.log'
        if not log.exists():
            continue  # never validated — no claim either way
        if 'Valid!' in log.read_text():
            run(f'unexpected pass (not in EXPECTED_PASS): {data_dir} × {version}', False,
                'Add to EXPECTED_PASS or investigate regression')

# ── Section 4: Conversations schema diagnostics ────────────────────────────────
print('\n── Conversations schema diagnostics ──────────────────────────────────────')

latest = CONV_DIR / 'v6.json'
if not latest.exists():
    run('conversations schema diagnostics', False,
        f'{latest.relative_to(REPO_ROOT)} missing — skipping all')
else:
    for diag in CONVERSATIONS_DIAGNOSTICS:
        script = DIAG_DIR / f'{diag}.py'
        if not script.exists():
            run(diag, False, f'Diagnostic script missing: {script.relative_to(REPO_ROOT)}')
            continue
        passed, output = call(script, str(latest))
        if not passed:
            lines = output.splitlines()
            detail = '\n    '.join(lines[1:]) if len(lines) > 1 else (lines[0] if lines else None)
        else:
            detail = None
        run(diag, passed, detail)

# ── Section 5: All-schema diagnostics ─────────────────────────────────────────
print('\n── All-schema diagnostics ────────────────────────────────────────────────')

for schema_path in ALL_SCHEMA_TARGETS:
    if not schema_path.exists():
        run(f'exists: {schema_path.relative_to(REPO_ROOT)}', False)
        continue
    for diag in ALL_SCHEMA_DIAGNOSTICS:
        script = DIAG_DIR / f'{diag}.py'
        if not script.exists():
            run(f'{diag}: {schema_path.name}', False,
                f'Diagnostic script missing: {script.relative_to(REPO_ROOT)}')
            continue
        passed, output = call(script, str(schema_path))
        if not passed:
            lines = output.splitlines()
            detail = '\n    '.join(lines[1:]) if len(lines) > 1 else (lines[0] if lines else None)
        else:
            detail = None
        run(f'{diag}: {schema_path.relative_to(SCHEMA_DIR)}', passed, detail)

# ── Section 6: mcp_join.csv pointer validation ────────────────────────────────
print('\n── mcp_join.csv pointer validation ──────────────────────────────────────')

import csv as _csv

MCP_JOIN = CONV_DIR / 'mcp_join.csv'
if not MCP_JOIN.exists():
    run('mcp_join.csv exists', False)
else:
    def _walk_pointer(doc: object, pointer: str) -> bool:
        from typing import Any
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

    join_fails: list[str] = []
    with MCP_JOIN.open() as fh:
        for i, row in enumerate(_csv.DictReader(fh), 2):
            for col in ('conv_path', 'mcp_path'):
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (CONV_DIR / file_part).resolve()
                if not f.exists():
                    join_fails.append(f'row {i} {col}: file not found: {file_part}')
                    continue
                if pointer and f.suffix == '.json':
                    try:
                        doc = json.loads(f.read_text())
                    except json.JSONDecodeError:
                        join_fails.append(f'row {i} {col}: invalid JSON: {file_part}')
                        continue
                    if not _walk_pointer(doc, pointer):
                        join_fails.append(f'row {i} {col}: bad pointer: {ref}')

    detail_str = '\n    '.join(join_fails[:5]) if join_fails else None
    run('mcp_join.csv: all pointers valid', not join_fails, detail_str)

# ── Summary ────────────────────────────────────────────────────────────────────
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
    print('  python src/test/diagnostics/<principle_id>.py rsc/schema/conversations/v4.json')
    print('Run repairs where available:')
    print('  python src/test/repairs/<principle_id>.py rsc/schema/conversations/v4.json')
    sys.exit(1)
else:
    print('\nAll checks passed. Safe to commit.')
    sys.exit(0)
