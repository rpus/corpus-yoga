'''
python ../Yoga/src/gen_model_candidate.py conversations > ../Yoga/gen/model/conversations.json
'''

import json, re, sys
from collections import defaultdict

SCHEMA_NAME = sys.argv[1]  # e.g. "conversations"

with open(f'../Yoga/rsc/schema/{SCHEMA_NAME}.json') as f:
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