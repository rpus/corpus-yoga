"""structure.keywords_declared — Every key at a schema position is a keyword the dialect declares: draft-04's meta-schema, or JSON Reference's $ref."""
import json
import sys
from schema_walk import schema_nodes, kind


with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
for path, node in schema_nodes(schema):
    for key in node:
        if kind(key) is None:
            fails.append(f'{path}: "{key}" is no draft-04 keyword (rsc/reference/JSONSchema/draft-04/schema.json declares none)')

if fails:
    print('FAIL structure.keywords_declared:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.keywords_declared')
