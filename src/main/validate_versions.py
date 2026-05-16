#!/usr/bin/env python
"""
Validate one JSON file against every versioned schema (v*.json) in a schema directory.
Writes per-version log files and prints a status summary.
"""

import glob
import os
import sys
from datetime import datetime

from validate import validate


def validate_versions(input_file, schema_dir, log_dir, label):
    os.makedirs(log_dir, exist_ok=True)
    for schema_path in sorted(glob.glob(os.path.join(schema_dir, 'v*.json'))):
        version = os.path.splitext(os.path.basename(schema_path))[0]
        log_out = os.path.join(log_dir, f'{version}.log')

        input_lines = open(input_file).read().count('\n')
        input_bytes = os.path.getsize(input_file)
        schema_bytes = os.path.getsize(schema_path)

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


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(f'Usage: {sys.argv[0]} <input_file> <schema_dir> <log_dir> <label>')
        sys.exit(1)
    validate_versions(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
