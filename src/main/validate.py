#!/usr/bin/env python
"""
Usage:
  src/run_python_script.sh src/main/validate.py <data.json> <schema.json>
  src/run_python_script.sh src/main/validate.py <data.json#/path/to/value> <schema.json#/definitions/Foo>

Fragment identifiers are JSON Pointers (RFC 6901); % encoding is supported.

A refusal is reported as the fault a reader acts on (issues/848): its first line names the
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
    its refusal is that union's to judge, reached by the descent (issues/894)."""
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
    verdict is the union's (issues/894): the discriminator's property, the value the instance
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


def _name(alternative):
    """An alternative as a reader names it: the definition it refers to, its type, or its
    index among the union's."""
    if isinstance(alternative, dict):
        if isinstance(alternative.get('$ref'), str):
            return alternative['$ref'].rsplit('/', 1)[-1]
        if isinstance(alternative.get('type'), str):
            return alternative['type']
    return 'alternative'


def _unmatched(error):
    """The union's verdict where no single alternative is selected and no discriminator
    declares a set (issues/894): the instance matches none of the alternatives, named - the
    library's own sentence, which is all a reader can honestly be told, never an
    alternative chosen by the count of its faults."""
    names = ', '.join(_name(alternative) for alternative in error.validator_value)
    return jsonschema.ValidationError(f'matches none of: {names}', path=list(error.absolute_path),
                                      schema_path=list(error.absolute_schema_path), instance=error.instance)


def legible(error):
    """The fault a reader acts on, found through each oneOf/anyOf: within the one
    alternative the instance's discriminator selects - no alternative is refused by it -
    the deepest fault; the union itself where the discriminator refuses every alternative
    (issues/894, the declared set named) or selects no single one (the alternatives named); the
    top error otherwise. No fault count chooses: at a discriminated union the verdict is a
    function of the discriminator's value and the schema, and at an undiscriminated one
    it is the union's."""
    while error.context:
        alternatives = _alternatives(error)
        selected = [subs for subs in alternatives.values() if not any(_refused(sub) for sub in subs)]
        if len(selected) != 1:
            undeclared = _undeclared(error, alternatives) if not selected else None
            return undeclared if undeclared is not None else _unmatched(error)
        error = max(selected[0], key=lambda sub: len(sub.absolute_path))
    return error


def _resolve(node, root, at):
    """A local $ref followed: the node it names and that node's pointer."""
    while isinstance(node, dict) and isinstance(node.get('$ref'), str) and node['$ref'].startswith('#/'):
        at = node['$ref'][1:]
        node = follow_pointer(root, at)
    return node, at


def node_pointer(root, schema_path, start=''):
    """The pointer, within the schema file, of the node whose keyword found the fault, as
    a JSON Pointer string (RFC 6901, ~ and / escaped, no fragment mark): the error's
    schema path walked from the root (or from start, a pointer), each $ref followed as it
    is met - jsonschema's path crosses refs without naming them - and the final keyword
    dropped."""
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
        at = f'{at}/{escaped(step)}'
    node, at = _resolve(node, root, at)
    return at


def escaped(step) -> str:
    """One step of a JSON Pointer, its ~ and / escaped (RFC 6901)."""
    return str(step).replace('~', '~0').replace('/', '~1')


def fault(data_path, schema_path, data_ptr='', schema_ptr=''):
    """The fault a reader acts on, as data (issues/848, issues/952): None where the data validates;
    otherwise its message, the property at fault (where), the instance path as a JSON
    Pointer (path) and as steps, the rule it fails - the keyword and its value - and the
    schema node whose keyword found it (schema), a JSON Pointer in the same form. A schema
    error is a fault with its message alone."""
    with open(data_path) as f:
        data = follow_pointer(json.load(f), data_ptr)
    with open(schema_path) as f:
        root_schema = json.load(f)
    base_uri = f'file://{os.path.abspath(schema_path)}'
    registry = Registry().with_resource(base_uri, Resource.from_contents(root_schema, default_specification=DRAFT4))
    schema = {"$ref": f"{base_uri}#{schema_ptr}"} if schema_ptr else root_schema
    try:
        jsonschema.Draft4Validator(schema, registry=registry).validate(data)
        return None
    except jsonschema.ValidationError as top:
        found = legible(top)
        steps = list(found.absolute_path)
        return {'message': found.message,
                'where': '/'.join(str(step) for step in steps if not isinstance(step, int)),
                'path': '/' + '/'.join(escaped(step) for step in steps),
                'steps': steps,
                'rule': _rule(found),
                'schema': node_pointer(root_schema, found.absolute_schema_path, schema_ptr)}
    except jsonschema.SchemaError as e:
        return {'message': f'Schema error: {e.message}', 'where': '', 'path': None, 'steps': [], 'rule': None, 'schema': None}


def _rule(found) -> str | None:
    """The keyword and the value the instance fails, `type ["string", "object"]`; None for
    a verdict the union gives (issues/894), which names no keyword of its own."""
    keyword = found.validator if isinstance(found.validator, str) else None
    try:
        value = json.dumps(found.validator_value)
    except TypeError:
        return None
    return f'{keyword} {value}' if keyword else None


def lines(found) -> list[str]:
    """A fault as the validator's lines: `Valid!` for none; else the fault's words, then
    `Path:` and `Schema path:` where it names an instance path (src/main/validate_inspection.py
    reads those two) - the schema node with the fragment mark, as the CLI takes a pointer."""
    if found is None:
        return ['Valid!']
    if found['path'] is None:
        return [found['message']]
    where = found['where']
    return [f'Validation error: {where}: {found["message"]}' if where else f'Validation error: {found["message"]}',
            f'Path: {found["steps"]}',
            f'Schema path: #{found["schema"]}']


def validate(data_path, schema_path, data_ptr='', schema_ptr=''):
    """Validate data_path against schema_path. Returns output lines - lines(fault(...))."""
    return lines(fault(data_path, schema_path, data_ptr, schema_ptr))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: python {sys.argv[0]} <data.json> <schema.json>')
        sys.exit(1)
    data_path, data_ptr = parse_arg(sys.argv[1])
    schema_path, schema_ptr = parse_arg(sys.argv[2])
    for line in validate(data_path, schema_path, data_ptr, schema_ptr):
        print(line)
