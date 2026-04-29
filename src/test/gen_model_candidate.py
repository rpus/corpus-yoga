"""
gen_model_candidate.py — Generate a per-schema definition catalogue.

For each definition in a JSON Schema file, records its description and every
JSON Pointer path at which it is referenced. The output is a candidate for
informing rsc/model.json — review it and curate rsc/model.json by hand.

Usage:
    python src/test/gen_model_candidate.py <schema-type> <schema-file>

Examples:
    python src/test/gen_model_candidate.py conversations rsc/schema/conversations/v6.json
    python src/test/gen_model_candidate.py memories      rsc/schema/memories/v1.json

Output: JSON to stdout. Redirect to gen/model/<schema-type>/<version>.json for review.
Normally invoked via src/test/gen_model.sh which handles all schemas automatically.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def generate(schema_name: str, schema_path: str | Path) -> str:
    with open(schema_path) as f:
        schema = json.load(f)

    candidates: dict[str, Any] = defaultdict(lambda: {'description': None, 'occurrences': {f'{schema_name}.json': []}})

    root_name = schema.get('title') or schema_name
    candidates[root_name]['description'] = schema.get('description') or None
    candidates[root_name]['occurrences'][f'{schema_name}.json'].append('#')

    def walk(obj, path='#'):
        if isinstance(obj, dict):
            if '$ref' in obj:
                target = obj['$ref']
                if target.startswith('#/definitions/'):
                    name = target[len('#/definitions/'):]
                    candidates[name]['occurrences'][f'{schema_name}.json'].append(path)
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
        entry['occurrences'][f'{schema_name}.json'] = sorted(set(entry['occurrences'][f'{schema_name}.json']))

    return json.dumps(dict(candidates), indent=2)


if __name__ == '__main__':
    print(generate(sys.argv[1].removesuffix('.json'), sys.argv[2]))
