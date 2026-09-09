#!/usr/bin/env python
"""structure.all_definitions_reachable - Every definition is reachable from root via
$ref, or is declared unreachable in the family's unreachable.csv (name, reason)
beside the version file; a declared name that is reachable, or that names no
definition, is a stale declaration and fails the same way."""
import csv
import json
import sys
from collections import deque
from pathlib import Path

schema_path = Path(sys.argv[1])
with open(schema_path) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

declaration = schema_path.parent / 'unreachable.csv'
declared = {}
if declaration.is_file():
    with open(declaration, newline='') as f:
        declared = {row['name']: row['reason'] for row in csv.DictReader(f)}

def find_refs(obj):
    refs = set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                refs.add(o['$ref'][len('#/definitions/'):])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return refs

def find_refs_ordered(obj):
    refs, seen = [], set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                r = o['$ref'][len('#/definitions/'):]
                if r not in seen:
                    seen.add(r)
                    refs.append(r)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return refs

if not defs:
    print('PASS structure.all_definitions_reachable (no definitions)')
    sys.exit(0)
root = next(iter(r for r in find_refs_ordered(schema) if r in defs), next(iter(defs)))
visited, queue = set(), deque([root])
while queue:
    node = queue.popleft()
    if node in visited:
        continue
    visited.add(node)
    for dep in find_refs(defs.get(node, {})):
        if dep in defs:
            queue.append(dep)

problems = []
unreachable = [k for k in defs if k not in visited and k not in declared]
if unreachable:
    problems.append(f'unreachable from {root} and not declared in {declaration.name}: {unreachable}')
stale = [k for k in declared if k in visited]
if stale:
    problems.append(f'declared unreachable in {declaration.name} but reachable from {root}: {stale}')
absent = [k for k in declared if k not in defs]
if absent:
    problems.append(f'declared unreachable in {declaration.name} but no definition: {absent}')
if problems:
    print('FAIL structure.all_definitions_reachable: ' + '; '.join(problems))
    sys.exit(1)
print(f'PASS structure.all_definitions_reachable ({len(declared)} declared unreachable)' if declared
      else 'PASS structure.all_definitions_reachable')
