#!/usr/bin/env python
"""
schema_recommendations.py - Given an instance document and a schema file,
output recommendations for improving the instance's conformance to the schema.

Usage:
    src/run_python_script.sh src/test/dev/schema_recommendations.py <instance-file> <schema-file>
"""

import inspect
import json
import sys


def properties_out_of_uniform_order(instance, schema):
    """Check whether object properties appear in a consistent order across all instances, yet the schema lists a different order."""
    return "(test is not yet implemented)"


def property_always_present_but_not_required(instance, schema):
    """Check whether any property appears in every instance object but is absent from 'required'."""
    return "(test is not yet implemented)"


def required_order_differs_from_properties(schema):
    """Check whether the order of 'required' entries matches the order of 'properties' keys."""
    return "(test is not yet implemented)"


def enum_value_never_used(instance, schema):
    """Check whether any enum value defined in the schema never appears in the instance."""
    return "(test is not yet implemented)"


def branch_never_deemed_valid(instance, schema):
    """Check whether any branch of a oneOf/anyOf is never satisfied by any instance value."""
    return "(test is not yet implemented)"


def definitions_not_in_breadth_first_order(schema):
    """Check whether the definitions appear in breadth-first referential encounter order starting from the root, i.e. the order in which a BFS traversal of $ref links first visits each definition."""
    return "(test is not yet implemented)"


def definition_unused(schema):
    """Check whether any definition in the schema is never referenced via $ref anywhere in the schema."""
    return "(test is not yet implemented)"


def properties_without_additional_properties(schema):
    """Check whether any object schema that defines 'properties' does not also set 'additionalProperties'.
    Note: adding 'additionalProperties: false' to a schema can turn previously passing instances into failures."""
    return "(test is not yet implemented)"


def known_enum_values_complete(instance, schema, domain):
    """Check whether any enum in the schema is missing values that are known from domain knowledge to be valid."""
    return "(test is not yet implemented)"


DOMAIN = {
    # e.g. "role": ["user", "assistant", "system"]
}

CHECKS = [
    ("properties out of uniform order",         properties_out_of_uniform_order),
    ("property always present but not required", property_always_present_but_not_required),
    ("required order differs from properties",   required_order_differs_from_properties),
    ("enum value never used",                    enum_value_never_used),
    ("branch never deemed valid",                branch_never_deemed_valid),
    ("definitions not in breadth-first order",   definitions_not_in_breadth_first_order),
    ("definition unused",                        definition_unused),
    ("properties without additionalProperties",  properties_without_additional_properties),
    ("known enum values complete",               known_enum_values_complete),
]


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <instance-file> <schema-file>", file=sys.stderr)
        sys.exit(1)

    instance_file, schema_file = sys.argv[1], sys.argv[2]

    with open(instance_file) as f:
        instance = json.load(f)
    with open(schema_file) as f:
        schema = json.load(f)

    for name, check in CHECKS:
        params = inspect.signature(check).parameters
        if "domain" in params:
            result = check(instance, schema, DOMAIN)
        elif "instance" in params:
            result = check(instance, schema)
        else:
            result = check(schema)
        print(f"--- {name} ---")
        print(result)


if __name__ == "__main__":
    main()
