#!/usr/bin/env python
"""
schema_path.py - Given a jsonschema instance error path and a schema file,
output the JSON pointer to the subschema at the error site.

Usage:
    python src/main/schema_path.py "[4, 'chat_messages', 8, 'files', 0]" rsc/schema/conversations.json

Output:
    JSON pointer string, e.g. #/definitions/MessageFile/properties/file_uuid
"""

import ast
import json
import sys


def resolve_ref(schema, root, pointer="#"):
    """If schema is a $ref, follow it and return (resolved_schema, new_pointer)."""
    if "$ref" in schema:
        ref = schema["$ref"]
        # Only handle local refs of the form #/definitions/Foo
        if ref.startswith("#/"):
            parts = ref[2:].split("/")
            node = root
            for part in parts:
                node = node[part]
            return node, ref
    return schema, pointer


def follow_path(instance_path, schema, root):
    """
    Walk the schema following the instance path.
    Returns the JSON pointer string to the schema node at the error site.
    """
    current = schema
    pointer = "#"

    for step in instance_path:
        current, pointer = resolve_ref(current, root, pointer)

        if isinstance(step, int):
            # Array index: follow items
            if "items" in current:
                items = current["items"]
                if isinstance(items, list):
                    # Per-index schemas
                    if step < len(items):
                        pointer = pointer + "/items/" + str(step)
                        current = items[step]
                    else:
                        # Beyond tuple validation, no schema to follow
                        break
                else:
                    pointer = pointer + "/items"
                    current = items
            else:
                break

        else:
            # String key: follow properties
            if "properties" in current and step in current["properties"]:
                pointer = pointer + "/properties/" + step
                current = current["properties"][step]
            else:
                # May be in allOf/oneOf/anyOf - search them
                found = False
                for combiner in ("allOf", "oneOf", "anyOf"):
                    if combiner in current:
                        for i, sub in enumerate(current[combiner]):
                            sub_resolved, _ = resolve_ref(sub, root)
                            if "properties" in sub_resolved and step in sub_resolved["properties"]:
                                pointer = pointer + "/" + combiner + "/" + str(i) + "/properties/" + step
                                current = sub_resolved["properties"][step]
                                found = True
                                break
                    if found:
                        break
                if not found:
                    print(f"Warning: could not follow step '{step}' from {pointer}", file=sys.stderr)
                    break

    # Final resolve
    current, pointer = resolve_ref(current, root, pointer)
    return pointer


def parse_instance_path(path_str):
    """Parse a jsonschema error path string like [4, 'chat_messages', 8, 'files', 0]."""
    return ast.literal_eval(path_str)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <instance-path> <schema-file>", file=sys.stderr)
        sys.exit(1)

    path_str = sys.argv[1]
    schema_file = sys.argv[2]

    try:
        instance_path = parse_instance_path(path_str)
    except Exception as e:
        print(f"Error parsing instance path: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(schema_file) as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema: {e}", file=sys.stderr)
        sys.exit(1)

    pointer = follow_path(instance_path, schema, schema)
    print(pointer)


if __name__ == "__main__":
    main()
