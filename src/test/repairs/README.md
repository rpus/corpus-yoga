# Repair Scripts

Each script takes a schema path as its first argument and writes back in place.
Scripts marked with † take additional arguments — see the module docstring.

Repair → diagnostic is one-to-many in one case: `documentation.every_definition_has_title_and_description.py` can also flip `naming.title_matches_key` FAIL→PASS as a side effect.

| Script | What it does | Diagnostic pre → post |
| --- | --- | --- |
| [`naming.upper_camel_case.py`](naming.upper_camel_case.py) † | Rename a definition key and all `$ref`s; takes `<schema> <old> <new>` | `naming.upper_camel_case` FAIL→PASS; `naming.title_matches_key` FAIL→PASS if title matched old key |
| [`naming.title_matches_key.py`](naming.title_matches_key.py) | Set every `title` to its definition key | `naming.title_matches_key` FAIL→PASS |
| [`naming.root_schema_title_matches_filename.py`](naming.root_schema_title_matches_filename.py) | Set root `title` to filename stem | `naming.root_schema_title_matches_filename` FAIL→PASS |
| [`structure.bfs_order.py`](structure.bfs_order.py) | Reorder all definitions into breadth-first referential encounter order | `structure.bfs_order` FAIL→PASS; `structure.field_order` unaffected |
| [`structure.field_order.py`](structure.field_order.py) | Reorder keys so `title, description` are first in every definition | `structure.field_order` FAIL→PASS; `structure.bfs_order` unaffected |
| [`structure.definitions_at_bottom.py`](structure.definitions_at_bottom.py) | Move `definitions` to last key in root schema | `structure.definitions_at_bottom` FAIL→PASS |
| [`structure.no_redundant_additional_properties_true.py`](structure.no_redundant_additional_properties_true.py) | Delete explicit `additionalProperties: true` | `structure.no_redundant_additional_properties_true` FAIL→PASS; `composition.no_additional_properties_on_subtypes` unaffected |
| [`structure.required_subset_of_properties.py`](structure.required_subset_of_properties.py) | Remove `required` entries absent from `properties` | `structure.required_subset_of_properties` FAIL→PASS |
| [`structure.pattern_constraints_enforced.py`](structure.pattern_constraints_enforced.py) | Extract regex from `description` into `pattern` field | `structure.pattern_constraints_enforced` FAIL→PASS |
| [`documentation.every_definition_has_title_and_description.py`](documentation.every_definition_has_title_and_description.py) | Insert `"TODO: document."` stub where `title` or `description` is missing | `documentation.every_definition_has_title_and_description` FAIL→PASS; `naming.title_matches_key` FAIL→PASS if missing title was the only violation; `documentation.descriptions_end_with_full_stop` unaffected |
| [`documentation.descriptions_end_with_full_stop.py`](documentation.descriptions_end_with_full_stop.py) | Append `.` to descriptions missing terminal punctuation | `documentation.descriptions_end_with_full_stop` FAIL→PASS |
| [`documentation.discriminator_fields_annotated.py`](documentation.discriminator_fields_annotated.py) | Add `"(discriminator)"` to discriminator field descriptions | `documentation.discriminator_fields_annotated` FAIL→PASS |
| [`composition.base_schemas_closed.py`](composition.base_schemas_closed.py) | Add `additionalProperties: false` to base schemas | `composition.base_schemas_closed` FAIL→PASS |

The `composition.*` principles (other than `composition.base_schemas_closed`) have no repair scripts — failures there require structural judgement.
