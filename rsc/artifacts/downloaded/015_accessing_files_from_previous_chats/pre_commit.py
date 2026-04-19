#!/usr/bin/env python3
"""
pre_commit.py — Pre-commit checks for the Yoga repo.

Usage:
    python src/pre_commit.py

As a git hook, symlink or copy to .git/hooks/pre-commit and make executable:
    cp src/pre_commit.py .git/hooks/pre-commit
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
REPO_ROOT  = Path(__file__).parent.parent
SRC        = REPO_ROOT / 'src'
DIAG_DIR   = SRC / 'diagnostics'
SCHEMA_DIR = REPO_ROOT / 'rsc' / 'schema'
GEN        = REPO_ROOT / 'gen'
VALIDATION = GEN / 'validation'

STEMS = ['conversations', 'memories', 'projects', 'users']

# Diagnostics that run against conversations.json only
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

# Diagnostics that run against all four schemas
ALL_SCHEMA_DIAGNOSTICS = [
    'naming.root_schema_title_matches_filename',
]

# ── Result tracking ───────────────────────────────────────────────────────────
results = []

def run(label, passed, detail=None):
    results.append((label, passed))
    mark = '✓' if passed else '✗'
    print(f'{mark} {label}' + (f'\n    {detail}' if not passed and detail else ''))

def call(script, *args):
    """Run an atomic script, return (passed, output)."""
    result = subprocess.run(
        [sys.executable, str(script)] + list(args),
        capture_output=True, text=True
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output

# ── Section 1: Required files ─────────────────────────────────────────────────
print('\n── Required files ───────────────────────────────────────────────────────')

required = [
    REPO_ROOT / 'conversations.schema.principles.md',
    REPO_ROOT / 'conversations.schema.workflow.md',
    SRC / 'validate.py',
    SRC / 'gen_model_candidate.py',
    REPO_ROOT / 'rsc' / 'schema' / 'model.json',
    *[SCHEMA_DIR / f'{s}.json' for s in STEMS],
    *[DIAG_DIR / f'{d}.py' for d in CONVERSATIONS_DIAGNOSTICS],
    *[DIAG_DIR / f'{d}.py' for d in ALL_SCHEMA_DIAGNOSTICS],
]
for path in required:
    run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists(),
        f'File not found: {path}')

# ── Section 2: Schema titles match filenames (all four schemas) ───────────────
print('\n── Schema titles ────────────────────────────────────────────────────────')

script = DIAG_DIR / 'naming.root_schema_title_matches_filename.py'
for stem in STEMS:
    schema_path = SCHEMA_DIR / f'{stem}.json'
    if not schema_path.exists():
        run(f'naming.root_schema_title_matches_filename: {stem}', False, 'Schema missing')
        continue
    passed, output = call(script, str(schema_path))
    run(f'naming.root_schema_title_matches_filename: {stem}', passed,
        output if not passed else None)

# ── Section 3: Schema validity ────────────────────────────────────────────────
print('\n── Schema validity ──────────────────────────────────────────────────────')

for stem in STEMS:
    path = SCHEMA_DIR / f'{stem}.json'
    if not path.exists():
        run(f'valid JSON: {stem}', False, 'File missing')
        continue
    try:
        schema = json.loads(path.read_text())
        run(f'valid JSON + $schema: {stem}', '$schema' in schema,
            'Missing $schema field' if '$schema' not in schema else None)
    except json.JSONDecodeError as e:
        run(f'valid JSON: {stem}', False, str(e))

# ── Section 4: Validation outputs present and passing ────────────────────────
print('\n── Validation outputs ───────────────────────────────────────────────────')

for stem in STEMS:
    path = VALIDATION / f'{stem}.txt'
    exists = path.exists()
    run(f'validation output exists: {stem}', exists,
        f'Run: python src/validate.py {stem}.json rsc/schema/{stem}.json > gen/validation/{stem}.txt'
        if not exists else None)
    if exists:
        content = path.read_text()
        run(f'validation passing: {stem}', 'Valid!' in content,
            content.strip().split('\n')[-1] if 'Valid!' not in content else None)

# ── Section 5: Conversations schema diagnostics ───────────────────────────────
print('\n── Conversations schema diagnostics ─────────────────────────────────────')

conv_schema = SCHEMA_DIR / 'conversations.json'
if not conv_schema.exists():
    run('conversations schema diagnostics', False, 'Schema file missing — skipping all')
else:
    for diag in CONVERSATIONS_DIAGNOSTICS:
        script = DIAG_DIR / f'{diag}.py'
        if not script.exists():
            run(diag, False, f'Diagnostic script missing: {script}')
            continue
        passed, output = call(script, str(conv_schema))
        detail = None
        if not passed:
            lines = output.splitlines()
            detail = '\n    '.join(lines[1:]) if len(lines) > 1 else lines[0] if lines else None
        run(diag, passed, detail)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passes   = sum(1 for _, p in results if p)
failures = [n for n, p in results if not p]
total    = len(results)

print(f'Results: {passes}/{total} PASS')

if failures:
    print(f'\n{len(failures)} check(s) failed. Commit blocked.')
    print('Run failing diagnostics individually for details:')
    print('  python src/diagnostics/<principle_id>.py rsc/schema/conversations.json')
    print('Run repairs where available:')
    print('  python src/repairs/<principle_id>.py rsc/schema/conversations.json')
    sys.exit(1)
else:
    print('\nAll checks passed. Safe to commit.')
    sys.exit(0)
