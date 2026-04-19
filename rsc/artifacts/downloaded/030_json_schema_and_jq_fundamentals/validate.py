"""
validate.py  —  validate conversations.json against conversations.schema.json

For best error messages, use the expanded schema produced by expand_schema.py:
    python expand_schema.py conversations.schema.json > conversations.schema.expanded.json
    python validate.py conversations.json conversations.schema.expanded.json

oneOf failures are disambiguated by finding the branch whose discriminator
field (type or name) matches the instance, and reporting only that branch's
errors rather than all branches simultaneously.

No $ref resolution is needed here — use expand_schema.py to eliminate refs
before validation.

Usage:
    python validate.py <data.json> <schema.json>
"""
import os, sys, json
import jsonschema

DISCRIMINATORS = ('type', 'name')

def load_and_report(path):
    size = os.path.getsize(path)
    with open(path) as f:
        lines = f.readlines()
    data = json.loads(''.join(lines))
    print(f'{path}: {len(lines):,} lines, {size:,} bytes')
    return data

def discriminator_value(schema):
    """
    Return (field, value) if this schema branch has a single-value enum
    on a discriminator field, else None. Also checks allOf branches.
    """
    props = schema.get('properties', {})
    for field in DISCRIMINATORS:
        if field in props:
            enum = props[field].get('enum')
            if enum and len(enum) == 1:
                return field, enum[0]
    for branch in schema.get('allOf', []):
        disc = discriminator_value(branch)
        if disc:
            return disc
    return None

def find_best_branch(error):
    """
    Given a oneOf ValidationError, find the branch whose discriminator
    matched the instance and return its sub-error. Recurses to handle
    nested oneOfs (e.g. ToolUseBlock has allOf + oneOf).
    Falls back to the original error if no discriminator match is found.
    """
    if error.validator != 'oneOf' or not error.context:
        return error

    instance = error.instance
    if not isinstance(instance, dict):
        return error

    for sub_error in error.context:
        disc = discriminator_value(sub_error.schema)
        if disc:
            field, value = disc
            if instance.get(field) == value:
                return find_best_branch(sub_error) if sub_error.context else sub_error

    return error

def format_error(error):
    best = find_best_branch(error)
    path = list(best.absolute_path)
    return f'Validation error: {best.message}\nPath: {path}'

if len(sys.argv) != 3:
    print(f'Usage: python {sys.argv[0]} <data.json> <schema.json>')
    sys.exit(1)

data   = load_and_report(sys.argv[1])
schema = load_and_report(sys.argv[2])

try:
    jsonschema.Draft4Validator(schema).validate(data)
    print('Valid!')
except jsonschema.ValidationError as e:
    print(format_error(e))
except jsonschema.SchemaError as e:
    print(f'Schema error: {e.message}')
