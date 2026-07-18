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
COLUMNS = ('command', 'target', 'calculus', 'step', 'summary')
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


_HELP_ROWS: list[dict] | None = None


def help_rows() -> list[dict]:
    """All rsc/cli/help.csv rows (columns command, subcommand, arg-name, arg-type,
    cardinality, help) — the SINGLE source for each command's verbs, flags, and the
    GENERATED usage. commands.csv holds no argument structure at all: usage is
    derived here, so the two can never drift and there is nothing to reconcile."""
    global _HELP_ROWS
    if _HELP_ROWS is None:
        with (REPO / 'rsc' / 'cli' / 'help.csv').open() as f:
            _HELP_ROWS = list(csv.DictReader(f))
    return _HELP_ROWS


def command_rows(command: str) -> list[dict]:
    return [r for r in help_rows() if r['command'] == command]


def verbs_of(command: str) -> list[str]:
    """A command's subcommand verbs — its distinct non-empty subcommands, in order."""
    out: list[str] = []
    for r in command_rows(command):
        if r['subcommand'] and r['subcommand'] not in out:
            out.append(r['subcommand'])
    return out


def flags_of(command: str) -> list[str]:
    """The --flags a command advertises, across all its subcommands, deduped in order."""
    out: list[str] = []
    for r in command_rows(command):
        if r['arg-name'].startswith('--') and r['arg-name'] not in out:
            out.append(r['arg-name'])
    return out


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


def _render_arg(name: str, arg_type: str) -> str:
    """One argument's usage fragment: a flag shows its name then its metavar; a
    positional shows its metavar (arg-type) alone."""
    if name.startswith('--'):
        return f'{name} {arg_type}' if arg_type else name
    return arg_type or name


def _render_args(rows: list[dict]) -> str:
    """The argument portion of a subcommand's usage, from its help.csv rows in order.
    cardinality is a literal count: blank -> optional [x]; a bare count '1' -> required,
    exactly that many x; 'N/<class>' -> N over the SET QUOTIENT <class> — the members
    share that value (one equivalence class) and render as the exclusive choice (a | b),
    emitted once at the first member."""
    pieces, seen = [], set()
    args = [r for r in rows if r['arg-name']]
    for r in args:
        card, frag = r['cardinality'], _render_arg(r['arg-name'], r['arg-type'])
        if not card:
            pieces.append(f'[{frag}]')
        elif '/' in card:
            if card in seen:
                continue
            seen.add(card)
            members = ' | '.join(_render_arg(a['arg-name'], a['arg-type'])
                                 for a in args if a['cardinality'] == card)
            pieces.append(f'({members})')
        else:  # a bare count -> required
            pieces.append(frag)
    return ' '.join(pieces)


def _by_subcommand(command: str) -> tuple[list[str], dict[str, list[dict]]]:
    """(ordered subcommands incl. '', {subcommand: rows}) for a command."""
    order: list[str] = []
    bysub: dict[str, list[dict]] = {}
    for r in command_rows(command):
        s = r['subcommand']
        if s not in bysub:
            bysub[s] = []
            order.append(s)
        bysub[s].append(r)
    return order, bysub


def _join(base: str, args: str) -> str:
    return f'{base} {args}' if args else base


def usage_of(command: str) -> str:
    """The compact usage sketch (subcommands ' | '-joined), GENERATED from help.csv —
    the string commands.csv used to store. One source now, so it cannot drift."""
    order, bysub = _by_subcommand(command)
    verbs = [s for s in order if s]
    if not verbs:
        return _render_args(bysub.get('', []))
    return ' | '.join(_join(s, _render_args(bysub[s])) for s in verbs)


def command_forms(command: str) -> list[str]:
    """`yoga <command> …` invocation forms, generated from help.csv: one per
    subcommand (with its own args), or a single form carrying the command-level args
    when there are no subcommands."""
    order, bysub = _by_subcommand(command)
    verbs = [s for s in order if s]
    base = f'yoga {command}'
    if not verbs:
        return [_join(base, _render_args(bysub.get('', [])))]
    return [_join(f'{base} {s}', _render_args(bysub[s])) for s in verbs]


def _forms(c: dict) -> list[str]:
    return command_forms(c['command'])


def render_command_help(c: dict) -> str:
    """The standard command help, shared by `yoga <cmd> -h` and `yoga commands
    <cmd>`: the summary, every invocation form, then each verb with its own args
    nested beneath it, command-level args flat. All generated from help.csv."""
    command = c['command']
    forms = ([f"yoga {command}   (status)"] if verbs_of(command) else []) + command_forms(command)
    out = [f"yoga {command} — {c['summary']}", '', *[f'  {f}' for f in forms]]
    order, bysub = _by_subcommand(command)
    argrows = [r for r in command_rows(command) if r['arg-name']]
    if not argrows:
        return '\n'.join(out) + '\n'
    label = {(r['subcommand'], r['arg-name']): _render_arg(r['arg-name'], r['arg-type'])
             for r in argrows}
    w = max(len(v) for v in label.values())
    out.append('')
    for s in order:
        desc = next((r['help'] for r in bysub[s] if not r['arg-name']), None)
        rows = [r for r in bysub[s] if r['arg-name']]
        if s:
            out.append(f"  {s}" + (f" — {desc}" if desc else ''))
            out += [f"      {label[(s, r['arg-name'])]:<{w}}  {r['help']}" for r in rows]
        else:
            out += [f"  {label[(s, r['arg-name'])]:<{w}}  {r['help']}" for r in rows]
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
          for c in cmds if (flags := flags_of(c['command']))],
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


def _sync_completion() -> None:
    """The `sync` operation: (re-)write cache/completions/_yoga from the table.
    `install` calls this before wiring, so it never wires a stale or absent file —
    install IS sync, then wire."""
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
        _sync_completion()
        print('→ wire it in: ./yoga completions install   (edits ~/.zshrc above compinit)')
        return 0
    if verb == 'install':
        _sync_completion()          # install IS sync, then wire
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
    """The tail every bare noun-status carries: the command's usage, GENERATED from
    help.csv. It names EVERY verb and flag that applies — so there is no need to
    guess a unique 'next' (a noun with several verbs has none)."""
    usage = usage_of(c['command'])
    return f"usage: yoga {c['command']}" + (f" {usage}" if usage else '')


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
    if not rest and verbs_of(row['command']):
        rc = _run_status(row)
        print(usage_line(row))
        return rc
    return dispatch(row, rest)


if __name__ == '__main__':
    sys.exit(main())
