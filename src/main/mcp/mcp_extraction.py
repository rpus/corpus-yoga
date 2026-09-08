#!/usr/bin/env python
"""
mcp_extraction.py - what the house factoring takes from upstream's schema.ts (#581):
the composition (which interface extends which) and the alias sites (where schema.ts
uses an exported type alias). Read at every sync from the committed
rsc/reference/mcp/<lineage>/schema.ts by the rules stated here; the tables the
factoring derives from it are written under tmp/cache/mcp/ as the readable face of
the derivation's inputs, and are never hand-written.

Rules:
- composition: `export interface X extends A, B {` contributes (X, A) and (X, B), in
  declaration order. `Omit<Base, "field">` contributes Base: the interface restates
  the omitted field itself, so composing over the whole base is what the snapshot
  bears - every row is verified there by the factoring before use.
- alias sites: `export type A = B;` naming one type is a copy site - the generator
  emitted A as a copy of B. An alias used as a property's type, or as a member of a
  union alias, is a use site. The factoring turns a site into an alias row only when
  the generator inlined the alias (its snapshot definition is referenced by nothing).

Parsing is by declaration shape - comments stripped, braces and angle brackets
matched - not by a TypeScript grammar; a declaration form this file does not read
(a generic interface, a mapped type) is reported by the factoring's verification
of every row against the snapshot, never silently misread.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

SELF = 'src/main/mcp/mcp_extraction.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], f'{_file} is not at its declared address {SELF}'

PRIMITIVES = {'string', 'number', 'boolean', 'null', 'unknown', 'never', 'any', 'object', 'void'}
_INTERFACE = re.compile(r'export interface (\w+)(?:\s+extends\s+([^{]+?))?\s*\{')
_ALIAS = re.compile(r'export type (\w+)\s*=\s*([^;]+);')
_OMIT = re.compile(r'^Omit<\s*(\w+)\s*,')
_PROPERTY = re.compile(r'^(\w+)\??\s*:\s*(.+)$', re.S)


@dataclass
class Interface:
    name: str
    bases: list[str]                       # as declared, Omit<Base, ...> read as Base
    properties: dict[str, str] = field(default_factory=dict)   # property -> declared type text


@dataclass
class Alias:
    name: str
    text: str                              # the right-hand side, whitespace collapsed
    members: list[str]                     # identifiers of a union rhs (a single-name rhs is one member)

    @property
    def single(self) -> str | None:
        """The one type this alias names, when its rhs is exactly one identifier."""
        return self.members[0] if len(self.members) == 1 and self.text == self.members[0] else None

    @property
    def union(self) -> bool:
        return '|' in self.text


def stripped(ts: str) -> str:
    """ts without comments; string literals kept whole (a comment marker inside one
    is text)."""
    out, i, n = [], 0, len(ts)
    while i < n:
        c = ts[i]
        if c in '"\'`':
            j = i + 1
            while j < n and ts[j] != c:
                j += 2 if ts[j] == '\\' else 1
            out.append(ts[i:j + 1])
            i = j + 1
        elif ts.startswith('/*', i):
            j = ts.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif ts.startswith('//', i):
            j = ts.find('\n', i)
            i = n if j < 0 else j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _split_top(text: str, sep: str) -> list[str]:
    """Split text on sep at bracket depth zero ((), [], {}, <>)."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c in '([{<':
            depth += 1
        elif c in ')]}>':
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _base(text: str) -> str:
    m = _OMIT.match(text)
    return m.group(1) if m else text.strip()


def _body(ts: str, open_brace: int) -> str:
    depth = 0
    for i in range(open_brace, len(ts)):
        if ts[i] == '{':
            depth += 1
        elif ts[i] == '}':
            depth -= 1
            if depth == 0:
                return ts[open_brace + 1:i]
    raise ValueError('unbalanced interface body')


def declarations(ts: str) -> tuple[list[Interface], list[Alias]]:
    """Every exported interface and type alias of schema.ts, in declaration order."""
    text = stripped(ts)
    interfaces: list[Interface] = []
    for m in _INTERFACE.finditer(text):
        bases = [_base(b) for b in _split_top(' '.join(m.group(2).split()), ',')] if m.group(2) else []
        iface = Interface(m.group(1), bases)
        for item in _split_top(_body(text, m.end() - 1), ';'):
            pm = _PROPERTY.match(item.strip())
            if pm:
                iface.properties[pm.group(1)] = ' '.join(pm.group(2).split())
        interfaces.append(iface)
    aliases: list[Alias] = []
    for m in _ALIAS.finditer(text):
        rhs = ' '.join(m.group(2).split()).lstrip('| ').strip()
        members = [p for p in _split_top(rhs, '|') if re.fullmatch(r'\w+', p) and p not in PRIMITIVES]
        aliases.append(Alias(m.group(1), rhs, members))
    return interfaces, aliases


def composition(interfaces: list[Interface]) -> dict[str, list[str]]:
    """{definition: [base, ...]} as schema.ts declares it, Omit read as its base."""
    return {i.name: list(i.bases) for i in interfaces if i.bases}


def property_sites(interfaces: list[Interface], alias: str) -> list[tuple[str, str]]:
    """(interface, pointer) for every property typed by the alias, or by an array of it."""
    out = []
    for i in interfaces:
        for prop, typ in i.properties.items():
            if typ == alias:
                out.append((i.name, f'properties/{prop}'))
            elif typ == f'{alias}[]':
                out.append((i.name, f'properties/{prop}/items'))
    return out


def union_sites(aliases: list[Alias], alias: str) -> list[str]:
    """The union aliases that list the alias as a member."""
    return [a.name for a in aliases if a.union and alias in a.members]
