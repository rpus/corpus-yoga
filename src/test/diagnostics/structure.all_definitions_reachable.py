#!/usr/bin/env python
"""structure.all_definitions_reachable — Every definition is reachable from root via $ref."""
import json, sys
from collections import deque

KNOWN_UNREACHABLE = {
    'ToolInputComputerUse',   # documented stub, no observed instances
    'ToolInputTextEditor',    # documented stub, no observed instances
    'ToolInputCodeExecution', # documented stub, no observed instances
}

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

def find_refs(obj):
    refs = set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o: refs.add(o['$ref'][len('#/definitions/'):])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj); return refs

visited, queue = set(), deque(['Conversation'])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node)
    for dep in find_refs(defs.get(node, {})):
        if dep in defs: queue.append(dep)

unreachable = [k for k in defs if k not in visited and k not in KNOWN_UNREACHABLE]
if unreachable:
    print(f'FAIL structure.all_definitions_reachable: {unreachable}')
    sys.exit(1)
print('PASS structure.all_definitions_reachable')
