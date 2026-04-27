#!/usr/bin/env python
"""structure.bfs_order — Definitions are in breadth-first referential encounter order."""
import json, sys
from collections import deque

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

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

root = next(iter(defs))  # first definition is the BFS root
order, visited, queue = [], set(), deque([root])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node); order.append(node)
    for dep in find_refs_ordered(defs.get(node, {})):
        if dep not in visited and dep in defs: queue.append(dep)
for k in defs:
    if k not in visited: order.append(k)

fails = [(i+1, c, b) for i, (c, b) in enumerate(zip(list(defs.keys()), order)) if c != b]
if fails:
    print(f'FAIL structure.bfs_order: {len(fails)} position(s) wrong')
    for pos, cur, bfs in fails[:3]:
        print(f'  pos {pos}: current={cur}, expected={bfs}')
    if len(fails) > 3: print(f'  ... and {len(fails)-3} more')
    sys.exit(1)
print('PASS structure.bfs_order')
