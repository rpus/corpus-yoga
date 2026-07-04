#!/usr/bin/env python
"""
Validate one JSON file against every versioned schema (v*.json) in a schema directory.
Writes per-version log files and prints a status summary.
"""

import glob
import os
import sys
from datetime import datetime
from pathlib import Path

from validate import validate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ — shared modules live at its root
from validation_matrix import write_matrix  # noqa: E402


def _log_current(log_out, input_file, schema_path, input_bytes, schema_bytes):
    """True iff the existing log demonstrably describes the current datum × schema:
    it postdates both files and its recorded byte sizes match. Lets an unchanged
    datum × schema pair skip revalidation — the log IS the memoisation."""
    try:
        log_mtime = os.path.getmtime(log_out)
        if log_mtime <= os.path.getmtime(input_file) or log_mtime <= os.path.getmtime(schema_path):
            return False
        with open(log_out) as fh:
            next(fh)
            input_line = next(fh)
            schema_line = next(fh)
    except (OSError, StopIteration):
        return False
    return input_line.rstrip().endswith(f', {input_bytes} bytes') and \
        schema_line.rstrip().endswith(f': {schema_bytes} bytes')


def validate_versions(input_file, schema_dir, log_dir, label):
    os.makedirs(log_dir, exist_ok=True)
    schemas = sorted(glob.glob(os.path.join(schema_dir, 'v*.json')))
    if not schemas:
        print(f'  {label}: no versioned schemas found in {schema_dir}', file=sys.stderr)
        return
    skipped = 0
    for schema_path in schemas:
        version = os.path.splitext(os.path.basename(schema_path))[0]
        log_out = os.path.join(log_dir, f'{version}.log')

        input_bytes = os.path.getsize(input_file)
        schema_bytes = os.path.getsize(schema_path)

        if _log_current(log_out, input_file, schema_path, input_bytes, schema_bytes):
            skipped += 1
            continue

        with open(input_file) as fh:
            input_lines = fh.read().count('\n')

        result = validate(input_file, schema_path)
        status = result[0]

        with open(log_out, 'w') as f:
            f.write(datetime.now().astimezone().replace(microsecond=0).isoformat() + '\n')
            f.write(f'{input_file}: {input_lines} lines, {input_bytes} bytes\n')
            f.write(f'{schema_path}: {schema_bytes} bytes\n')
            for line in result:
                f.write(line + '\n')

        if len(status) > 80:
            print(f'  {label} ({version}): {status[:80]}…')
            print(f'    → {log_out}')
        else:
            print(f'  {label} ({version}): {status}')

    if skipped:
        print(f'  {label}: {skipped}/{len(schemas)} version(s) current — skipped')

    # Validation owns the datum's machine-local matrix: re-render matrix.md from the
    # logs just written, so it can never lag them. The datum dir is the parent of the
    # 'validation' component of log_dir (which may nest further, e.g. projects/<uuid>).
    p = Path(log_dir).resolve()
    while p.name != 'validation' and p != p.parent:
        p = p.parent
    if p.name == 'validation':
        mfile = write_matrix(p.parent, Path(schema_dir).resolve().parent)
        if mfile:
            print(f'  matrix: {mfile}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(f'Usage: {sys.argv[0]} <input_file> <schema_dir> <log_dir> <label>')
        sys.exit(1)
    validate_versions(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
