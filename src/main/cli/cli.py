#!/usr/bin/env python
"""
cli.py — the machinery behind `./yoga`, the repo's terminal surface.

One curated table (rsc/cli/commands.csv; format: rsc/cli/README.md) is the
whole interface: a bare `./yoga` renders it as help, `./yoga <command> [args...]`
execs the row's target with the args forwarded verbatim (so
`./yoga <command> --help` prints the TARGET's help — each script stays the one
authority on its own interface), and `./yoga completions` derives static zsh
tab-completion from the same table. Presentation is re-derived on every
invocation and stored nowhere (L5); the CLI adds no behaviour of its own.

The table also speaks the calculus: each row cites the rsc/CALCULUS.md
operations and laws its command performs, and the pre-commit code tier
(check_cli_surface) holds it to that — cited terms must be defined there,
targets must exist, advertised flags must appear in the target's source (or its
stem-sibling wrapper/implementation), and advertised subcommand VERBS must appear
in the target's own --help output — the live dispatch surface, not a source grep.
The vocabulary is parsed from the calculus document itself (calculus_terms),
never restated.

Usage:
    ./yoga                       # render the table
    ./yoga <command> [args...]   # exec the target
    ./yoga completions [--write]  # zsh completion to stdout, or written under cache/
    ./yoga commands              # every command's syntax: a SYNOPSIS derived from the table

This module is deliberately STDLIB-ONLY: the ./yoga launcher falls back to
system python3 when the venv does not exist yet, so a fresh clone can render
the table, print the calculus, and generate completion before ./RUNME.sh has
run. Adding a third-party import here would silently break that.
"""
import csv
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TABLE = REPO / 'rsc' / 'cli' / 'commands.csv'
COLUMNS = ('command', 'target', 'usage', 'calculus', 'step', 'summary')
COMPLETION_OUT = REPO / 'cache' / 'completions' / '_yoga'


def commands() -> list[dict]:
    """The curated command table. Raises if the columns drift from COLUMNS —
    the table is an interface, not a suggestion."""
    with TABLE.open() as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f'{TABLE.relative_to(REPO)}: '
                             f'columns {reader.fieldnames} != {list(COLUMNS)}')
        return list(reader)


def flags_of(usage: str) -> list[str]:
    """The --flags a usage sketch advertises — machine-read for completion and
    for the flags-exist-in-target check. Brackets, pipes, AND parens are grouping
    punctuation, never flag text — a '(--a|--b)' choice must not leak '--b)' into
    the emitted completion (it did once: the zsh file failed to parse). Deduped
    preserving order: a flag repeated across alternatives (agent's --session)
    advertises once."""
    toks = [t for t in re.sub(r'[\[\]|()]', ' ', usage).split() if t.startswith('--')]
    return list(dict.fromkeys(toks))


def verbs_of(usage: str) -> list[str]:
    """The subcommand verbs a usage sketch advertises: the first bare word of each
    ' | '-separated alternative (not a --flag, not a <placeholder>). Alternatives
    are spaced ' | '; an enum value like '--only a|b' uses an unspaced '|' and so is
    not split. check_cli_surface verifies each against the TARGET'S OWN --help
    output (argparse renders the live subparsers; shell targets print their real
    usage) — a renamed or un-dispatched verb goes red even while the word survives
    in the source, which a source grep could never catch (verbs are ordinary
    words)."""
    verbs = []
    for alt in usage.split(' | '):
        tok = alt.strip().lstrip('[').split(' ', 1)[0]
        if re.fullmatch(r'[a-z][a-z-]*', tok):
            verbs.append(tok)
    return verbs


def calculus_terms() -> set[str]:
    """The citable vocabulary, parsed from rsc/CALCULUS.md itself: every bolded
    bullet lead (operations, products), compound names split on ' / ' with
    parentheticals dropped, plus the law ids. The calculus document is the one
    authority; the table must speak its language."""
    text = (REPO / 'rsc' / 'CALCULUS.md').read_text()
    terms: set[str] = set()
    for m in re.finditer(r'^- \*\*(.+?)\*\*', text, re.M):
        name = m.group(1)
        if law := re.match(r'(L\d+) —', name):
            terms.add(law.group(1))
            continue
        for part in re.sub(r'\s*\([^)]*\)', '', name).split(' / '):
            terms.add(part.strip())
    return terms


def render_synopsis(cmds: list[dict]) -> str:
    """`yoga commands` — every command's syntax, man-page SYNOPSIS style (and
    nothing else, for now) — derived from the table on every invocation and
    stored nowhere (L5), so it can never drift from the one authority. One
    invocation FORM per line: a usage's ' | '-separated alternatives are
    distinct forms (the same split verbs_of reads); an unspaced '|' is an enum
    inside one form and stays put."""
    out = ['yoga(1) — claude-export-yoga', '', 'SYNOPSIS',
           '  yoga',
           '  yoga <command> --help']
    for c in cmds:
        if not c['usage']:
            out.append(f'  yoga {c["command"]}')
            continue
        for alt in c['usage'].split(' | '):
            out.append(f'  yoga {c["command"]} {alt.strip()}')
    out.append('')
    return '\n'.join(out)


def render_help(cmds: list[dict]) -> str:
    out = ['yoga — the terminal surface of claude-export-yoga',
           'table: rsc/cli/commands.csv · calculus: rsc/CALCULUS.md (`./yoga calculus`)',
           '',
           'usage: ./yoga <command> [args...]   # `./yoga <command> --help` asks the target itself',
           '']
    for c in cmds:
        out.append(f'  {c["command"]}' + (f' {c["usage"]}' if c['usage'] else ''))
        out.append(f'      {c["summary"]}'
                   + (f'  ⟨{c["calculus"]}⟩' if c['calculus'] else '')
                   + (f'  ≡ run step {c["step"]}' if c['step'] else ''))
    out += ['',
            'zsh completion: `./yoga completions --write`, then add the printed lines to ~/.zshrc',
            '']
    return '\n'.join(out)


def completion_script(cmds: list[dict]) -> str:
    """A static zsh completion function derived from the table (regenerate via
    `./yoga completions`; never edit the emitted file). The command word completes
    with summaries; after it, a word starting '-' completes the row's
    advertised flags and anything else completes as a path."""
    def esc(s: str) -> str:
        return (s.replace('\\', '\\\\').replace("'", "'\\''").replace(':', '\\:'))
    lines = [
        '#compdef yoga',
        '# derived from rsc/cli/commands.csv by `./yoga completions` — regenerate, never edit',
        '',
        '_yoga() {',
        '  local -a cmds opts',
        '  cmds=(',
        *[f"    '{esc(c['command'])}:{esc(c['summary'])}'" for c in cmds],
        '  )',
        '  if (( CURRENT == 2 )); then',
        "    _describe -t commands 'yoga command' cmds",
        '    return',
        '  fi',
        '  case "${words[2]}" in',
        *[f"    {c['command']}) opts=({' '.join(flags)}) ;;"
          for c in cmds if (flags := flags_of(c['usage']))],
        '  esac',
        '  if [[ ${words[CURRENT]} == -* ]]; then',
        '    (( ${#opts} )) && compadd -- "${opts[@]}"',
        '  else',
        '    _files',
        '  fi',
        '}',
        '',
        '_yoga "$@"',
        '',
    ]
    return '\n'.join(lines)


def tilde(p: Path) -> str:
    """Home-relative rendering: '~/dev/...' where p is under $HOME, else
    absolute. The printed ~ lines are portable across machines and users,
    and zsh expands ~ in an unquoted fpath entry and in an alias at use time."""
    home = Path.home()
    return f'~/{p.relative_to(home)}' if p.is_relative_to(home) else str(p)


def completion(rest: list[str]) -> int:
    if any(a in rest for a in ('-h', '--help')):
        # a help request is a question, never an action — and never the product
        print('yoga completions [--write] — emit zsh tab-completion derived from rsc/cli/commands.csv\n'
              '  (bare: print to stdout; --write: install under cache/completions/ and print the ~/.zshrc lines)')
        return 0
    text = completion_script(commands())
    if '--write' in rest:
        COMPLETION_OUT.parent.mkdir(parents=True, exist_ok=True)
        COMPLETION_OUT.write_text(text)
        print(f'wrote {COMPLETION_OUT.relative_to(REPO)}')
        print('→ add to ~/.zshrc (before compinit), then restart the shell:')
        print(f'    fpath=({tilde(COMPLETION_OUT.parent)} $fpath)')
        print(f"    alias yoga='{tilde(REPO / 'yoga')}'   # optional: yoga from anywhere")
        return 0
    print(text, end='')
    return 0


def dispatch(row: dict, rest: list[str]) -> int:
    """Exec the row's target, args forwarded verbatim; a .md target is printed.
    exec (not subprocess) so signals, exit codes, and interactivity are the
    target's own — the CLI leaves no process between the user and the script."""
    target = REPO / row['target']
    if target.suffix == '.md':
        print(target.read_text(), end='')
        return 0
    if target.suffix == '.py':
        runner = REPO / 'src' / 'run_python_script.sh'
        os.execv(str(runner), [runner.name, str(target), *rest])
    os.execv(str(target), [str(target), *rest])
    return 1  # unreachable


def main() -> int:
    argv = sys.argv[1:]
    cmds = commands()
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(render_help(cmds), end='')
        return 0
    row = next((c for c in cmds if c['command'] == argv[0]), None)
    if row is None:
        print(f'yoga: unknown command {argv[0]!r} — the table:\n', file=sys.stderr)
        print(render_help(cmds), file=sys.stderr, end='')
        return 2
    if row['command'] == 'completions':
        return completion(argv[1:])
    if row['command'] == 'commands':
        print(render_synopsis(cmds), end='')
        return 0
    return dispatch(row, argv[1:])


if __name__ == '__main__':
    sys.exit(main())
