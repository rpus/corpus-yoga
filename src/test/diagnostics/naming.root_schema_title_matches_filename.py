#!/usr/bin/env python
"""naming.root_schema_title_matches_filename — Root schema title matches filename stem."""
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
stem = path.stem  # e.g. 'conversations' from 'conversations.json'

with open(path) as f:
    schema = json.load(f)

title = schema.get('title')
if title != stem:
    print(f'FAIL naming.root_schema_title_matches_filename: title={title!r}, expected={stem!r}')
    sys.exit(1)
print('PASS naming.root_schema_title_matches_filename')
