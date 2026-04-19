# the restriction algebra

## core observation

Every keyword in JSON Schema Draft 4 is a restriction — it narrows the set of
documents that are valid against the schema. The schema is a conjunction of
constraints, each carving away invalid instances, converging on the set of
conforming documents.

This observation has a precise consequence: every Draft 4 schema is equivalent
to an `allOf` whose array contains the restrictions of the original.

```json
{
  "type": "string",
  "minLength": 3,
  "pattern": "^[a-z]"
}
```

is exactly equivalent to:

```json
{
  "allOf": [
    { "type": "string" },
    { "minLength": 3 },
    { "pattern": "^[a-z]" }
  ]
}
```

## canonical form theorem

Every Draft 4 schema has a canonical form: an `allOf` of atomic restrictions
in a declared canonical order. Two schemas are semantically equivalent if and
only if their canonical forms are identical (modulo value equality).

## purity test

A proposed keyword passes the purity test if and only if it can appear as a
standalone element of an `allOf` array with no dependency on the evaluation
state of other keywords.

`if`/`then`/`else` (Draft 7) fails this test: its meaning depends on the
outcome of evaluating another sub-schema. It is a procedure, not a restriction.
This is why `schema+json` flags post-Draft-4 keywords as intrusions.

## three keyword sets

| set | keywords | role |
|---|---|---|
| restriction | `type`, `enum`, `allOf`, `anyOf`, `oneOf`, `not`, `properties`, `additionalProperties`, `patternProperties`, `required`, `dependencies`, `items`, `additionalItems`, `uniqueItems`, `minItems`, `maxItems`, `minProperties`, `maxProperties`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minLength`, `maxLength`, `pattern`, `format` | validate documents |
| structural | `id`, `definitions`, `$ref` | name and reference schemas |
| annotation | `$schema`, `title`, `description`, `default` | describe schemas to humans |

## canonical order

Restrictions should be ordered from most-general to most-specific, with
cheapest (highest elimination rate) first. The default canonical order is
declared in `package.json` and user-configurable per domain.

The canonical order is a hypothesis about the data distribution. It can be
verified empirically: run the validator with and without the declared order,
measure rejection rates at each gate.

## three-allOf separation (planned)

The fully canonical form separates the three keyword sets into distinct `allOf`
arrays:

```json
{
  "allOf": [{ "$schema": "..." }, { "title": "..." }],
  "allOf": [{ "id": "..." }, { "definitions": {} }],
  "allOf": [{ "type": "object" }, { "required": ["name"] }]
}
```

- annotation `allOf`: human-facing shell; freely changeable
- structural `allOf`: identity and reference machinery
- restriction `allOf`: the bedrock; changes are semantic changes

This separation makes schema diffs meaningful at two independent levels.
