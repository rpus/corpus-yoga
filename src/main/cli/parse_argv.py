#!/usr/bin/env python
"""parse_argv.py — a verb's argv, answered by the declaration's own parser (#474).

The python face of parse_argv.sh: a bash target has no parser to answer
`yoga <command> <verb> -h`, so `-h` used to land in the verb's own argv — an
ENACTING verb could receive a flag-shaped token as its argument and start its
chain (tmp/logs/forge/flip/2026-08-13T083136Z.log is the fixture). This face
builds the verb's parser from its declaration (argparse_help.verb_parser) and
hands it the argv: argparse itself answers -h, refuses what the declaration
does not express, and words both from the declared rows — one engine, one
voice, the same shape a python target's own parser speaks.

Invocation: parse_argv.py <command> <verb> [argv...]. The verdict is the exit
code:

    0, empty stdout   argv is valid — the caller proceeds with it unchanged
    0, help on stdout a -h/--help token — the caller prints and exits 0
    2                  refused — argparse already wrote usage + error to stderr
    anything else      this face itself failed (a wiring bug, never the user)

STDLIB-ONLY, like cli.py: the yoga launcher and the bash targets run on system
python3 before any venv exists.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/parse_argv.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src'))
sys.path.insert(0, str(_file.parent))
import cli  # noqa: E402 — the one reader of src/main/cli/
from argparse_help import verb_parser  # noqa: E402 — the declaration's parser generator


def main() -> int:
    command, verb, argv = sys.argv[1], sys.argv[2], sys.argv[3:]
    if verb not in cli.subcommands_of(command):
        print(f'parse_argv.py: {command} declares no verb {verb!r}', file=sys.stderr)
        return 70
    verb_parser(command, verb).parse_args(argv)
    return 0


if __name__ == '__main__':
    sys.exit(main())
