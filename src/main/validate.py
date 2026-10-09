#!/usr/bin/env python
"""
Usage:
  src/run_python_script.sh src/main/validate.py <data.json> <schema.json>
  src/run_python_script.sh src/main/validate.py <data.json#/path/to/value> <schema.json#/definitions/Foo>

Fragment identifiers are JSON Pointers (RFC 6901); % encoding is supported.

A refusal is reported as the fault a reader acts on (#848): its first line names the
property at fault by its path within the instance and the validator's words for it,
the second the instance path, the third the schema node whose keyword found it.
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


def _refused(error):
    """Whether the instance's discriminator refuses the alternative this error belongs
    to: an enum or const fault on a property at the alternative's own level, or a
    oneOf/anyOf every alternative of which is so refused."""
    if error.context:
        return all(any(_refused(sub) for sub in subs) for subs in _alternatives(error).values())
    return error.validator in ('enum', 'const') and len(error.relative_path) == 1


def _alternatives(error):
    """The context of a oneOf/anyOf error by alternative: index to its faults."""
    alternatives = {}
    for sub in error.context:
        alternatives.setdefault(sub.relative_schema_path[0], []).append(sub)
    return alternatives


def legible(error):
    """The fault a reader acts on, found through each oneOf/anyOf: the alternative the
    instance's discriminator selects - no alternative is refused by it - with the fewest
    faults, and within it the deepest; the top error otherwise."""
    while error.context:
        alternatives = _alternatives(error)
        selected = [subs for subs in alternatives.values() if not any(_refused(sub) for sub in subs)]
        subs = min(selected or alternatives.values(), key=len)
        error = max(subs, key=lambda sub: len(sub.absolute_path))
    return error


def _resolve(node, root, at):
    """A local $ref followed: the node it names and that node's pointer."""
    while isinstance(node, dict) and isinstance(node.get('$ref'), str) and node['$ref'].startswith('#/'):
        at = node['$ref'][1:]
        node = follow_pointer(root, at)
    return node, at


def node_pointer(root, schema_path, start=''):
    """The pointer, within the schema file, of the node whose keyword found the fault:
    the error's schema path walked from the root (or from start, a pointer), each $ref
    followed as it is met - jsonschema's path crosses refs without naming them - and the
    final keyword dropped."""
    node, at = follow_pointer(root, start), start
    for step in list(schema_path)[:-1]:
        node, at = _resolve(node, root, at)
        if step == '$ref':
            continue
        if isinstance(node, dict) and step in node:
            node = node[step]
        elif isinstance(node, list) and isinstance(step, int) and step < len(node):
            node = node[step]
        else:
            break
        at = f'{at}/{step}'
    node, at = _resolve(node, root, at)
    return '#' + at


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
    except jsonschema.ValidationError as top:
        fault = legible(top)
        where = '/'.join(str(step) for step in fault.absolute_path if not isinstance(step, int))
        return [f'Validation error: {where}: {fault.message}' if where else f'Validation error: {fault.message}',
                f'Path: {list(fault.absolute_path)}',
                f'Schema path: {node_pointer(root_schema, fault.absolute_schema_path, schema_ptr)}']
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
