#!/usr/bin/env python3
"""
pre_commit.py — Pre-commit checks for the Yoga repo.

Usage:
    source ~/venvs/general/bin/activate
        python src/main/pre_commit.py
    deactivate

As a git hook:
    cp src/main/pre_commit.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Atomic diagnostic scripts live in src/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/repairs/{principle_id}.py.
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
DOC        = REPO_ROOT / 'doc'
DIAG_DIR   = SRC / 'diagnostics'
SCHEMA_DIR = RSC / 'schema'
CONV_DIR   = SCHEMA_DIR / 'conversations'

CONV_VERSIONS = ['v1', 'v2', 'v3', 'v4']

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
    ('data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000', 'v4'),
}

ALL_SCHEMA_DIAGNOSTICS = [
    'naming.root_schema_title_matches_filename',
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
    DOC  / 'conversations.schema.principles.md',
    DOC  / 'conversations.schema.workflow.md',
    SRC  / 'main' / 'validate.py',
    SRC  / 'main' / 'validate.sh',
    SRC  / 'main' / 'gen_model_candidate.py',
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
            'Run: src/main/validate.sh --data-root ../exported-data')
        continue
    content = log.read_text()
    passed = 'Valid!' in content
    detail = next((l for l in content.splitlines() if l.startswith('Validation error:')), None)
    run(f'validation passing: {data_dir} × {version}', passed, detail)

# ── Section 4: Conversations schema diagnostics ────────────────────────────────
print('\n── Conversations schema diagnostics ──────────────────────────────────────')

latest = CONV_DIR / 'v4.json'
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
    print('  python src/diagnostics/<principle_id>.py rsc/schema/conversations/v4.json')
    print('Run repairs where available:')
    print('  python src/repairs/<principle_id>.py rsc/schema/conversations/v4.json')
    sys.exit(1)
else:
    print('\nAll checks passed. Safe to commit.')
    sys.exit(0)
