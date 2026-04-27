#!/usr/bin/env python
"""
schema_fragment.py - Given a JSON pointer and a schema file, output the
literal subschema at that pointer.

Usage:
    python src/main/conversation-exports/schema_fragment.py "#/definitions/MessageFile" rsc/schema/conversations/v{N}.json

Output:
    Pretty-printed JSON of the subschema.
"""

import json
import sys


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <json-pointer> <schema-file>", file=sys.stderr)
        sys.exit(1)

    pointer, schema_file = sys.argv[1], sys.argv[2]

    with open(schema_file) as f:
        schema = json.load(f)

    # Strip leading # and split on /
    parts = [p for p in pointer.lstrip("#").split("/") if p]
    node = schema
    for part in parts:
        node = node[part]

    print(json.dumps(node, indent=2))


if __name__ == "__main__":
    main()
