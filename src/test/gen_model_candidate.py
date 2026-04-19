'''
for f in conversations.json; do python "../Yoga/src/gen_model_candidate.py" "$f" "../Yoga/rsc/schema/${f%.json}.json" > "../Yoga/gen/model/${f%.json}.json"; done
'''

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