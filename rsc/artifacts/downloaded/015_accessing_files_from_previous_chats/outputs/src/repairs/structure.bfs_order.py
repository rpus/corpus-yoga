#!/usr/bin/env python3
"""Repair: reapply BFS ordering to definitions.
Usage: python structure.bfs_order.py schema.json"""
import json, sys
from collections import deque

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
defs = schema['definitions']

def find_refs_ordered(obj):
    refs, seen = [], set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                r = o['$ref'][len('#/definitions/'):]
                if r not in seen: seen.add(r); refs.append(r)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj); return refs

order, visited, queue = [], set(), deque(['Conversation'])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node); order.append(node)
    for dep in find_refs_ordered(defs.get(node, {})):
        if dep not in visited and dep in defs: queue.append(dep)
for k in defs:
    if k not in visited: order.append(k)

schema['definitions'] = {k: defs[k] for k in order}
defs_out = schema.pop('definitions')
schema['definitions'] = defs_out
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Reordered {len(order)} definitions')