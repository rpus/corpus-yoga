#!/usr/bin/env python3
"""
pre_commit.py — Pre-commit checks for the Yoga repo.

Usage:
    python src/pre_commit.py

As a git hook, symlink or copy to .git/hooks/pre-commit and make executable:
    cp src/pre_commit.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.
Each check prints PASS or FAIL with a brief explanation.

Atomic diagnostic scripts live in src/diagnostics/.
Atomic repair scripts live in src/repairs/.
Each diagnostic takes a schema path as its sole argument and exits 0/1.
"""

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
CONV_SCHEMA = SCHEMA_DIR / 'conversations.json'

# ── Result tracking ───────────────────────────────────────────────────────────
results = []

def check(name, passed, detail=None):
    results.append((name, 'PASS' if passed else 'FAIL'))
    mark = '✓' if passed else '✗'
    print(f'{mark} {name}' + (f'\n    {detail}' if not passed and detail else ''))
    return passed

def run_diagnostic(script_name, schema_path):
    """Run a diagnostic script and return (passed, output)."""
    script = DIAG_DIR / f'{script_name}.py'
    if not script.exists():
        return False, f'Diagnostic script not found: {script}'
    result = subprocess.run(
        [sys.executable, str(script), str(schema_path)],
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
    SCHEMA_DIR / 'model.json',
    *[SCHEMA_DIR / f'{s}.json' for s in STEMS],
    *[DIAG_DIR / f'{d}.py' for d in [
        'naming.upper_camel_case',
        'naming.title_matches_key',
        'naming.root_schema_title_matches_filename',
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
    ]],
]

for path in required:
    check(f'exists: {path.relative_to(REPO_ROOT)}', path.exists(),
          f'File not found: {path}')

# ── Section 2: Schema title matches filename (all four schemas) ───────────────
print('\n── Schema titles ────────────────────────────────────────────────────────')

for stem in STEMS:
    path = SCHEMA_DIR / f'{stem}.json'
    if path.exists():
        passed, output = run_diagnostic('naming.root_schema_title_matches_filename', path)
        check(f'naming.root_schema_title_matches_filename: {stem}', passed,
              output if not passed else None)

# ── Section 3: Schemas are valid JSON with $schema ────────────────────────────
print('\n── Schema validity ──────────────────────────────────────────────────────')

import json
for stem in STEMS:
    path = SCHEMA_DIR / f'{stem}.json'
    if not path.exists():
        check(f'valid JSON: {stem}', False, 'File missing'); continue
    try:
        schema = json.loads(path.read_text())
        check(f'valid JSON + $schema: {stem}', '$schema' in schema,
              'Missing $schema field' if '$schema' not in schema else None)
    except json.JSONDecodeError as e:
        check(f'valid JSON: {stem}', False, str(e))

# ── Section 4: Validation outputs present and passing ────────────────────────
print('\n── Validation outputs ───────────────────────────────────────────────────')

for stem in STEMS:
    path = VALIDATION / f'{stem}.txt'
    if not check(f'validation output exists: {stem}', path.exists(),
                 f'Run: for f in *.json; do python src/validate.py "$f" '
                 f'"rsc/schema/${{f%.json}}.json" > "gen/validation/${{f%.json}}.txt"; done'):
        continue
    content = path.read_text()
    check(f'validation passes: {stem}', 'Valid!' in content,
          content.strip().split('\n')[-1] if 'Valid!' not in content else None)

# ── Section 5: Conversations schema — all enforced diagnostics ────────────────
print('\n── Conversations schema diagnostics ─────────────────────────────────────')

DIAGNOSTICS = [
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

if CONV_SCHEMA.exists():
    for diag in DIAGNOSTICS:
        passed, output = run_diagnostic(diag, CONV_SCHEMA)
        detail = None
        if not passed:
            # Extract first failure line from output
            lines = [l for l in output.splitlines() if l.startswith('  ')]
            detail = lines[0] if lines else output
        check(diag, passed, detail)
else:
    check('conversations schema diagnostics', False, 'Schema file missing')

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passes   = sum(1 for _, s in results if s == 'PASS')
total    = len(results)
failures = [(n, ) for n, s in results if s == 'FAIL']

print(f'Results: {passes}/{total} PASS')

if failures:
    print(f'\n{len(failures)} check(s) failed. Commit blocked.')
    sys.exit(1)
else:
    print('\nAll checks passed. Safe to commit.')
    sys.exit(0)