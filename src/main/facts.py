"""
facts.py - a verb's facts as nested indented lines, YAML, from one printer (#740).

A status holds its facts as data - mappings of counts, lists of units, a verdict - and
prints them here: one fact per line, a fact that qualifies another indented beneath it,
a heading over the items it covers. The lines are YAML, so the same artifact is read by a
human by its shape and loaded by a machine as data; no width is enforced, since a line
that is one fact is as long as its fact. The emitter covers what a status holds -
mappings, lists, strings, numbers, booleans and None - and quotes a string wherever YAML
would otherwise read it as something else.

A status's facts are a named shape (#759): a dataclass whose fields are the facts it
holds, so that a reader takes them as fields and the type check holds the keys. A field
prints under its name's words, or under the key `named` gives it; a field that is None is
not printed; a shape whose keys are its data says so in a `facts` method. A collection is
a mapping keyed by its members' names, each member's facts beneath its name, so that a
dash means only a bare value with nothing to key it by, and the nesting alone says what
belongs to what (#765). Two facts every status shares are types of their own: a remedy,
the command a reader types (Command) or the reader's own act in words (Act), and a finding
(Finding), the FAIL the usr gate's table counts. A Command prints as a pair, the line its
key and what it does its value: what is typed is always a whole scalar. A noun written in shell hands its rows to
a status module beside it, which types them: no shell builds facts.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

STEP = 2   # the indentation of a subordinate fact

# a plain scalar YAML reads as a number, a boolean, null or a time, or that its indicators would cut
_NOT_PLAIN = re.compile(r'[-+]?(\d[\d_]*|\d*\.\d+|0x[0-9a-fA-F]+|\.inf|\.nan)|true|false|yes|no|on|off|null|~|\d{4}-\d\d-\d\d.*', re.I)
_INDICATORS = set('?:,[]{}#&*!|>\'"%@`')


def scalar(value) -> str:
    """One value as YAML writes it: numbers, booleans and None in their own spelling, a
    string plain where YAML would read it back as the same string, double-quoted - JSON's
    quoting, which YAML accepts - where it would not."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    plain = (text and text == text.strip() and not _NOT_PLAIN.fullmatch(text)
             and ': ' not in text and ' #' not in text and not text.endswith(':')
             and text[0] not in _INDICATORS and not (text[0] == '-' and (len(text) == 1 or text[1] == ' '))
             and '\n' not in text)
    return text if plain else json.dumps(text, ensure_ascii=False)


def lines(facts, depth: int = 0) -> list[str]:
    """The facts as lines: a mapping's keys in their given order, each a line, with a
    nested mapping or list beneath it; a list's items each a line opening with a dash, a
    mapping item carrying its first pair on that line and the rest beneath."""
    pad = ' ' * (depth * STEP)
    out: list[str] = []
    if isinstance(facts, dict):
        if not facts:
            return [pad + '{}']
        for key, value in facts.items():
            if isinstance(value, (dict, list)) and value:
                out.append(f'{pad}{scalar(key)}:')
                out.extend(lines(value, depth + 1))
            else:
                out.append(f'{pad}{scalar(key)}: {scalar(value) if not isinstance(value, (dict, list)) else ("{}" if isinstance(value, dict) else "[]")}')
        return out
    if isinstance(facts, list):
        if not facts:
            return [pad + '[]']
        for item in facts:
            if isinstance(item, dict) and item:
                inner = lines(item, depth + 1)
                out.append(f'{pad}- {inner[0].lstrip()}')
                out.extend(inner[1:])
            elif isinstance(item, list) and item:
                out.append(f'{pad}-')
                out.extend(lines(item, depth + 1))
            else:
                out.append(f'{pad}- {scalar(item) if not isinstance(item, (dict, list)) else ("{}" if isinstance(item, dict) else "[]")}')
        return out
    return [pad + scalar(facts)]


def named(label: str, **kwargs):
    """A field that prints under a key its name cannot spell - a path, a name with a dot."""
    return field(metadata={'key': label}, **kwargs)


@dataclass(frozen=True)
class Command:
    """A remedy the reader types: a corpus-yoga command, or a standard tool's."""
    line: str                     # the command as typed
    does: str                     # what it does

    def facts(self) -> dict:
        return {self.line: self.does}


@dataclass(frozen=True)
class Act:
    """A remedy that is the reader's own act, in words: nothing types it."""
    words: str

    def said(self) -> str:
        return self.words


@dataclass(frozen=True)
class Finding:
    """What a status found wrong: the FAIL the usr gate's stage table counts, and its remedy."""
    FAIL: str
    remedy: Command | Act | None = None


def plain(shape):
    """The shape as the mappings, lists and scalars the printer prints: a dataclass its
    fields in order under their keys, None omitted; one that says itself, its words; one
    with a `facts` method, what that returns."""
    if is_dataclass(shape) and not isinstance(shape, type):
        said = getattr(shape, 'said', None)
        if callable(said):
            return said()
        own = getattr(shape, 'facts', None)
        if callable(own):
            return plain(own())
        return {f.metadata.get('key', f.name.replace('_', ' ')): plain(getattr(shape, f.name))
                for f in fields(shape) if getattr(shape, f.name) is not None}
    if isinstance(shape, dict):
        return {key: plain(value) for key, value in shape.items() if value is not None}
    if isinstance(shape, (list, tuple)):
        return [plain(item) for item in shape]
    if isinstance(shape, PurePath):
        return shape.as_posix()
    return shape


def say(shape: DataclassInstance) -> None:
    """Print a status: its named shape, as YAML. A status is said once, whole, so that its
    keys are the fields of one type."""
    print('\n'.join(lines(plain(shape))))
