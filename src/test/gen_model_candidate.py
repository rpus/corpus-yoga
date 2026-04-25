"""
gen_model_candidate.py — Generate a per-schema definition catalogue.

For each definition in a JSON Schema file, records its description and every
JSON Pointer path at which it is referenced. The output is a candidate for
informing rsc/model.json — review it and curate rsc/model.json by hand.

Usage:
    python src/test/gen_model_candidate.py <schema-stem> <schema-file>

Examples:
    python src/test/gen_model_candidate.py conversations rsc/schema/conversations/v6.json
    python src/test/gen_model_candidate.py memories      rsc/schema/memories/memories.json

Output: JSON to stdout. Redirect to gen/model/<schema-stem>.json for review.
"""

import json, sys
from collections import defaultdict

SCHEMA_NAME = sys.argv[1].removesuffix('.json')

with open(sys.argv[2]) as f:
    schema = json.load(f)

candidates = defaultdict(lambda: {'description': None, 'occurrences': {f'{SCHEMA_NAME}.json': []}})

root_name = schema.get('title') or SCHEMA_NAME
candidates[root_name]['description'] = schema.get('description') or None
candidates[root_name]['occurrences'][f'{SCHEMA_NAME}.json'].append('#')

def walk(obj, path='#'):
    if isinstance(obj, dict):
        if '$ref' in obj:
            target = obj['$ref']
            if target.startswith('#/definitions/'):
                name = target[len('#/definitions/'):]
                candidates[name]['occurrences'][f'{SCHEMA_NAME}.json'].append(path)
                # Pick up description from the definition itself
                defn = schema.get('definitions', {}).get(name, {})
                d = defn.get('description')
                if isinstance(d, str):
                    candidates[name]['description'] = d
        for k, v in obj.items():
            walk(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f'{path}[{i}]')

walk(schema)

for name, entry in candidates.items():
    entry['occurrences'][f'{SCHEMA_NAME}.json'] = sorted(set(entry['occurrences'][f'{SCHEMA_NAME}.json']))

print(json.dumps(dict(candidates), indent=2))