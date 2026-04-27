#!/usr/bin/env python
"""
debug_code_session_record.py — Diagnose why a specific record in a converted session
JSON fails validation against rsc/schema/claude-code-sessions/v1.json.

For each branch of Record.oneOf, reports whether it passes or fails and — for the
branch matching the record's type — drills into the sub-schema to find the leaf-level
cause. Equivalent to running the validation workflow from workflow.md steps 1–3
(validate → categorise → triage) for a single record.

Usage:
    # Diagnose the first failing record in a session:
    python src/test/debug_code_session_record.py gen/code-sessions/claude-export-yoga/{uuid}/session.json

    # Diagnose record at a specific index:
    python src/test/debug_code_session_record.py gen/code-sessions/.../session.json --index 42

    # Diagnose all failing records (summary):
    python src/test/debug_code_session_record.py gen/code-sessions/.../session.json --all
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
SCHEMA_PATH = REPO_ROOT / 'rsc' / 'schema' / 'claude-code-sessions' / 'v1.json'


def load(session_path: Path, schema_path: Path):
    try:
        from jsonschema import Draft4Validator
    except ImportError:
        print('jsonschema not installed. Run: pip install jsonschema', file=sys.stderr)
        sys.exit(1)
    schema = json.loads(schema_path.read_text())
    data = json.loads(session_path.read_text())
    return Draft4Validator(schema), schema, data


def diagnose_record(validator, schema, record, index: int) -> bool:
    """Return True if record is valid, False if it fails (with diagnostics printed)."""
    root_errs = list(validator.iter_errors(record))
    if not root_errs:
        return True

    rtype = record.get('type', '<missing>')
    print(f'\nRecord [{index}] type={rtype!r}  FAILS')
    print(f'  Top-level: {root_errs[0].message[:120]}')

    # Test each branch of Record.oneOf
    record_def = schema['definitions']['Record']
    print()
    for branch_ref in record_def['oneOf']:
        name = branch_ref['$ref'].split('/')[-1]
        branch_def = schema['definitions'][name]
        errs = list(validator.descend(record, branch_def))
        if not errs:
            print(f'  {name}: PASS')
        else:
            # Show only the most specific error for non-matching branches
            best = min(errs, key=lambda e: (len(e.absolute_path) == 0, -len(e.absolute_path)))
            print(f'  {name}: FAIL  ({best.message[:80]})')

    # Drill into the matching branch
    type_to_def = {
        'user': 'UserTurnType', 'assistant': 'AssistantTurnType',
        'attachment': 'AttachmentRecordType', 'system': 'SystemRecordType',
        'queue-operation': 'QueueOperation', 'permission-mode': 'PermissionModeRecord',
        'last-prompt': 'LastPromptRecord', 'file-history-snapshot': 'FileHistorySnapshot',
        'ai-title': 'AiTitleRecord',
    }
    inner = type_to_def.get(rtype)
    if inner and inner in schema['definitions']:
        print(f'\n  Drilling into {inner}:')
        inner_errs = list(validator.descend(record, schema['definitions'][inner]))
        if inner_errs:
            for e in sorted(inner_errs, key=lambda e: -len(e.absolute_path))[:5]:
                print(f'    path={list(e.absolute_path)}  {e.message[:100]}')
        else:
            print(f'    (no errors in {inner} directly — failure is at wrapper level)')

    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('session_json', type=Path,
                        help='Converted session JSON (from RUNME-code-sessions.sh)')
    parser.add_argument('--schema', type=Path, default=SCHEMA_PATH,
                        help=f'Schema path (default: {SCHEMA_PATH.relative_to(REPO_ROOT)})')
    parser.add_argument('--index', type=int, default=None,
                        help='Diagnose record at this index (default: first failing)')
    parser.add_argument('--all', action='store_true',
                        help='Diagnose all failing records (prints summary)')
    args = parser.parse_args()

    if not args.session_json.exists():
        print(f'Not found: {args.session_json}', file=sys.stderr)
        sys.exit(1)

    validator, schema, data = load(args.session_json, args.schema)
    print(f'Session: {args.session_json}  ({len(data)} records)')
    print(f'Schema:  {args.schema.relative_to(REPO_ROOT)}')

    if args.index is not None:
        diagnose_record(validator, schema, data[args.index], args.index)
        return

    failures = [(i, r) for i, r in enumerate(data)
                if list(validator.iter_errors(r))]

    if not failures:
        print('\nAll records valid.')
        return

    print(f'\n{len(failures)} failing records.')

    if args.all:
        for i, record in failures:
            diagnose_record(validator, schema, record, i)
    else:
        i, record = failures[0]
        print(f'Showing first failure (use --all for all, --index N for a specific one).')
        diagnose_record(validator, schema, record, i)


if __name__ == '__main__':
    main()
