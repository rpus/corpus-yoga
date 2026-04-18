"""
expand_schema.py  —  inline all $refs in a JSON Schema, producing a fully
expanded schema with no $ref indirection. Useful for validation debugging:
error messages from the expanded schema are specific rather than opaque.

Cycles are broken by leaving the $ref in place when a definition is already
being expanded (detected via an `expanding` set). This is safe because cyclic
schemas cannot be fully expanded anyway, and the cyclic paths are rarely where
validation failures occur.

Usage:
    python expand_schema.py conversations.schema.json > conversations.schema.expanded.json
    python validate.py conversations.json conversations.schema.expanded.json
"""
import sys, json, copy

def load(path):
    with open(path) as f:
        return json.load(f)

def ref_name(ref):
    return ref.lstrip('#/definitions/')

def expand(node, defs, expanding=None):
    """
    Recursively expand all $refs in `node`, using `defs` as the definition
    store. `expanding` is the set of definition names currently on the call
    stack — used to detect and break cycles.
    """
    if expanding is None:
        expanding = set()

    if isinstance(node, dict):
        if '$ref' in node and len(node) == 1:
            # pure $ref — replace with expanded definition
            name = ref_name(node['$ref'])
            if name in expanding:
                # cycle detected — leave as $ref to break the loop
                return {'$ref': node['$ref']}
            defn = defs.get(name)
            if defn is None:
                return node  # unknown ref — leave as-is
            return expand(copy.deepcopy(defn), defs, expanding | {name})

        if '$ref' in node:
            # $ref with siblings (e.g. description alongside $ref)
            # expand the ref and merge siblings in
            name = ref_name(node['$ref'])
            siblings = {k: v for k, v in node.items() if k != '$ref'}
            if name in expanding:
                result = dict(siblings)
                result['$ref'] = node['$ref']
                return result
            defn = defs.get(name)
            if defn is None:
                return {k: expand(v, defs, expanding) for k, v in node.items()}
            expanded = expand(copy.deepcopy(defn), defs, expanding | {name})
            if isinstance(expanded, dict):
                result = dict(expanded)
                result.update(siblings)  # siblings override (e.g. description)
                return result
            return expanded

        # regular object — recurse into all values
        return {k: expand(v, defs, expanding) for k, v in node.items()}

    if isinstance(node, list):
        return [expand(item, defs, expanding) for item in node]

    return node

if len(sys.argv) < 2:
    print(f'Usage: python {sys.argv[0]} <schema.json>', file=sys.stderr)
    sys.exit(1)

schema = load(sys.argv[1])
defs = schema.get('definitions', {})

# expand the root schema (excluding definitions — they're only needed as a
# source for expansion, and including them would double the output size)
expanded = expand({k: v for k, v in schema.items() if k != 'definitions'}, defs)

# optionally keep definitions for reference (commented out by default)
# expanded['definitions'] = {name: expand(defn, defs, {name})
#                             for name, defn in defs.items()}

print(json.dumps(expanded, indent=2))
