"""
gen_model.py — Generate per-schema definition catalogues as candidates for rsc/model.json.
Output goes to gen/model/ for review; rsc/model.json is hand-curated from these.

Usage:
    python src/test/gen_model.py
"""

import re
from pathlib import Path

from gen_model_candidate import generate

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[1]
SCHEMA_DIR = REPO_ROOT / 'rsc' / 'schema'
OUT_DIR    = REPO_ROOT / 'gen' / 'model'


def latest_version(schema_dir: Path) -> Path:
    versions = sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )
    if not versions:
        raise FileNotFoundError(f'No v*.json found in {schema_dir}')
    return versions[-1]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, schema_dir in [
        ('conversations', SCHEMA_DIR / 'conversations'),
        ('sessions',      SCHEMA_DIR / 'sessions'),
    ]:
        schema = latest_version(schema_dir)
        (OUT_DIR / f'{name}.json').write_text(generate(name, schema))
        print(f'  ✓ gen/model/{name}.json  (from {schema.name})')

    for name in ('memories', 'projects', 'users'):
        schema = SCHEMA_DIR / name / f'{name}.json'
        (OUT_DIR / f'{name}.json').write_text(generate(name, schema))
        print(f'  ✓ gen/model/{name}.json')

    print('Review gen/model/ and update rsc/model.json as needed.')


if __name__ == '__main__':
    main()
