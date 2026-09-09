#!/usr/bin/env python
"""
mcp_extraction.py - what the house factoring takes from upstream's schema.ts (#581,
#597): the composition (which interface extends which), the alias sites (where
schema.ts uses an exported type alias), the category tags (#595) and the exported
constants. Read at every sync from the committed rsc/reference/mcp/<lineage>/schema.ts
through the parser generated from the house TypeScript grammar
(rsc/rpus/grammar/TypeScript, generated under src/gen/grammar/TypeScript by
`corpus-yoga grammar sync`); the tables the factoring derives from it are written
under tmp/cache/mcp/ as the readable face of the derivation's inputs, and are never
hand-written.

Rules:
- composition: `export interface X extends A, B {` contributes (X, A) and (X, B), in
  declaration order. `Omit<Base, "field">` contributes Base: the interface restates
  the omitted field itself, so composing over the whole base is what the snapshot
  bears - every row is verified there by the factoring before use.
- alias sites: `export type A = B;` naming one type is a copy site - the generator
  emitted A as a copy of B. An alias used as a property's type, or as a member of a
  union alias, is a use site. The factoring turns a site into an alias row only when
  the generator inlined the alias (its snapshot definition is referenced by nothing).
- category: the `@category` tag of the JSDoc block before a declaration - read from
  the lexer's COMMENT channel by position, the block nearest the declaration.

The grammar is the reader: a declaration or type expression the grammar does not
accept is a parse error naming the line, raised here, never a silent miss - the
file is read whole or refused. A type expression is read as a tree (TypeExpr),
never carried as text. The parser is generated on each machine (src/gen/grammar,
gitignored); absent, every reading refuses with the remedy.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast
import importlib

SELF = 'src/main/mcp/mcp_extraction.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
GRAMMAR_PARSER = REPO / 'src' / 'gen' / 'grammar' / 'TypeScript'   # generated, gitignored - corpus-yoga grammar sync
sys.path.insert(0, str(GRAMMAR_PARSER))
from antlr4 import CommonTokenStream, InputStream  # noqa: E402
from antlr4.error.ErrorListener import ErrorListener  # noqa: E402
PARSER_REMEDY = (f'{GRAMMAR_PARSER.relative_to(REPO)} is absent - corpus-yoga grammar sync generates it from '
                 'rsc/rpus/grammar/TypeScript (corpus-yoga prerequisites sync --apply does so with the rest)')

PRIMITIVES = {'string', 'number', 'boolean', 'null', 'unknown', 'any'}


def _all(contexts: Any) -> list:
    """A generated accessor's list form: ANTLR types `x()` as one context, a list or None."""
    return list(cast(list, contexts) or [])


@dataclass
class TypeExpr:
    """A type expression as the grammar reads it: reference (name, args), array
    (items), union or intersection (members), object (properties), primitive or
    literal (name), typeof (name)."""
    kind: str
    name: str = ''
    args: list['TypeExpr'] = field(default_factory=list)
    items: 'TypeExpr | None' = None
    members: list['TypeExpr'] = field(default_factory=list)
    properties: dict[str, 'TypeExpr'] = field(default_factory=dict)

    @property
    def reference(self) -> str | None:
        """The one name this expression is, when it is a bare reference."""
        return self.name if self.kind == 'reference' and not self.args else None


@dataclass
class Interface:
    name: str
    bases: list[str]                       # as declared, Omit<Base, ...> read as Base
    properties: dict[str, TypeExpr] = field(default_factory=dict)


@dataclass
class Alias:
    name: str
    expr: TypeExpr

    @property
    def text(self) -> str:
        return _text(self.expr)

    @property
    def members(self) -> list[str]:
        """Identifiers of a union rhs (a single-name rhs is one member)."""
        parts = self.expr.members if self.expr.kind == 'union' else [self.expr]
        return [p.reference for p in parts if p.reference]

    @property
    def single(self) -> str | None:
        """The one type this alias names, when its rhs is exactly one identifier."""
        return self.expr.reference

    @property
    def union(self) -> bool:
        return self.expr.kind == 'union'


@dataclass
class Constant:
    name: str
    value: str                             # the literal as written


class ParseRefused(ValueError):
    pass


class _Refuse(ErrorListener):
    def __init__(self, what: str):
        self.what = what

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise ParseRefused(f'{self.what} {line}:{column}: {msg} - the house TypeScript grammar does not read it')


def _text(expr: TypeExpr) -> str:
    if expr.kind in ('primitive', 'literal', 'reference') and not expr.args:
        return expr.name
    if expr.kind == 'reference':
        return f'{expr.name}<{", ".join(_text(a) for a in expr.args)}>'
    if expr.kind == 'array':
        return f'{_text(expr.items)}[]' if expr.items else '[]'
    if expr.kind == 'union':
        return ' | '.join(_text(m) for m in expr.members)
    if expr.kind == 'intersection':
        return ' & '.join(_text(m) for m in expr.members)
    if expr.kind == 'typeof':
        return f'typeof {expr.name}'
    return '{ ' + '; '.join(f'{k}: {_text(v)}' for k, v in expr.properties.items()) + ' }'


def _expr(ctx) -> TypeExpr:
    """A typeExpression context read into a TypeExpr."""
    union = ctx.unionType()
    members = [_intersection(i) for i in _all(union.intersectionType())]
    return members[0] if len(members) == 1 else TypeExpr('union', members=members)


def _intersection(ctx) -> TypeExpr:
    members = [_array(a) for a in _all(ctx.arrayOrPrimaryType())]
    return members[0] if len(members) == 1 else TypeExpr('intersection', members=members)


def _array(ctx) -> TypeExpr:
    expr = _primary(ctx.primaryType())
    for _ in _all(ctx.OpenBracket()):
        expr = TypeExpr('array', items=expr)
    return expr


def _primary(ctx) -> TypeExpr:
    if ctx.primitiveType():
        return TypeExpr('primitive', name=ctx.primitiveType().getText())
    if ctx.StringLiteral():
        return TypeExpr('literal', name=ctx.StringLiteral().getText())
    if ctx.typeQuery():
        return TypeExpr('typeof', name=ctx.typeQuery().Identifier().getText())
    if ctx.typeReference():
        ref = ctx.typeReference()
        args = [_expr(a.typeExpression()) for a in (_all(ref.typeArgumentList().typeArgument()) if ref.typeArgumentList() else [])]
        return TypeExpr('reference', name=ref.Identifier().getText(), args=args)
    if ctx.objectType():
        return TypeExpr('object', properties=_properties(ctx.objectType()))
    return _expr(ctx.typeExpression())


def _properties(ctx) -> dict[str, TypeExpr]:
    """The property signatures of an object type, by name (a quoted name unquoted);
    index signatures are not properties."""
    out = {}
    for member in _all(ctx.memberSignature()):
        sig = member.propertySignature()
        if sig is None:
            continue
        name = sig.propertyName().getText()
        if name.startswith('"'):
            name = name[1:-1]
        out[name] = _expr(sig.typeExpression())
    return out


class ParserAbsent(AssertionError):
    """The generated parser is not on this machine - a refusal of the derivation, with
    the remedy."""


def _parser():
    """The generated lexer and parser classes, imported when first needed so that a
    machine without them fails by name, not at import of this module."""
    try:
        lexer = importlib.import_module('TypeScriptLexer').TypeScriptLexer
        parser = importlib.import_module('TypeScriptParser').TypeScriptParser
    except ModuleNotFoundError as missing:
        raise ParserAbsent(PARSER_REMEDY) from missing
    return lexer, parser


def parsed(ts: str, what: str = 'schema.ts'):
    """The parse tree of a schema.ts text and its token stream; a text the grammar
    refuses raises ParseRefused naming the line; an absent parser raises ParserAbsent."""
    TypeScriptLexer, TypeScriptParser = _parser()
    lexer = TypeScriptLexer(InputStream(ts))
    stream = CommonTokenStream(lexer)
    parser = TypeScriptParser(stream)
    for recogniser in (lexer, parser):
        recogniser.removeErrorListeners()
        recogniser.addErrorListener(_Refuse(what))
    return parser.typeScriptFile(), stream


def declarations(ts: str) -> tuple[list[Interface], list[Alias]]:
    """Every exported interface and type alias of schema.ts, in declaration order."""
    tree, _ = parsed(ts)
    interfaces: list[Interface] = []
    aliases: list[Alias] = []
    for decl in _all(tree.declaration()):
        if decl.interfaceDeclaration():
            d = decl.interfaceDeclaration()
            bases = []
            if d.extendsClause():
                for ref in _all(d.extendsClause().typeReference()):
                    name = ref.Identifier().getText()
                    if name == 'Omit' and ref.typeArgumentList():
                        base = _expr(_all(ref.typeArgumentList().typeArgument())[0].typeExpression()).reference
                        assert base, f'{d.Identifier().getText()}: Omit of no named base'
                        name = base
                    bases.append(name)
            interfaces.append(Interface(d.Identifier().getText(), bases, _properties(d.objectType())))
        elif decl.typeAliasDeclaration():
            d = decl.typeAliasDeclaration()
            aliases.append(Alias(d.Identifier().getText(), _expr(d.typeExpression())))
    return interfaces, aliases


def constants(ts: str) -> list[Constant]:
    """Every exported constant of schema.ts with its literal, in declaration order -
    what upstream's generator does not emit."""
    tree, _ = parsed(ts)
    return [Constant(d.constDeclaration().Identifier().getText(), d.constDeclaration().constValue().getText())
            for d in _all(tree.declaration()) if d.constDeclaration()]


def categories(ts: str) -> dict[str, str | None]:
    """{declared name: its @category tag, None where the JSDoc carries none} for every
    exported interface and type alias - the JSDoc being the nearest COMMENT-channel
    block before the declaration, a backticked method tag read as its bare method."""
    tree, stream = parsed(ts)
    out: dict[str, str | None] = {}
    for decl in _all(tree.declaration()):
        d = decl.interfaceDeclaration() or decl.typeAliasDeclaration()
        if d is None:
            continue
        comments = stream.getHiddenTokensToLeft(decl.start.tokenIndex, _parser()[0].COMMENT) or []
        doc = comments[-1].text if comments else ''
        tag = None
        if doc.startswith('/**'):
            for line in doc.splitlines():
                body = line.strip().lstrip('*').strip()
                if body.startswith('@category '):
                    tag = body[len('@category '):].strip().strip('`')
        out[d.Identifier().getText()] = tag
    return dict(sorted(out.items()))


def composition(interfaces: list[Interface]) -> dict[str, list[str]]:
    """{definition: [base, ...]} as schema.ts declares it, Omit read as its base."""
    return {i.name: list(i.bases) for i in interfaces if i.bases}


def property_sites(interfaces: list[Interface], alias: str) -> list[tuple[str, str]]:
    """(interface, pointer) for every property typed by the alias, or by an array of it."""
    out = []
    for i in interfaces:
        for prop, typ in i.properties.items():
            if typ.reference == alias:
                out.append((i.name, f'properties/{prop}'))
            elif typ.kind == 'array' and typ.items is not None and typ.items.reference == alias:
                out.append((i.name, f'properties/{prop}/items'))
    return out


def union_sites(aliases: list[Alias], alias: str) -> list[str]:
    """The union aliases that list the alias as a member."""
    return [a.name for a in aliases if a.union and alias in a.members]
