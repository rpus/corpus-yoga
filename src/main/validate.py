#!/usr/bin/env python
"""
Usage:
  src/run_python_script.sh src/main/validate.py <data.json> <schema.json>
  src/run_python_script.sh src/main/validate.py <data.json#/path/to/value> <schema.json#/definitions/Foo>

Fragment identifiers are JSON Pointers (RFC 6901); % encoding is supported.
"""

import os
import sys
import json
import jsonschema
from urllib.parse import unquote
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4


def parse_arg(arg):
    """Split a file argument into (path, pointer). Pointer is '' if no fragment."""
    if '#' in arg:
        path, fragment = arg.split('#', 1)
        return path, unquote(fragment)
    return arg, ''


def follow_pointer(doc, pointer):
    """Walk a JSON Pointer (RFC 6901) and return the referenced value."""
    if not pointer:
        return doc
    for segment in pointer.lstrip('/').split('/'):
        segment = segment.replace('~1', '/').replace('~0', '~')
        doc = doc[int(segment)] if isinstance(doc, list) else doc[segment]
    return doc


def validate(data_path, schema_path, data_ptr='', schema_ptr=''):
    """Validate data_path against schema_path. Returns output lines."""
    with open(data_path) as f:
        data = follow_pointer(json.load(f), data_ptr)
    with open(schema_path) as f:
        root_schema = json.load(f)
    base_uri = f'file://{os.path.abspath(schema_path)}'
    registry = Registry().with_resource(base_uri, Resource.from_contents(root_schema, default_specification=DRAFT4))
    schema = {"$ref": f"{base_uri}#{schema_ptr}"} if schema_ptr else root_schema
    try:
        jsonschema.Draft4Validator(schema, registry=registry).validate(data)
        return ['Valid!']
    except jsonschema.ValidationError as e:
        return [f'Validation error: {e.message}', f'Path: {list(e.absolute_path)}']
    except jsonschema.SchemaError as e:
        return [f'Schema error: {e.message}']


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: python {sys.argv[0]} <data.json> <schema.json>')
        sys.exit(1)
    data_path, data_ptr = parse_arg(sys.argv[1])
    schema_path, schema_ptr = parse_arg(sys.argv[2])
    for line in validate(data_path, schema_path, data_ptr, schema_ptr):
        print(line)
