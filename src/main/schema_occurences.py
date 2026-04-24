#!/usr/bin/env python
"""
schema_occurrences.py - Given a schema file, a subschema pointer, and an instance
document, output the path to every location in the instance where that subschema
applies (i.e. every place the schema references it via $ref).

Usage:
    python src/main/schema_occurences.py "#/definitions/MessageFile" \\
        rsc/schema/conversations/v{N}.json conversations.json > paths.jsonl

Output:
    One jq-style path array per line (JSONL), e.g.
        [0,"chat_messages",0,"files",0]
        [0,"chat_messages",0,"files",1]
        [1,"chat_messages",3,"files",0]

To fetch all occurrences as a location-keyed object:
    jq -n --slurpfile inst conversations.json \\
        '[inputs as $p | {key: ($p|tostring), value: ($inst[0]|getpath($p))}] | from_entries' \\
        paths.jsonl
"""

import json
import sys


def find_ref_schema_paths(node, target_ref, current=()):
    """
    Walk the schema tree (without following $refs) and yield every schema path
    at which a $ref to target_ref appears.
    """
    if isinstance(node, dict):
        if node.get("$ref") == target_ref:
            yield current
        else:
            for key, child in node.items():
                yield from find_ref_schema_paths(child, target_ref, current + (key,))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from find_ref_schema_paths(child, target_ref, current + (i,))


def schema_path_to_instance_pattern(schema_path):
    """
    Convert a schema path (tuple of keys) to an instance pattern: a list of
    ('key', name) or ('array',) steps, representing how to walk an instance.

    Schema keywords consumed:
      properties/<name>  →  ('key', name)
      items              →  ('array',)
      allOf/N, anyOf/N, oneOf/N  →  transparent (skipped)
    """
    pattern = []
    i = 0
    while i < len(schema_path):
        step = schema_path[i]
        if step == "properties":
            i += 1
            if i < len(schema_path):
                pattern.append(("key", schema_path[i]))
        elif step == "items":
            pattern.append(("array",))
        elif step in ("allOf", "anyOf", "oneOf"):
            i += 1  # skip the combiner index — transparent to instance structure
        i += 1
    return pattern


def find_instance_patterns(schema, target_ptr, visited=None):
    """
    Yield instance patterns (lists of steps) for every place target_ptr is used.
    Recursively resolves through definitions: if the $ref appears inside
    definitions/X/..., it first finds where #/definitions/X is used and prepends
    those patterns.
    """
    if visited is None:
        visited = frozenset()
    if target_ptr in visited:
        return
    visited = visited | {target_ptr}

    for schema_path in find_ref_schema_paths(schema, target_ptr):
        if schema_path and schema_path[0] == "definitions":
            # The ref is inside a definition — resolve the parent definition first
            def_name = schema_path[1]
            def_ptr = f"#/definitions/{def_name}"
            remaining_pattern = schema_path_to_instance_pattern(schema_path[2:])
            for parent_pattern in find_instance_patterns(schema, def_ptr, visited):
                yield parent_pattern + remaining_pattern
        else:
            yield schema_path_to_instance_pattern(schema_path)


def enumerate_instance_paths(instance, pattern):
    """
    Walk the instance following the pattern, yielding every matching path as a
    list of keys/indices.
    """
    if not pattern:
        yield []
        return

    (kind, *args), *rest = pattern

    if kind == "key":
        name = args[0]
        if isinstance(instance, dict) and name in instance:
            for suffix in enumerate_instance_paths(instance[name], rest):
                yield [name] + suffix

    elif kind == "array":
        if isinstance(instance, list):
            for idx, child in enumerate(instance):
                for suffix in enumerate_instance_paths(child, rest):
                    yield [idx] + suffix


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <subschema-pointer> <schema-file> <instance-file>",
            file=sys.stderr,
        )
        sys.exit(1)

    target_ptr, schema_file, instance_file = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(schema_file) as f:
        schema = json.load(f)
    with open(instance_file) as f:
        instance = json.load(f)

    count = 0
    for pattern in find_instance_patterns(schema, target_ptr):
        for instance_path in enumerate_instance_paths(instance, pattern):
            print(json.dumps(instance_path))
            count += 1

if __name__ == "__main__":
    main()
