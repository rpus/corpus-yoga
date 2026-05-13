#!/usr/bin/env python
"""
jsonl_to_json.py — Convert a JSONL file to a JSON array, one line at a time.

Each non-empty line is parsed (for validation) then written as-is into the array.
Memory use is O(1) per line regardless of file size.

When writing to a file, also writes a companion <output>.title containing the last
ai-title value found in the session (empty if none). Callers can use this to create
a human-readable symlink alongside the output file.

Usage:
    python jsonl_to_json.py input.jsonl              # writes to stdout
    python jsonl_to_json.py input.jsonl output.json  # writes to file + .title
    cat input.jsonl | python jsonl_to_json.py        # reads from stdin
"""

import json
import sys
from pathlib import Path


def convert(src, dst):
    """Convert JSONL src to JSON array dst. Returns last ai-title seen, or ''."""
    dst.write('[')
    sep = '\n'
    current_title = ''
    for line in src:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)  # validate; raises json.JSONDecodeError on malformed input
        if record.get('type') == 'ai-title':
            current_title = record.get('aiTitle', '')
        dst.write(sep + line)
        sep = ',\n'
    dst.write('\n]\n')
    return current_title


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        convert(sys.stdin, sys.stdout)
    elif len(args) == 1:
        with open(args[0]) as src:
            convert(src, sys.stdout)
    elif len(args) == 2:
        with open(args[0]) as src, open(args[1], 'w') as dst:
            title = convert(src, dst)
        Path(args[1] + '.title').write_text(title)
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
