# canonical form

## definition

A schema is in canonical form when:

1. keywords are partitioned into three groups: structural, restriction, annotation
2. within each group, keywords appear in the declared canonical order
3. (planned) each group occupies a distinct `allOf` array

## canonical order

The default canonical order for restrictions (user-configurable):

```
type, enum,
allOf, anyOf, oneOf, not,
properties, additionalProperties, patternProperties, required, dependencies,
items, additionalItems, uniqueItems, minItems, maxItems,
minProperties, maxProperties,
minimum, maximum, exclusiveMinimum, exclusiveMaximum, multipleOf,
minLength, maxLength, pattern, format
```

rationale: type and enum first (cheapest, highest elimination); logical
combinators next; structural object/array constraints; numeric/string
constraints last (most specific, applied only after type is confirmed).

## formatter (planned)

The `schema+json` formatter is the canonicaliser. Format on save normalises
the schema to canonical form. The diff between two formatted schema versions
is a pure semantic diff — no noise from reordering.

## propertyOrder (proposed)

A `propertyOrder` keyword (conservative extension of Draft 4) would allow
canonical order to be declared inside the schema itself, overriding the
global setting for that schema's domain.

```json
{
  "propertyOrder": ["type", "required", "properties", "minLength"],
  "type": "object",
  "required": ["name"],
  "properties": { "name": { "type": "string" } }
}
```

This would have been a sane Draft 5. Every subsequent draft instead added
imperative constructs, breaking the restriction algebra.
