"""
facts.py - a verb's facts as nested indented lines, YAML, from one printer (issues/740).

A status holds its facts as data - mappings of counts, lists of units, a verdict - and
prints them here: one fact per line, a fact that qualifies another indented beneath it,
a heading over the items it covers. The lines are YAML, so the same artifact is read by a
human by its shape and loaded by a machine as data; no width is enforced, since a line
that is one fact is as long as its fact. Said to a terminal, a value too long for the
terminal's width continues on lines indented beneath it (issues/790), which YAML and the reader
here both read as the one value; said anywhere else a fact stays one line. The emitter covers what a status holds -
mappings, lists, strings, numbers, booleans and None - and quotes a string wherever YAML
would otherwise read it as something else.

A status's facts are a named shape (issues/759): a dataclass whose fields are the facts it
holds, so that a reader takes them as fields and the type check holds the keys. A field
prints under its name's words, or under the key `named` gives it; a field that is None is
not printed; a shape whose keys are its data says so in a `facts` method. A collection is
a mapping keyed by its members' names, each member's facts beneath its name, so that a
dash means only a bare value with nothing to key it by, and the nesting alone says what
belongs to what (issues/765). A status line is one of three (issues/1034): a fact, settled; an
act (Would), a declared corpus-yoga verb with what it would act on, which now: lifts; or an
unsettled reading (Unsettled), which now: lifts under the noun that reports it. An act is said
only in now:, under the modality its verb declares - MAY or MUST, in RFC 2119's words
(issues/1050) - and never where it stands in the body, which says the fact alone. No act is
written in words or as a command no verb declares - there is no type to write one in. A
finding (Finding) is the FAIL the usr gate's table counts. A noun written in shell hands its rows to
a status module beside it, which types them: no shell builds facts.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING

import tier  # the launcher's names, one home

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

STEP = 2   # the indentation of a subordinate fact

# a plain scalar YAML reads as a number, a boolean, null, a date or a time - a time only where
# its clock has colons, so a stamp like 2026-10-04T182101Z is text - or that its indicators would cut
_NOT_PLAIN = re.compile(r'[-+]?(\d[\d_]*|\d*\.\d+([eE][-+]\d+)?|0x[0-9a-fA-F]+|\.inf|\.nan)|true|false|yes|no|on|off|null|~'
                        r'|\d{4}-\d\d?-\d\d?([Tt ]\d\d?:\d\d:\d\d(\.\d*)?( ?(Z|[-+]\d\d?(:\d\d)?))?)?', re.I)
_INDICATORS = set('?:,[]{}#&*!|>\'"%@`')


def scalar(value) -> str:
    """One value as YAML writes it: numbers, booleans and None in their own spelling, a
    string plain where YAML would read it back as the same string, double-quoted - JSON's
    quoting, which YAML accepts - where it would not."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, float):
        return _float(value)
    text = str(value)
    plain = (text and text == text.strip() and not _NOT_PLAIN.fullmatch(text)
             and ': ' not in text and ' #' not in text and not text.endswith(':')
             and text[0] not in _INDICATORS and not (text[0] == '-' and (len(text) == 1 or text[1] == ' '))
             and '\n' not in text)
    return text if plain else json.dumps(text, ensure_ascii=False)


def _rows(facts, depth: int) -> list[tuple[int, str, str | None]]:
    """The facts as rows: each a line's indentation, its head - a key and its colon, a
    dash, both, or nothing - and the value that follows the head on that line, if any."""
    indent = depth * STEP
    out: list[tuple[int, str, str | None]] = []

    def inline(value) -> str:
        return scalar(value) if not isinstance(value, (dict, list)) else ('{}' if isinstance(value, dict) else '[]')
    if isinstance(facts, dict):
        if not facts:
            return [(indent, '', '{}')]
        for key, value in facts.items():
            if isinstance(value, (dict, list)) and value:
                out.append((indent, f'{scalar(key)}:', None))
                out.extend(_rows(value, depth + 1))
            else:
                out.append((indent, f'{scalar(key)}:', inline(value)))
        return out
    if isinstance(facts, list):
        if not facts:
            return [(indent, '', '[]')]
        for item in facts:
            if isinstance(item, dict) and item:
                inner = _rows(item, depth + 1)
                out.append((indent, f'- {inner[0][1]}', inner[0][2]))
                out.extend(inner[1:])
            elif isinstance(item, list) and item:
                out.append((indent, '-', None))
                out.extend(_rows(item, depth + 1))
            else:
                out.append((indent, '-', inline(item)))
        return out
    return [(indent, '', scalar(facts))]


# A continuation line that opened on one of these would read as something other than the
# rest of its value - an item, a comment, a key - so no break falls before such a word.
_NO_BREAK_BEFORE = set('-?:#&*!|>%@`[]{},')


def _broken(indent: int, head: str, value: str, width: int) -> list[str]:
    """One row as lines no longer than `width` where its words allow: the value broken
    between words, each continuation indented deeper than the row's key, or than its dash
    where it has no key. YAML folds such lines into the one value, a space at each
    break, plain or double-quoted - so a break falls only at a single space, and a value
    holding two together, or none, stays one line."""
    first = ' ' * indent + head + (' ' if head else '')
    words = value.split(' ')
    if len(first) + len(value) <= width or len(words) < 2 or '' in words:
        return [first + value]
    beneath = ' ' * (indent + (STEP if head.startswith('-') else 0) + (STEP if head.endswith(':') else 0))
    out: list[str] = []
    line: list[str] = [words[0]]
    lead = first
    for word in words[1:]:
        if len(lead) + len(' '.join(line)) + 1 + len(word) <= width:
            line.append(word)
            continue
        carried: list[str] = []
        if word[0] in _NO_BREAK_BEFORE:               # the break moves a word earlier, and the word goes down with this one
            if len(line) < 2 or line[-1][0] in _NO_BREAK_BEFORE:
                line.append(word)                     # no earlier place to break: the line runs long
                continue
            carried = [line.pop()]
        out.append(lead + ' '.join(line))
        lead, line = beneath, [*carried, word]
    out.append(lead + ' '.join(line))
    return out


def lines(facts, depth: int = 0, width: int | None = None) -> list[str]:
    """The facts as lines: a mapping's keys in their given order, each a line, with a
    nested mapping or list beneath it; a list's items each a line opening with a dash, a
    mapping item carrying its first pair on that line and the rest beneath. Given a
    width, a value that would pass it continues on indented lines; a key is never broken."""
    out: list[str] = []
    for indent, head, value in _rows(facts, depth):
        if value is None:
            out.append(' ' * indent + head)
        elif width is None:
            out.append(' ' * indent + head + (' ' if head else '') + value)
        else:
            out.extend(_broken(indent, head, value, width))
    return out


def opening(key: str, depth: int = 0) -> str:
    """The line that opens a mapping whose members are printed one by one as they become
    known - an act's loop, which says each entry before its act - so that a verb that
    prints progressively still prints no head of its own; `lines` prints the members
    at depth + 1, and the whole reads back as the mapping."""
    return ' ' * (depth * STEP) + scalar(key) + ':'


# -- reading: the printer's inverse ------------------------------------------------------------

# YAML's own number grammar, as its readers resolve it: a float has a dot, and an exponent
# follows the dot with its sign - so a sha of the shape 34e10310 is the string it is.
_NUMBER = re.compile(r'-?\d+(\.\d+([eE][-+]\d+)?)?')
_NOT_FINITE = {'.inf': float('inf'), '-.inf': float('-inf'), '.nan': float('nan')}


def _float(value: float) -> str:
    """A float as YAML reads it back: repr with a dot before any exponent, and YAML's
    spelling of the infinities and nan."""
    if value != value:
        return '.nan'
    if value in (float('inf'), float('-inf')):
        return '.inf' if value > 0 else '-.inf'
    text = repr(value)
    if 'e' in text and '.' not in text:
        text = text.replace('e', '.0e')
    return text


def _scalar(text: str):
    """One printed value read back: what `scalar` wrote, and an empty mapping or list."""
    if text.startswith('"'):
        return json.loads(text)
    if text in ('null', 'true', 'false'):
        return {'null': None, 'true': True, 'false': False}[text]
    if text in ('{}', '[]'):
        return {} if text == '{}' else []
    if text in _NOT_FINITE:
        return _NOT_FINITE[text]
    if _NUMBER.fullmatch(text):
        return float(text) if '.' in text else int(text)
    return text


def _pair(text: str) -> tuple[str, str] | None:
    """A line as a key and what follows its colon; None where the line is no pair."""
    if text.startswith('"'):
        try:
            key, end = json.JSONDecoder().raw_decode(text)
        except ValueError:
            return None
        if not isinstance(key, str) or text[end:end + 1] != ':' or text[end + 1:end + 2] not in ('', ' '):
            return None
        return key, text[end + 1:].strip()
    at = text.find(': ')
    if at != -1:
        return text[:at], text[at + 2:].strip()
    return (text[:-1], '') if text.endswith(':') else None


def _continued(rows: list[tuple[int, str]], at: int, indent: int, value: str) -> tuple[str, int]:
    """A value with the lines that continue it - each deeper than `indent`, where its key
    or its dash stands - joined by a space at each break: (the value, the row after it)."""
    while at < len(rows) and rows[at][0] > indent:
        value, at = f'{value} {rows[at][1]}', at + 1
    return value, at


def _block(rows: list[tuple[int, str]], start: int, indent: int):
    """The mapping or list whose lines stand at `indent` from row `start`: (it, the row after it)."""
    at = start
    if rows[at][1] == '-' or rows[at][1].startswith('- '):
        items: list = []
        while at < len(rows) and rows[at][0] == indent and (rows[at][1] == '-' or rows[at][1].startswith('- ')):
            rest = rows[at][1][1:].strip()
            if not rest:                              # a list beneath the dash
                item, at = _block(rows, at + 1, rows[at + 1][0])
            elif _pair(rest) is not None:             # a mapping whose first pair shares the dash's line
                rows[at] = (indent + STEP, rest)
                item, at = _block(rows, at, indent + STEP)
            else:
                rest, at = _continued(rows, at + 1, indent, rest)
                item = _scalar(rest)
            items.append(item)
        return items, at
    out: dict = {}
    while at < len(rows) and rows[at][0] == indent:
        pair = _pair(rows[at][1])
        if pair is None:
            raise ValueError(f'line {at + 1} is neither a pair nor an item: {rows[at][1][:60]}')
        key, rest = pair
        if key in out:
            raise ValueError(f'the key {key!r} stands twice in one mapping')
        if rest:
            rest, at = _continued(rows, at + 1, indent, rest)
            out[key] = _scalar(rest)
        elif at + 1 < len(rows) and rows[at + 1][0] > indent:
            out[key], at = _block(rows, at + 1, rows[at + 1][0])
        else:
            raise ValueError(f'the key {key!r} holds nothing')
    if at < len(rows) and rows[at][0] > indent:
        raise ValueError(f'line {at + 1} is indented under nothing: {rows[at][1][:60]}')
    return out, at


def load(text: str):
    """What `lines` printed, read back as the mappings, lists and scalars it was printed
    from: the printer's inverse, and no more of YAML than the printer writes. It needs
    nothing outside the standard library, so a reader of a status runs where the printer
    does (issues/766); the dev gate holds the two as inverses against a YAML reader."""
    rows = [(len(line) - len(line.lstrip(' ')), line.strip()) for line in text.splitlines() if line.strip()]
    if not rows:
        return {}
    out, at = _block(rows, 0, rows[0][0])
    if at != len(rows):
        raise ValueError(f'line {at + 1} stands outside what precedes it: {rows[at][1][:60]}')
    return out


def named(label: str, **kwargs):
    """A field that prints under a key its name cannot spell - a path, a name with a dot."""
    return field(metadata={'key': label}, **kwargs)


@dataclass(frozen=True)
class Would:
    """An act a status names (issues/1028): the command as typed, and what it would act on -
    each thing with how many, or with what changes in it beneath. What the act would do, and
    whether the room must or may do it, are what its verb declares (`would` and `modality`,
    src/main/cli/<noun>/<verb>.json), never the caller's; a noun's now: is every act its body
    holds, gathered by now_of, so that an act is said once, in one shape, and only there."""
    line: str
    acts_on: dict

    def facts(self) -> dict:
        return {self.line: {would_of(self.line): self.acts_on}}

    @property
    def modality(self) -> str:
        return declared_of(self.line)['modality']


@dataclass(frozen=True)
class Unsettled:
    """A reading a status could not settle - unverified, unread or unknown, with why - said in
    its body as its words, and lifted into now: under the noun that reports it (issues/1034),
    as an act is: a reader is shown what stands unsettled, never only what to run."""
    reading: str
    noun: str

    def said(self) -> str:
        return self.reading


@dataclass(frozen=True)
class Acts:
    """Several acts named at one spot, said as one mapping by command."""
    acts: tuple[Would, ...]

    def facts(self) -> dict:
        out: dict = {}
        for act in self.acts:
            merge(out, act.facts())
        return out


_DECLARED: dict[str, dict] = {}


def declared_of(line: str) -> dict:
    """The declaration of the verb the command runs: the verb named after the noun, or the
    noun's own declaration where none is."""
    words = line.split()
    at = next(i for i, word in enumerate(words) if word.endswith('corpus-yoga'))
    noun = words[at + 1]
    verb = words[at + 2] if len(words) > at + 2 and not words[at + 2].startswith('-') else noun
    key = f'{noun} {verb}'
    if key not in _DECLARED:
        declared = Path(__file__).resolve().parents[2] / 'src' / 'main' / 'cli' / noun / f'{verb}.json'
        _DECLARED[key] = json.loads(declared.read_text())
    return _DECLARED[key]


def would_of(line: str) -> str:
    """What the command would do, in the words its verb declares."""
    return declared_of(line)['would']


def merge(into: dict, more: dict, once: bool = False) -> dict:
    """More acts into a mapping of acts: counts of one thing added - or, where the same act is
    named twice (`once`, two nouns naming one unit), the larger kept - mappings merged, and a
    value that is neither taken as it stands."""
    import copy
    for key, value in more.items():
        held = into.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and isinstance(held, int) and not isinstance(held, bool):
            into[key] = max(held, value) if once else held + value
        elif isinstance(value, dict) and isinstance(held, dict):
            merge(held, value, once)
        else:
            into[key] = copy.deepcopy(value)
    return into


REPORTS = 'reports the noun'   # beneath a noun's command in now:, what it reports and cannot settle
MODALITY = ('MAY', 'MUST')     # RFC 2119's words, in the order now: says them (issues/1050)


def ordered(now: dict) -> dict:
    """A now: as said: MAY first, MUST last, a modality with no act not said."""
    return {modality: now[modality] for modality in MODALITY if now.get(modality)}


def now_of(shape) -> dict:
    """A status's now: - every act it names, gathered by command and merged (issues/1028) under
    the modality its verb declares (issues/1050), and every reading it could not settle, under the
    noun that reports it (issues/1034) and under MAY, since reading it again is the reader's
    choice - so that no noun composes its now: beside its body. Gathered from the facts the
    body says, so that a field its own `facts` leaves unsaid names no act; a nested now: is no
    act of the body. Empty where the body names nothing."""
    out: dict = {}

    def walk(node) -> None:
        if isinstance(node, Would):
            merge(out, {node.modality: node.facts()})
        elif isinstance(node, Acts):
            for act in node.acts:
                walk(act)
        elif isinstance(node, Unsettled):
            merge(out, {'MAY': {f'corpus-yoga {node.noun}': {REPORTS: {node.reading: 1}}}}, once=True)
        elif is_dataclass(node) and not isinstance(node, type):
            own = getattr(node, 'facts', None)
            if callable(own):
                walk(own())
            else:
                for f in fields(node):
                    if f.name != 'now':
                        walk(getattr(node, f.name))
        elif isinstance(node, dict):
            for key, value in node.items():
                if key != 'now':
                    walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(shape)
    return ordered(out)


@dataclass(frozen=True)
class Finding:
    """What a status found wrong: the FAIL the usr gate's stage table counts, and its remedy."""
    FAIL: str
    remedy: Would | None = None


def _kept(pairs) -> dict | None:
    """The pairs said: each value plain, an act and None omitted - an act is said in now: only
    (issues/1050) - and None where every pair held an act, so that a key that held only acts is
    not said either."""
    held = [(key, value) for key, value in pairs if value is not None]
    out = {key: said for key, value in held if (said := plain(value)) is not None}
    return None if held and not out else out


def plain(shape):
    """The shape as the mappings, lists and scalars the printer prints: a dataclass its
    fields in order under their keys, None and acts omitted; one that says itself, its words;
    one with a `facts` method, what that returns; an act, None - it is said in now:."""
    if isinstance(shape, (Would, Acts)):
        return None
    if is_dataclass(shape) and not isinstance(shape, type):
        said = getattr(shape, 'said', None)
        if callable(said):
            return said()
        own = getattr(shape, 'facts', None)
        if callable(own):
            return plain(own())
        return _kept((f.metadata.get('key', f.name.replace('_', ' ')), getattr(shape, f.name)) for f in fields(shape))
    if isinstance(shape, dict):
        return _kept(shape.items())
    if isinstance(shape, (list, tuple)):
        items = [said for item in shape if (said := plain(item)) is not None]
        return None if shape and not items else items
    if isinstance(shape, PurePath):
        return shape.as_posix()
    return shape


def terminal_width() -> int | None:
    """The width of the terminal the lines are printed to; None where they go to a pipe,
    a file or a capture, whose reader is given one line a fact."""
    return shutil.get_terminal_size().columns if sys.stdout.isatty() else None


DEPTH = 'CORPUS_YOGA_NARRATION_DEPTH'   # the depth an inner verb's lines stand at: a step of another verb's record (issues/805)


def depth() -> int:
    """The depth the calling verb's lines stand at: 0 for the verb the reader typed, deeper
    for a verb run as a step of another's, which sets it for the step."""
    return int(os.environ.get(DEPTH) or 0)


def narration(event) -> list[str]:
    """One event of a record as the lines of one list item at the depth (issues/805): a command
    with its outcome beneath - `- <command>:` then `did: done` or `did NOT: exit N` - a read
    with its answer on the item line, or a phrase alone. A record is a list of events under
    the step it belongs to, so that it loads as data and reads by its shape."""
    return lines([event], depth())


def say(shape: DataclassInstance) -> None:
    """Print a status: its named shape, as YAML, at the depth. A status is said once, whole, so
    that its keys are the fields of one type."""
    print('\n'.join(lines(plain(shape), depth(), width=terminal_width())))


def say_standing(shape: DataclassInstance) -> None:
    """Print a noun's bare status, which ends on now: (issues/1034): its shape, then every act it
    names and every reading it could not settle, gathered by now_of - or none."""
    said = plain(shape)
    assert isinstance(said, dict), 'a status is a mapping'
    said['now'] = now_of(shape) or phrase('none - nothing to do')
    print('\n'.join(lines(said, depth(), width=terminal_width())))


ACT = tier.ACT                   # the launcher names the act it dispatched, `<command> <verb>` (issues/896)
EFFECT = 'CORPUS_YOGA_EFFECT'    # and the file the act hands its effect up through


def handed_up(effect: str) -> bool:
    """Whether this effect is the launcher's to say: the launcher named the act it
    dispatched and the file to hand the effect through, and the effect line is that act's
    - `<command> <verb>: …` - not an inner verb's. Where it is, the effect is written there,
    in the printer's lines, for src/main/reply.py."""
    act, path = os.environ.get(ACT, ''), os.environ.get(EFFECT, '')
    if not act or not path or not effect.startswith(act + ':'):
        return False
    handed = {'effect': effect}
    Path(path).write_text('\n'.join(lines(plain(handed))) + '\n')
    return True


def report_lines(outcomes, effect: str) -> list[str]:
    """What an act reports (issues/801, issues/896), as lines: its facts by outcome, where it has not
    already printed them act by act; then its effect line, `<noun> <verb>: DONE - …` or
    `NOT DONE - …`. now: is the launcher's reply, never the verb's: where the launcher
    dispatched this act the effect is handed up and the launcher replies with the bare
    status - what stands in the way, then now:, the room's standing read after the act,
    which no act adds steps of its own to (issues/947, issues/1016) - then the effect; where
    none did - an inner invocation, a step of another verb - the effect is the last line
    and no now: is said."""
    out: list[str] = []
    if outcomes:
        said = plain(outcomes)
        if isinstance(said, dict):
            out = lines(plain(said), width=terminal_width())
    if handed_up(effect):
        return out
    return out + [effect]


_DECLARED_PHRASE: dict[str, str] | None = None


def declared_phrase() -> dict[str, str]:
    """Every phrase a status can say, by the noun whose declaration holds it: the
    `phrase` arrays of src/main/cli/<noun>/<noun>.json (issues/909)."""
    global _DECLARED_PHRASE
    if _DECLARED_PHRASE is None:
        _DECLARED_PHRASE = {}
        for declared in sorted((Path(__file__).resolve().parents[2] / 'src' / 'main' / 'cli').glob('*/*.json')):
            if declared.stem == declared.parent.name:
                for said in json.loads(declared.read_text()).get('phrase', []):
                    _DECLARED_PHRASE[said] = declared.parent.name
    return _DECLARED_PHRASE


def phrase(template: str, **places) -> str:
    """A phrase a status says, quoted as its noun's declaration holds it, with its places
    filled (issues/909, issues/935). A phrase no declaration holds is unrepresentable: it raises here, in
    every room, rather than printing in the one room whose state selects it."""
    if template not in declared_phrase():
        raise KeyError(f'no declaration holds the phrase {template!r}')
    return template.format_map(places)


def report(outcomes, effect: str) -> None:
    """Print what an act reports (issues/801, issues/896): report_lines, each a line."""
    said = report_lines(outcomes, effect)
    if said:
        pad = ' ' * (depth() * STEP)
        print('\n'.join(pad + line for line in said), flush=True)
