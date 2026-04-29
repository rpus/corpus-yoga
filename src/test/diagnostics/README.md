# Diagnostic Scripts

Each script takes a schema path as its sole argument, exits 0 on pass, 1 on fail.

Diagnostic → repair is mostly one-to-one, with one many-to-one case: both `naming.upper_camel_case` and `naming.title_matches_key` can be repaired by `naming.upper_camel_case.py`, which fixes both atomically when the mismatch is a rename.

| Script | What it checks | Repair script |
| --- | --- | --- |
| [`naming.upper_camel_case.py`](./naming.upper_camel_case.py) | All definition names are UpperCamelCase | [`naming.upper_camel_case.py`](../repairs/naming.upper_camel_case.py) † |
| [`naming.title_matches_key.py`](./naming.title_matches_key.py) | Every definition's `title` matches its key | [`naming.title_matches_key.py`](../repairs/naming.title_matches_key.py) or [`naming.upper_camel_case.py`](../repairs/naming.upper_camel_case.py) † |
| [`naming.root_schema_title_matches_filename.py`](./naming.root_schema_title_matches_filename.py) | Root schema `title` matches filename stem | [`naming.root_schema_title_matches_filename.py`](../repairs/naming.root_schema_title_matches_filename.py) |
| [`naming.property_keys_lowercase.py`](./naming.property_keys_lowercase.py) | All property keys are lowercase or snake_case | Manual — property rename requires verifying data field names |
| [`structure.field_order.py`](./structure.field_order.py) | Every definition begins with `title`, `description` | [`structure.field_order.py`](../repairs/structure.field_order.py) |
| [`structure.bfs_order.py`](./structure.bfs_order.py) | Definitions are in breadth-first referential encounter order | [`structure.bfs_order.py`](../repairs/structure.bfs_order.py) |
| [`structure.definitions_at_bottom.py`](./structure.definitions_at_bottom.py) | `definitions` is the last key in the root schema | [`structure.definitions_at_bottom.py`](../repairs/structure.definitions_at_bottom.py) |
| [`structure.required_subset_of_properties.py`](./structure.required_subset_of_properties.py) | Every `required` field is listed in `properties` | [`structure.required_subset_of_properties.py`](../repairs/structure.required_subset_of_properties.py) |
| [`structure.no_redundant_additional_properties_true.py`](./structure.no_redundant_additional_properties_true.py) | No explicit `additionalProperties: true` | [`structure.no_redundant_additional_properties_true.py`](../repairs/structure.no_redundant_additional_properties_true.py) |
| [`structure.pattern_constraints_enforced.py`](./structure.pattern_constraints_enforced.py) | String fields with a regex in `description` also have a `pattern` constraint | [`structure.pattern_constraints_enforced.py`](../repairs/structure.pattern_constraints_enforced.py) |
| [`structure.property_order_matches_data.py`](./structure.property_order_matches_data.py) | Property order in key definitions matches canonical field order from observed data | Manual — update canonical order in script after re-deriving from export data |
| [`structure.all_definitions_reachable.py`](./structure.all_definitions_reachable.py) | Every definition is reachable from root via `$ref` (known stubs excepted) | Manual — remove or connect the unreachable definition |
| [`structure.no_dangling_refs.py`](./structure.no_dangling_refs.py) | Every `$ref` target exists in `definitions` | Manual — add the missing definition or fix the `$ref` |
| [`structure.minItems_on_non_empty_arrays.py`](./structure.minItems_on_non_empty_arrays.py) | Non-empty arrays have `minItems: 1` | Manual — verify against export data before adding constraint |
| [`documentation.every_definition_has_title_and_description.py`](./documentation.every_definition_has_title_and_description.py) | Every definition has both `title` and `description` | [`documentation.every_definition_has_title_and_description.py`](../repairs/documentation.every_definition_has_title_and_description.py) |
| [`documentation.null_only_fields_documented.py`](./documentation.null_only_fields_documented.py) | `null`-typed fields note their empirical basis in their description | Manual — see inline snippet in principles doc |
| [`documentation.open_set_enums_documented.py`](./documentation.open_set_enums_documented.py) | Likely open-set enums say so in their description | Manual — see inline snippet in principles doc |
| [`documentation.discriminator_fields_annotated.py`](./documentation.discriminator_fields_annotated.py) | Discriminator fields are annotated with `(discriminator)` | Manual — verify which field is the discriminator before annotating |
| [`composition.discriminated_union_pattern.py`](./composition.discriminated_union_pattern.py) | Structural `oneOf` unions have a `Has*DiscriminatorProperty` in `allOf` | Manual — requires structural judgement |
| [`composition.discriminator_values_disjoint.py`](./composition.discriminator_values_disjoint.py) | Discriminator enum values across `oneOf` branches are disjoint | Manual — requires structural judgement |
| [`composition.base_schemas_closed.py`](./composition.base_schemas_closed.py) | Base schemas have `additionalProperties: false` | Manual — verify all base fields are accounted for first |
| [`composition.wrapper_has_five_fields.py`](./composition.wrapper_has_five_fields.py) | Union wrapper schemas have exactly five fields: `title`, `description`, `type`, `allOf`, `oneOf` | Manual — see inline snippet in principles doc |
| [`composition.no_additional_properties_on_subtypes.py`](./composition.no_additional_properties_on_subtypes.py) | Subtype schemas do not set `additionalProperties` (delegated to base) | Manual — see inline snippet in principles doc |
| [`composition.base_not_used_directly.py`](./composition.base_not_used_directly.py) | Base schemas are not referenced directly in `oneOf` or `properties` | Manual — requires structural judgement |
| [`empirical.oneOf_branches_evidenced.py`](./empirical.oneOf_branches_evidenced.py) | No `oneOf` branch is annotated as unevidenced (`"not observed"` in description) | Manual — evidence the branch or remove it |
| [`empirical.nullable_fields_surveyed.py`](./empirical.nullable_fields_surveyed.py) | All `oneOf`-with-null constructs are named definitions with descriptions | Manual — promote to a named definition and document the nullable nature |

† `naming.upper_camel_case.py` repair takes `<schema> <old> <new>` — not a batch fix.
