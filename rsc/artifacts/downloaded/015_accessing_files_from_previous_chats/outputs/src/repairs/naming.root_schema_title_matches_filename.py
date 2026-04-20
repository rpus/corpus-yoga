#!/usr/bin/env python3
"""Repair: set root schema title to match filename stem.
Usage: python naming.root_schema_title_matches_filename.py schema.json"""
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
with open(path) as f:
    schema = json.load(f)
schema['title'] = path.stem
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Set title to {path.stem!r}')