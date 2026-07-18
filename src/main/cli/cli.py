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
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TABLE = REPO / 'rsc' / 'cli' / 'commands.csv'
COLUMNS = ('command', 'target', 'usage', 'calculus', 'step', 'summary')
COMPLETION_OUT = REPO / 'cache' / 'completions' / '_yoga'
# The comment that tags the block `install` writes into ~/.zshrc, and by which
# `uninstall` finds it again. One constant, so the write and its inverse can never
# name the block differently.
COMPLETION_MARKER = '# yoga tab-completion (regenerate: ./yoga completions sync)'


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


def _forms(c: dict) -> list[str]:
    """A row's invocation forms: the usage's ' | '-separated alternatives (the
    same split verbs_of reads); an unspaced '|' is an enum inside one form."""
    if not c['usage']:
        return [f'yoga {c["command"]}']
    return [f'yoga {c["command"]} {alt.strip()}' for alt in c['usage'].split(' | ')]


def command_help_items(command: str) -> list[tuple[str, str]]:
    """(item, description) rows for a command from rsc/cli/help.csv — the one home
    for verb/flag helptext, hoisted into the command help so the targets' argparse
    carries none. Empty until a command's rows are added."""
    table = REPO / 'rsc' / 'cli' / 'help.csv'
    if not table.exists():
        return []
    with table.open() as f:
        return [(r['item'], r['help']) for r in csv.DictReader(f) if r['command'] == command]


def render_command_help(c: dict) -> str:
    """The standard command help, shared by `yoga <cmd> -h` and `yoga commands
    <cmd>`: the summary, every invocation form, and each verb/flag as a headed
    subparagraph (rsc/cli/help.csv). All from data (L5) — uniform, no drift. A
    noun's bare form (its status) leads."""
    forms = ([f"yoga {c['command']}   (status)"] if verbs_of(c['usage']) else []) + _forms(c)
    out = [f"yoga {c['command']} — {c['summary']}", '', *[f'  {f}' for f in forms]]
    items = command_help_items(c['command'])
    if items:
        out.append('')
        for item, text in items:
            out += [item, f'    {text}']
    return '\n'.join(out) + '\n'


def render_synopsis(cmds: list[dict], name: str | None = None) -> str:
    """`yoga commands [<command>]` — from the table (L5). With a command: its
    standard help. Bare: every command's forms, one per line."""
    if name:
        c = next((c for c in cmds if c['command'] == name), None)
        if c is None:
            return f'yoga commands: no command {name!r} — `yoga commands` lists them all\n'
        return render_command_help(c)
    out = ['yoga — claude-export-yoga', '']
    for c in cmds:
        out += [f'  {f}' for f in _forms(c)]
    return '\n'.join(out) + '\n'


def render_help(cmds: list[dict]) -> str:
    """`yoga -h` — the command menu: one line each, name and summary. Bare `yoga`
    runs the machine report (prerequisites); `yoga <command> -h` is a command's forms."""
    w = max(len(c['command']) for c in cmds)
    out = ['yoga — claude-export-yoga', '',
           *[f"  {c['command']:<{w}}  {c['summary']}" for c in cmds],
           '', '→ `yoga <command> -h` for its forms · `yoga <command>` for its status', '']
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


def install_completion() -> int:
    """Wire cache/completions into ~/.zshrc — idempotently, and ABOVE compinit.

    Position is the whole difficulty, which is why this is a command and not
    printed advice: zsh scans fpath when compinit RUNS, so a line added after it
    silently does nothing. That is the mistake the old printed lines invited (the
    obvious move is to append), and a grep for the string could not tell it from
    success. We insert above the first fpath=/compinit line, first backing up over
    its comment header so we land OUTSIDE a managed block — Docker Desktop rewrites
    its own block and would eat a line placed inside it.
    """
    zshrc = Path.home() / '.zshrc'
    fpath_line = f'fpath=({tilde(COMPLETION_OUT.parent)} $fpath)'
    lines = zshrc.read_text().splitlines() if zshrc.exists() else []
    if any(str(COMPLETION_OUT.parent) in l or tilde(COMPLETION_OUT.parent) in l for l in lines):
        print(f'{tilde(zshrc)}: already wired — nothing to do')
        return 0
    idx = next((i for i, l in enumerate(lines)
                if re.match(r'\s*(compinit\b|fpath=)', l)), None)
    if idx is None:
        lines += ['', COMPLETION_MARKER, fpath_line, 'autoload -Uz compinit', 'compinit']
        where = 'appended, with its own compinit (this ~/.zshrc had none)'
    else:
        while idx > 0 and lines[idx - 1].lstrip().startswith('#'):
            idx -= 1                      # step above the block's comment header
        lines[idx:idx] = [COMPLETION_MARKER, fpath_line, '']
        where = f'inserted at line {idx + 1}, above compinit'
    # No backup is written. The block is tagged (COMPLETION_MARKER) and positioned,
    # so --uninstall is a precise inverse the tool owns — a better undo than a
    # whole-file copy the user would have to remember to delete. Nothing lands
    # outside ~/.zshrc itself.
    zshrc.write_text('\n'.join(lines) + '\n')
    print(f'{tilde(zshrc)}: {where}')
    print(f'    {fpath_line}')
    print('  undo anytime: ./yoga completions uninstall')
    print(f"→ start a new shell (exec zsh). Optional, for yoga from anywhere:\n"
          f"    alias yoga='{tilde(REPO / 'yoga')}'")
    return 0


def uninstall_completion() -> int:
    """The exact inverse of install: remove the tagged yoga block from ~/.zshrc,
    leaving everything else byte-identical. The marker comment and the fpath line
    naming our completion dir are unambiguously ours; one adjacent blank (install
    leaves one on a side) goes with them. A compinit install added to a ~/.zshrc
    that had none is deliberately LEFT — it is generic zsh a later config may now
    rely on, and an idle compinit harms nothing; removing it could break what was
    built on top."""
    zshrc = Path.home() / '.zshrc'
    if not zshrc.exists():
        print(f'{tilde(zshrc)}: no such file — nothing to remove')
        return 0
    lines = zshrc.read_text().splitlines()
    parent, tparent = str(COMPLETION_OUT.parent), tilde(COMPLETION_OUT.parent)
    drop: set[int] = set()
    for i, l in enumerate(lines):
        if l.strip() == COMPLETION_MARKER:
            drop.add(i)
        elif l.lstrip().startswith('fpath=') and (parent in l or tparent in l):
            drop.add(i)  # the fpath line, even if the marker was hand-removed
    if not drop:
        print(f'{tilde(zshrc)}: no yoga completion block found — nothing to remove')
        return 0
    lo, hi = min(drop), max(drop)
    if hi + 1 < len(lines) and lines[hi + 1].strip() == '':
        drop.add(hi + 1)                  # the blank install left after an insert
    elif lo > 0 and lines[lo - 1].strip() == '':
        drop.add(lo - 1)                  # or the blank it left before an append
    kept = [l for i, l in enumerate(lines) if i not in drop]
    zshrc.write_text('\n'.join(kept) + '\n')
    print(f'{tilde(zshrc)}: removed the yoga completion block ({len(drop)} lines) — '
          'nothing else touched')
    print('→ start a new shell (exec zsh) for it to take effect')
    return 0


def completion_status() -> int:
    """The bare-noun default: show current state, write nothing. Whether the _yoga
    file is written (and current with the table) and whether ~/.zshrc is wired."""
    written = COMPLETION_OUT.exists()
    current = written and COMPLETION_OUT.read_text() == completion_script(commands())
    zshrc = Path.home() / '.zshrc'
    wired = zshrc.exists() and any(l.strip() == COMPLETION_MARKER
                                   for l in zshrc.read_text().splitlines())
    state = ('not written — `yoga completions sync`' if not written else
             'current' if current else 'STALE — `yoga completions sync`')
    print(f'completions: {tilde(COMPLETION_OUT)} — {state}')
    print(f'  ~/.zshrc: ' + ('wired' if wired else 'not wired — `yoga completions install`'))
    return 0


def _write_completion() -> None:
    COMPLETION_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMPLETION_OUT.write_text(completion_script(commands()))
    print(f'wrote {COMPLETION_OUT.relative_to(REPO)}')


def completion(rest: list[str]) -> int:
    if any(a in rest for a in ('-h', '--help')):
        # a help request is a question, never an action — and never the product
        print('yoga completions — zsh tab-completion derived from rsc/cli/commands.csv\n'
              '  (bare)      status: whether _yoga is written/current and wired into ~/.zshrc\n'
              '  sync        (re-)write cache/completions/_yoga from the table — idempotent\n'
              '  install     sync, then wire it into ~/.zshrc above compinit (idempotent)\n'
              '  uninstall   remove that block from ~/.zshrc (the exact inverse — no file left behind)')
        return 0
    verb = next((a for a in rest if not a.startswith('-')), None)
    if verb is None:
        return completion_status()                  # bare noun → status
    if verb == 'sync':
        _write_completion()
        print('→ wire it in: ./yoga completions install   (edits ~/.zshrc above compinit)')
        return 0
    if verb == 'install':
        _write_completion()
        return install_completion()
    if verb == 'uninstall':
        return uninstall_completion()
    print(f'yoga completions: unknown verb {verb!r} — sync | install | uninstall (bare: status)',
          file=sys.stderr)
    return 2


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


def usage_line(c: dict) -> str:
    """The tail every bare noun-status carries: the command's own usage, from the
    table. It names EVERY verb and flag that applies — so there is no need to guess
    a unique 'next' (a noun with several verbs has none), and it can never drift
    from the surface the honesty check already holds to `commands.csv`."""
    return f"usage: yoga {c['command']}" + (f" {c['usage']}" if c['usage'] else '')


def _run_status(row: dict) -> int:
    """Run a noun's bare (status) invocation as a CHILD, so the CLI can print the
    usage tail after it returns. Only ever reached for a read-only status — no verb,
    no args — so subprocess (not the execv dispatch uses) is safe: nothing here is
    interactive, and the child's exit code is forwarded."""
    target = REPO / row['target']
    if target.suffix == '.py':
        return subprocess.run([str(REPO / 'src' / 'run_python_script.sh'),
                               str(target)]).returncode
    return subprocess.run([str(target)]).returncode


def main() -> int:
    argv = sys.argv[1:]
    cmds = commands()
    if not argv:
        # bare `yoga` → the machine report: what still needs attention (failures-only;
        # `yoga prerequisites --show-all` for the full report). The root obeys the same
        # rule as every noun — bare shows status, -h shows help — and its status IS the
        # prerequisites report, so there is nothing to invent here.
        return dispatch(next(c for c in cmds if c['command'] == 'prerequisites'), [])
    if argv[0] in ('-h', '--help'):
        print(render_help(cmds), end='')      # help is the -h/--help flag, uniformly —
        return 0                              # not a bareword `help` the table never declared
    row = next((c for c in cmds if c['command'] == argv[0]), None)
    if row is None:
        print(f'yoga: unknown command {argv[0]!r} — the table:\n', file=sys.stderr)
        print(render_help(cmds), file=sys.stderr, end='')
        return 2
    rest = argv[1:]
    # command-level help (`yoga <cmd> -h`, no verb before the flag) → the uniform
    # standard help. A verb before it (`yoga <cmd> <verb> -h`) falls through to the
    # target, whose argparse carries that verb's own flags.
    if rest and rest[0] in ('-h', '--help'):
        print(render_command_help(row), end='')
        return 0
    if row['command'] == 'commands':
        name = next((a for a in rest if not a.startswith('-')), None)
        print(render_synopsis(cmds, name), end='')
        return 0
    if row['command'] == 'completions':
        rc = completion(rest)
        if not rest:                              # bare noun → tail with the usage
            print(usage_line(row))
        return rc
    # A bare noun (advertised verbs, no args) shows status, then tails with its usage
    # — the one tail that works everywhere, naming every verb that applies. Verbs
    # (check/run/supersede: no advertised verbs) act on a bare invocation, so they
    # keep the plain execv path and no tail.
    if not rest and verbs_of(row['usage']):
        rc = _run_status(row)
        print(usage_line(row))
        return rc
    return dispatch(row, rest)


if __name__ == '__main__':
    sys.exit(main())
