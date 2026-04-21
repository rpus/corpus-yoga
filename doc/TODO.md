# TODO

The principles document is clear. Four principles are marked enforced but have only inline snippets, no standalone script and not registered in `pre_commit.py`:

- `structure.pattern_constraints_enforced` — even flagged "advisory — no standalone script yet" in its own inline comment, contradicting the enforced heading
- `structure.property_order_matches_data` — inline Python only
- `empirical.oneOf_branches_evidenced` — inline Python only
- `empirical.nullable_fields_surveyed` — inline Python only

Plus two empirical ones that are handled differently:

- `empirical.validate_against_all_known_exports` — implemented directly in `pre_commit.py` via the `EXPECTED_PASS` matrix rather than a standalone script
- `naming.subtype_naming_convention` — explicitly documented as covered indirectly by `naming.upper_camel_case` + `naming.title_matches_key`

So the genuine gap is those first four. Want me to start implementing them as standalone scripts?

`repairs/composition.base_schemas_closed.py`
`repairs/documentation.discriminator_fields_annotated.py`

These were either never promoted to the repo or were deliberately dropped at some point. Worth checking whether they were superseded or just abandoned.

See also: `src/main/schema_recommendations.py`
