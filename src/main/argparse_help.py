"""Fill an argparse parser's help text from rsc/cli/help.csv.

A target deleted its help= strings when help.csv became the single source for
argument wording. That left the target's own `-h` mute (bare flags, no prose) —
both when run directly and when reached via `yoga <command> <verb> -h`. This
puts the words back without storing them twice: the parser still owns the
structure (what arguments exist), help.csv owns the wording.

It also sets prog, for the same reason: a parser reached as `yoga agent capture`
should not print `usage: agent.py capture`, naming a file instead of the command.

Call enrich(parser, command) once, after building the parser, before parse_args.
Matching per help.csv row: a flag by its first option string (--session), a
positional by its dest (term), a subcommand by its name; a row with a blank
arg-name is that subcommand's own one-line description.

Pass subcommand when the parser IS one verb rather than holding subparsers —
cache routes clean and sync to separate flat scripts, so clean.py calls
enrich(ap, 'cache', 'clean') and its flags match the cache/clean help.csv rows.

Stdlib only, and it reaches into argparse's _actions / _SubParsersAction — the
usual way to post-process a parser; stable across CPython versions.
"""
import argparse
import csv
from pathlib import Path

_HELP_CSV = Path(__file__).resolve().parents[2] / 'rsc' / 'cli' / 'help.csv'


def _rows(command: str) -> list[dict]:
    with _HELP_CSV.open() as f:
        return [r for r in csv.DictReader(f) if r['command'] == command]


def _fill(parser, rows: list[dict]) -> None:
    """Set help= on each of parser's own arguments from its matching row."""
    by_name = {r['arg-name']: r for r in rows if r['arg-name']}
    for a in parser._actions:
        name = a.option_strings[0] if a.option_strings else a.dest
        r = by_name.get(name)
        if r and not a.help:
            a.help = r['help']


def enrich(parser, command: str, subcommand: str = '') -> None:
    # The parser is reached as `yoga <command> [<subcommand>]`, so that is what its usage
    # must name. argparse otherwise defaults prog to sys.argv[0], the implementation file
    # — `usage: agent.py capture`, naming something the reader did not type and the table
    # does not carry. Each subparser is set explicitly rather than left to inherit the
    # correction: add_parser snapshots the parent's prog when the subparser is built, so
    # assigning parser.prog here cannot reach one that already exists.
    parser.prog = ' '.join(w for w in ('yoga', command, subcommand) if w)
    rows = _rows(command)
    _fill(parser, [r for r in rows if r['subcommand'] == subcommand])
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for verb, sub in action.choices.items():
            sub.prog = f'{parser.prog} {verb}'
            verb_rows = [r for r in rows if r['subcommand'] == verb]
            for r in verb_rows:
                if not r['arg-name'] and not sub.description:
                    sub.description = r['help']
            _fill(sub, verb_rows)
