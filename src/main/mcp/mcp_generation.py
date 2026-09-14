#!/usr/bin/env python
"""
mcp_generation.py - the mcp schema generated from schema.ts alone (#598): every
exported interface, alias and constant read through the house TypeScript grammar
(mcp_extraction) and written as a draft-04 shape in the house dialect, the shape
upstream's generator would flatten it to - so the factoring composes these over the
declared bases as before, and upstream's schema.json stands as the witness the
result must flatten to (mcp_factoring.disagreements), never as a source.

The reading, one rule per TypeScript form, each held by the witness:
- a primitive: string, boolean, null as their JSON types; number as integer (the
  generator's default), number where the JSDoc says `@TJS-type number`; unknown and
  any as the empty schema.
- a string literal, and `typeof` a constant: the one-element enum of the value,
  typed by it (a string, or an integer).
- a reference: `Array<T>` an array of T, `Record<string, T>` an object whose
  additional properties are T, any other name a $ref to the definition - the
  aliases upstream inlines are references here by construction.
- an array `T[]`: an array of T.
- an object type: an object with its property signatures (optional members absent
  from `required`) and its index signature as additionalProperties.
- a union: string literals fold into one enum; a literal beside the primitive that
  contains it is absorbed by it; the primitives fold into one `type` list; every
  other member stands in an `anyOf` after them, in declaration order.
- an intersection: an allOf of its members.
- an interface: an object of its own properties over the properties its bases
  supply (a base's property the interface redeclares is the interface's) - the
  flat shape the factoring then composes over the bases again.
- JSDoc: the block before a declaration or a member is its description, rendered as
  upstream's generator renders it (tag blocks dropped, `{@link A | b}` as `{@link
  Ab}`); `@format`, `@minimum`, `@maximum` and `@maxItems` become keywords. A member
  without a JSDoc takes its base's description with the base's property.
"""

import re
import sys
from pathlib import Path

SELF = 'src/main/mcp/mcp_generation.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import mcp_extraction as extraction  # noqa: E402  (sibling module)
from mcp_extraction import TypeExpr  # noqa: E402

PRIMITIVE_TYPE = {'string': 'string', 'boolean': 'boolean', 'null': 'null', 'number': 'integer'}
TAG_BLOCKS = ('@example', '@includeCode', '@category', '@TJS-type', '@minimum', '@maximum', '@maxItems',
              '@format', '@internal', '@see', '@deprecated', '@typescript', '{@includeCode')
KEYWORD_TAGS = {'@format': ('format', str), '@minimum': ('minimum', int), '@maximum': ('maximum', int),
                '@maxItems': ('maxItems', int)}


def jsdoc_lines(doc: str) -> list[str]:
    """The lines of a JSDoc block without its frame."""
    body = doc[3:-2]
    out = []
    for raw in body.split('\n'):
        line = raw.strip()
        if line.startswith('*'):
            line = line[1:]
        if line.startswith(' '):
            line = line[1:]
        out.append(line.rstrip())
    return out


def description(doc: str) -> str | None:
    """The description upstream's generator renders from a JSDoc block: a tag line
    and the non-blank lines that continue it are dropped, `{@link A | b}` reads
    `{@link Ab}`, runs of blank lines collapse."""
    if not doc.startswith('/**'):
        return None
    kept, dropping = [], False
    for line in jsdoc_lines(doc):
        if any(line.lstrip().startswith(t) for t in TAG_BLOCKS):
            dropping = True
            continue
        if dropping and line.strip():
            continue
        dropping = False
        kept.append(line)
    text = '\n'.join(kept).strip('\n')
    text = re.sub(r'\{@link ([^}|]*?)\s*\|\s*([^}]*)\}', r'{@link \1\2}', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text or None


def keywords(doc: str) -> dict:
    """The schema keywords a JSDoc block declares by tag, and whether it retypes a
    number (`@TJS-type number`)."""
    out: dict = {}
    if not doc.startswith('/**'):
        return out
    for line in jsdoc_lines(doc):
        line = line.strip()
        for tag, (keyword, kind) in KEYWORD_TAGS.items():
            if line.startswith(tag + ' '):
                out[keyword] = kind(line[len(tag):].strip())
        if line.startswith('@TJS-type '):
            out['type'] = line[len('@TJS-type '):].strip()
    return out


def _literal(text: str) -> dict:
    """The one-element enum of a TypeScript literal, typed by it."""
    if text.startswith('"'):
        return {'type': 'string', 'enum': [text[1:-1]]}
    return {'type': 'integer', 'enum': [int(text)]}


class Generation:
    """One schema.ts read whole: its declarations, constants and comments, and the
    flat shape of every exported interface and alias."""

    def __init__(self, ts: str):
        self.tree, self.stream = extraction.parsed(ts)
        self.comment_channel = extraction._parser()[0].COMMENT
        self.interfaces, self.aliases = extraction.declarations(ts)
        self.by_name = {i.name: i for i in self.interfaces}
        self.constants = {c.name: c.value for c in extraction.constants(ts)}
        self.docs: dict[str, str] = {}                 # declaration -> JSDoc
        for decl in extraction._all(self.tree.declaration()):
            d = decl.interfaceDeclaration() or decl.typeAliasDeclaration()
            if d is not None:
                self.docs[d.Identifier().getText()] = extraction.jsdoc_before(decl, decl.start.tokenIndex)

    # ── type expressions ──
    def schema(self, expr: TypeExpr, doc: str = '') -> dict:
        """The draft-04 schema of a type expression, in the house dialect; `doc` is
        the JSDoc of the member it types, for its keywords."""
        tags = keywords(doc)
        out = self._schema(expr)
        if tags.get('type') == 'number' and out.get('type') == 'integer':
            out['type'] = 'number'
        for k, v in tags.items():
            if k != 'type':
                out[k] = v
        return out

    def _schema(self, expr: TypeExpr) -> dict:
        kind = expr.kind
        if kind == 'primitive':
            return {'type': PRIMITIVE_TYPE[expr.name]} if expr.name in PRIMITIVE_TYPE else {}
        if kind == 'literal':
            return _literal(expr.name)
        if kind == 'typeof':
            assert expr.name in self.constants, f'typeof {expr.name}: no such constant'
            return _literal(self.constants[expr.name])
        if kind == 'array':
            assert expr.items is not None
            return {'type': 'array', 'items': self._schema(expr.items)}
        if kind == 'reference':
            if expr.name == 'Array' and expr.args:
                return {'type': 'array', 'items': self._schema(expr.args[0])}
            if expr.name == 'Record' and len(expr.args) == 2:
                return {'type': 'object', 'additionalProperties': self._schema(expr.args[1])}
            assert not expr.args, f'{expr.name}: a generic this generation does not read'
            return {'$ref': f'#/definitions/{expr.name}'}
        if kind == 'object':
            return self._object(expr)
        if kind == 'intersection':
            return {'allOf': [self._schema(m) for m in expr.members]}
        if kind == 'union':
            return self._union(expr.members)
        raise AssertionError(f'a type expression this generation does not read: {kind}')

    def _object(self, expr: TypeExpr) -> dict:
        """An object type's schema: its members' schemas by name, each with its
        JSDoc's description and keywords, the non-optional ones required, the index
        signature as additionalProperties."""
        out: dict = {'type': 'object'}
        props, required = {}, []
        for name, (member, optional) in expr.properties.items():
            doc = expr.docs.get(name, '')
            prop = self.schema(member, doc)
            text = description(doc)
            if text:
                prop['description'] = text
            props[name] = prop
            if not optional:
                required.append(name)
        if props:
            out['properties'] = props
        if required:
            out['required'] = required
        if expr.index is not None:
            out['additionalProperties'] = self._schema(expr.index)
        return out

    def _union(self, members: list[TypeExpr]) -> dict:
        literals, primitives, others = [], [], []
        for m in members:
            if m.kind == 'literal' or m.kind == 'typeof':
                literals.append(_literal(m.name if m.kind == 'literal' else self.constants[m.name]))
            elif m.kind == 'primitive':
                primitives.append(self._schema(m))
            else:
                others.append(self._schema(m))
        types = [p['type'] for p in primitives if 'type' in p]
        literals = [l for l in literals if l['type'] not in types]      # absorbed by the wider primitive
        folded: list[dict] = []
        if literals:
            kinds = sorted({l['type'] for l in literals})
            for t in kinds:
                folded.append({'type': t, 'enum': sorted((v for l in literals if l['type'] == t for v in l['enum']), key=str)})
        if types:
            folded.append({'type': types[0] if len(types) == 1 else types})
        if not others and len(folded) == 1:
            return folded[0]
        return {'anyOf': others + folded}

    # ── declarations ──
    def flat(self, name: str) -> dict:
        """The flat shape of an exported interface or alias: an interface as its own
        properties over its bases' (the flattening upstream performs), an alias as
        its expression's schema; with its description."""
        doc = self.docs.get(name, '')
        if name in self.by_name:
            iface = self.by_name[name]
            body = self._object(iface.body)
            merged_props: dict = {}
            merged_required: list = []
            for base in iface.bases:
                base_flat = self.flat(base)
                for p, s in base_flat.get('properties', {}).items():
                    merged_props[p] = s
                for r in base_flat.get('required', []):
                    if r not in merged_required:
                        merged_required.append(r)
                if 'additionalProperties' in base_flat and 'additionalProperties' not in body:
                    body['additionalProperties'] = base_flat['additionalProperties']
            for p, s in body.get('properties', {}).items():
                if 'description' not in s and p in merged_props and 'description' in merged_props[p]:
                    s = {**s, 'description': merged_props[p]['description']}
                merged_props[p] = s
            for r in body.get('required', []):
                if r not in merged_required:
                    merged_required.append(r)
            out: dict = {'type': 'object'}
            if merged_props:
                out['properties'] = merged_props
            if merged_required:
                out['required'] = merged_required
            if 'additionalProperties' in body:
                out['additionalProperties'] = body['additionalProperties']
        else:
            alias = next(a for a in self.aliases if a.name == name)
            out = self.schema(alias.expr, doc)
        text = description(doc)
        if text:
            out['description'] = text
        return out

    def shapes(self) -> dict[str, dict]:
        """{name: flat shape} for every exported interface and alias, in declaration order."""
        names = [i.name for i in self.interfaces] + [a.name for a in self.aliases]
        order = []
        for decl in extraction._all(self.tree.declaration()):
            d = decl.interfaceDeclaration() or decl.typeAliasDeclaration()
            if d is not None:
                order.append(d.Identifier().getText())
        return {n: self.flat(n) for n in order if n in names}
