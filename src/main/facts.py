"""
facts.py - a verb's facts as nested indented lines, YAML, from one printer (#740).

A status holds its facts as data - mappings of counts, lists of units, a verdict - and
prints them here: one fact per line, a fact that qualifies another indented beneath it,
a heading over the items it covers. The lines are YAML, so the same artifact is read by a
human by its shape and loaded by a machine as data; no width is enforced, since a line
that is one fact is as long as its fact. The emitter covers what a status holds -
mappings, lists, strings, numbers, booleans and None - and quotes a string wherever YAML
would otherwise read it as something else. Run as a script, it reads the facts as JSON
on stdin and prints them - the same printer for a noun written in shell, which builds
its facts with jq (#753).
"""
import json
import re
import sys

SELF = 'src/main/facts.py'

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


def say(facts) -> None:
    print('\n'.join(lines(facts)))


if __name__ == '__main__':
    say(json.load(sys.stdin))
