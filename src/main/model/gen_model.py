#!/usr/bin/env python
"""
gen_model.py — Generate per-schema definition catalogues as candidates for rsc/schema/model.json.
Output: gen/model/{schema}/v{N}.json for each versioned schema (flat, not mirroring rsc/schema/{pipeline}/{schema}/).
rsc/schema/model.json is hand-curated from these.

Usage:
    ./yoga model
"""

import re
from pathlib import Path

from gen_model_candidate import generate

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[2]
SCHEMA_DIR = REPO_ROOT / 'rsc' / 'schema'
OUT_DIR    = REPO_ROOT / 'gen' / 'model'


def _sorted_versions(schema_dir: Path) -> list[Path]:
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )


def main():
    for pipeline_dir in sorted(SCHEMA_DIR.iterdir()):
        if not pipeline_dir.is_dir() or pipeline_dir.name.startswith('_'):
            continue
        for schema_dir in sorted(pipeline_dir.iterdir()):
            if not schema_dir.is_dir():
                continue
            versions = _sorted_versions(schema_dir)
            if not versions:
                continue
            name = schema_dir.name
            out_dir = OUT_DIR / name
            out_dir.mkdir(parents=True, exist_ok=True)
            for schema in versions:
                (out_dir / schema.name).write_text(generate(name, schema))
                print(f'  ✓ gen/model/{name}/{schema.name}')

    print('Review gen/model/ and update rsc/schema/model.json as needed.')


if __name__ == '__main__':
    main()
