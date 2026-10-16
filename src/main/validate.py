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
    oneOf/anyOf at that level every alternative of which is so refused. A union deeper
    in the instance - a turn's content block - is not the alternative's discriminator:
    its refusal is that union's to judge, reached by the descent (#894)."""
    if error.context:
        return not error.relative_path and all(any(_refused(sub) for sub in subs) for subs in _alternatives(error).values())
    return error.validator in ('enum', 'const') and len(error.relative_path) == 1


def _discriminators(error):
    """The enum or const faults a refusal rests on: the error itself, or, through a nested
    oneOf/anyOf every alternative of which is refused, each alternative's own."""
    if not error.context:
        return [error]
    return [leaf for subs in _alternatives(error).values() for sub in subs if _refused(sub) for leaf in _discriminators(sub)]


def _alternatives(error):
    """The context of a oneOf/anyOf error by alternative: index to its faults."""
    alternatives = {}
    for sub in error.context:
        alternatives.setdefault(sub.relative_schema_path[0], []).append(sub)
    return alternatives


def _undeclared(error, alternatives):
    """Where the instance's discriminator refuses every alternative of a oneOf/anyOf, the
    verdict is the union's (#894): the discriminator's property, the value the instance
    carries, and the values the alternatives declare - never an alternative chosen by the
    count of its faults, which would name a type the record was not of."""
    refusals = [[leaf for sub in subs if _refused(sub) for leaf in _discriminators(sub)] for subs in alternatives.values()]
    if not all(refusals) or len({tuple(leaf.relative_path) for leaves in refusals for leaf in leaves}) != 1:
        return None
    refusals = [leaf for leaves in refusals for leaf in leaves]
    # every discriminator sits at the alternative's own level: a refusal that rests on a
    # nested union's leaves is that union's to judge, found by the descent, never this one's
    if any(len(leaf.absolute_path) != len(error.absolute_path) + 1 for leaf in refusals):
        return None
    prop = refusals[0].relative_path[0]
    declared = sorted({str(v) for sub in refusals
                       for v in (sub.validator_value if isinstance(sub.validator_value, list) else [sub.validator_value])})
    carried = refusals[0].instance
    message = f'{carried!r} is not a {prop} the union declares - declared: {declared}'
    return jsonschema.ValidationError(message, path=list(error.absolute_path) + [prop],
                                      schema_path=list(error.absolute_schema_path), instance=carried)


def legible(error):
    """The fault a reader acts on, found through each oneOf/anyOf: the alternative the
    instance's discriminator selects - no alternative is refused by it - with the fewest
    faults, and within it the deepest; the union itself where the discriminator refuses
    every alternative (#894); the top error otherwise."""
    while error.context:
        alternatives = _alternatives(error)
        selected = [subs for subs in alternatives.values() if not any(_refused(sub) for sub in subs)]
        if not selected:
            undeclared = _undeclared(error, alternatives)
            if undeclared is not None:
                return undeclared
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
