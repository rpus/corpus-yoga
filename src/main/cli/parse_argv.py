#!/usr/bin/env python
"""parse_argv.py — a verb's argv, answered from its declaration (#474).

The python face of parse_argv.sh: a bash target has no argparse to answer
`yoga <command> <verb> -h`, so `-h` used to land in the verb's own argv — an
ENACTING verb could receive a flag-shaped token as its argument and start its
chain (tmp/logs/forge/flip/2026-08-13T083136Z.log is the fixture). This face
asks cli.py — the one reader of src/main/cli/ — for the verb's declared rows,
answers help from them, and refuses argv the declaration does not express, so
the refusal precedes any act.

Invocation: parse_argv.py <command> <verb> [argv...]. The verdict is the exit
code, the words are stdout:

    0, empty stdout   argv is valid — the caller proceeds with it unchanged
    0, help on stdout a -h/--help token — the caller prints and exits 0
    2, error on stdout the refusal (usage + error) — the caller relays to
                       stderr and exits 2
    anything else      this face itself failed (a wiring bug, never the user)

Validation enforces only what declarations express: flags by exact name (a
declared type means the flag consumes the next token as its value), positionals
by declared order, cardinality '1' required and blank optional. Any richer
cardinality is not enforced — under-enforcement leaves the target's own
refusals in charge; over-enforcement would refuse argv the surface accepts.
Tokens are matched as the bash targets speak them: no '--flag=value' fusing,
which no target parses.

STDLIB-ONLY, like cli.py: the yoga launcher and the bash targets run on system
python3 before any venv exists.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/parse_argv.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_file.parent))
import cli  # noqa: E402 — the one reader of src/main/cli/


def refusal(command: str, verb: str, error: str) -> str:
    """The argparse voice, so both languages refuse in the same shape."""
    return f'usage: {cli.verb_usage(command, verb)}\nyoga {command} {verb}: error: {error}\n'


def validate(command: str, verb: str, argv: list[str]) -> str | None:
    """None when argv is what the declaration expresses; else the refusal text."""
    rows = [r for r in cli.command_rows(command) if r['subcommand'] == verb and r['arg-name']]
    flags = {r['arg-name']: r for r in rows if r['arg-name'].startswith('--')}
    positionals = [r for r in rows if not r['arg-name'].startswith('--')]
    given = 0
    tokens = list(argv)
    while tokens:
        token = tokens.pop(0)
        if token.startswith('-'):
            flag = flags.get(token)
            if flag is None:
                return refusal(command, verb, f'unrecognized arguments: {token}')
            if flag['arg-type']:
                if not tokens:
                    return refusal(command, verb, f'argument {token}: expected one argument')
                tokens.pop(0)
            continue
        given += 1
        if given > len(positionals):
            return refusal(command, verb, f'unrecognized arguments: {token}')
    required = [r for r in positionals[given:] if r['cardinality'] == '1']
    if required:
        names = ', '.join(r['arg-type'] or r['arg-name'] for r in required)
        return refusal(command, verb, f'the following arguments are required: {names}')
    return None


def main() -> int:
    command, verb, argv = sys.argv[1], sys.argv[2], sys.argv[3:]
    if verb not in cli.subcommands_of(command):
        print(f'parse_argv.py: {command} declares no verb {verb!r}', file=sys.stderr)
        return 70
    if any(t in ('-h', '--help') for t in argv):
        print(cli.render_verb_help(command, verb), end='')
        return 0
    error = validate(command, verb, argv)
    if error is not None:
        print(error, end='')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
