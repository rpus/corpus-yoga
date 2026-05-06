#!/usr/bin/env python
"""Repair structure.bfs_order — Reorder definitions into breadth-first referential encounter order.

Usage: python src/test/repairs/structure.bfs_order.py <schema>

Traverses $refs starting from the root entry point (first definition, assumed to be
the primary type — e.g. Conversation for conversations.json). Definitions unreachable
via $ref are appended at the end in their original relative order.
Writes back to the same file in place.
"""
import json
import sys
from collections import deque
from pathlib import Path

def find_refs_ordered(obj):
    """Return $ref targets in first-encounter order, depth-first within a node."""
    refs, seen = [], set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                r = o['$ref']
                if r.startswith('#/definitions/'):
                    name = r[len('#/definitions/'):]
                    if name not in seen:
                        seen.add(name)
                        refs.append(name)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return refs

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

defs = schema.get('definitions', {})
if not defs:
    print('No definitions found.')
    sys.exit(0)

root = next(iter(r for r in find_refs_ordered(schema) if r in defs), next(iter(defs)))
order, visited, queue = [], set(), deque([root])
while queue:
    node = queue.popleft()
    if node in visited:
        continue
    visited.add(node)
    order.append(node)
    for dep in find_refs_ordered(defs.get(node, {})):
        if dep in defs and dep not in visited:
            queue.append(dep)

# Append unreachable definitions in original relative order
for k in defs:
    if k not in visited:
        order.append(k)

original = list(defs.keys())
if order == original:
    print('Already in BFS order — nothing to do.')
    sys.exit(0)

# Report first divergence
for i, (cur, bfs) in enumerate(zip(original, order)):
    if cur != bfs:
        print(f'First divergence at position {i+1}: current={cur!r}, expected={bfs!r}')
        break

schema['definitions'] = {k: defs[k] for k in order}

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)

print(f'Reordered {len(order)} definitions into BFS order in {schema_path}')
