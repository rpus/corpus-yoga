#!/usr/bin/env python
"""structure.all_definitions_reachable — Every definition is reachable from root via $ref."""
import json
import sys
from collections import deque

# Definitions intentionally unreachable via $ref — documented stubs for API
# tool types not yet observed in any export.
# Each entry is annotated with the schema version from which it applies.
KNOWN_UNREACHABLE = {
    'ToolInputComputerUse',   # v1+: API tool, not yet surfaced in exports
    'ToolInputTextEditor',    # v1+: API tool, not yet surfaced in exports
    'ToolInputCodeExecution', # v1+: API tool, not yet surfaced in exports
}

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

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

unreachable = [k for k in defs if k not in visited and k not in KNOWN_UNREACHABLE]
if unreachable:
    print(f'FAIL structure.all_definitions_reachable: {unreachable}')
    sys.exit(1)
print('PASS structure.all_definitions_reachable')
