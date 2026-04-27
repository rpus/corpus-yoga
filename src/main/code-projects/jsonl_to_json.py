#!/usr/bin/env python
"""
jsonl_to_json.py — Convert a JSONL file to a JSON array, one line at a time.

Each non-empty line is parsed (for validation) then written as-is into the array.
Memory use is O(1) per line regardless of file size.

Usage:
    python jsonl_to_json.py input.jsonl              # writes to stdout
    python jsonl_to_json.py input.jsonl output.json  # writes to file
    cat input.jsonl | python jsonl_to_json.py        # reads from stdin
"""

import json
import sys


def convert(src, dst):
    dst.write('[')
    sep = '\n'
    for line in src:
        line = line.strip()
        if not line:
            continue
        json.loads(line)  # validate; raises json.JSONDecodeError on malformed input
        dst.write(sep + line)
        sep = ',\n'
    dst.write('\n]\n')


def main():
    args = sys.argv[1:]
    if len(args) == 0:
        convert(sys.stdin, sys.stdout)
    elif len(args) == 1:
        with open(args[0]) as src:
            convert(src, sys.stdout)
    elif len(args) == 2:
        with open(args[0]) as src, open(args[1], 'w') as dst:
            convert(src, dst)
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
