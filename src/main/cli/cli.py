#!/usr/bin/env python
"""
cli.py — the machinery behind `./yoga`, the repo's terminal surface.

Two curated tables are the interface (format: rsc/cli/README.md): rsc/cli/commands.csv
names each command and its target; rsc/cli/help.csv describes the arguments.
`./yoga <command> [args...]` execs the row's target with the args forwarded verbatim.
`./yoga -h` lists the commands; `./yoga <command> -h` renders that command's help from
the tables; a subcommand one level down (`./yoga <command> <subcommand> --help`) is
answered by argparse — the target's own, or the parser cli.py builds for a command it
handles itself. `./yoga completions` derives static zsh tab-completion from
the tables. Presentation is re-derived on every invocation and stored nowhere (L5);
the CLI adds no behaviour of its own.

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
    ./yoga completions install-latest  # regenerate the zsh tab-completion and wire it
    ./yoga commands              # every command's syntax: a SYNOPSIS derived from the table

This module is deliberately STDLIB-ONLY: the ./yoga launcher falls back to
system python3 when the venv does not exist yet, so a fresh clone can render
the table, print the calculus, and generate completion before ./RUNME.sh has
run. Adding a third-party import here would silently break that.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from argparse_help import enrich  # noqa: E402 — stdlib-only itself, so the bootstrap holds

REPO = Path(__file__).resolve().parents[3]
TABLE = REPO / 'rsc' / 'cli' / 'commands.csv'
COLUMNS = ('command', 'target', 'calculus', 'summary')
COMPLETION_OUT = REPO / 'cache' / 'completions' / '_yoga'
# The comments that DELIMIT the block `install` writes into ~/.zshrc, and by which
# `uninstall` finds it again. A start AND an end, so the block has an extent: uninstall
# removes everything between them, and a line added inside it later leaves with it
# without uninstall having to learn that line's shape. One pair of constants, so
# install and uninstall can never disagree about where the block begins or ends.
COMPLETION_MARKER = '# yoga tab-completion (refresh: ./yoga completions install-latest)'
COMPLETION_END = '# end yoga tab-completion'


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
    cardinality, help) — the SINGLE source for each command's subcommands, flags, and the
    GENERATED usage. commands.csv holds no argument structure at all: usage is
    derived here, so the two can never drift and there is nothing to reconcile."""
    global _HELP_ROWS
    if _HELP_ROWS is None:
        with (REPO / 'rsc' / 'cli' / 'help.csv').open() as f:
            _HELP_ROWS = list(csv.DictReader(f))
    return _HELP_ROWS


def command_rows(command: str) -> list[dict]:
    return [r for r in help_rows() if r['command'] == command]


def subcommands_of(command: str) -> list[str]:
    """A command's distinct non-empty subcommands, in order."""
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


def steps() -> list[dict]:
    """The (command, subcommand) invocations the run pipeline executes as named plan
    steps, declared by help.csv's `step` column (its value names the pipeline). The gate
    holds `RUNME.sh --plan` to these: each must appear as a plan line naming the command
    AND its verb — so the plan speaks the command surface, and a step can never invoke a
    noun bare, which would silently become a status no-op."""
    return [{'command': r['command'], 'subcommand': r['subcommand'], 'pipeline': r['step']}
            for r in help_rows() if r.get('step')]


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
    subcommands = [s for s in order if s]
    if not subcommands:
        return _render_args(bysub.get('', []))
    return ' | '.join(_join(s, _render_args(bysub[s])) for s in subcommands)


def command_forms(command: str) -> list[str]:
    """`yoga <command> …` invocation forms, generated from help.csv: one per
    subcommand (with its own args), or a single form carrying the command-level args
    when there are no subcommands."""
    order, bysub = _by_subcommand(command)
    subcommands = [s for s in order if s]
    base = f'yoga {command}'
    if not subcommands:
        return [_join(base, _render_args(bysub.get('', [])))]
    return [_join(f'{base} {s}', _render_args(bysub[s])) for s in subcommands]


def _forms(c: dict) -> list[str]:
    return command_forms(c['command'])


def render_command_help(c: dict) -> str:
    """The standard command help, shared by `yoga <cmd> -h` and `yoga commands
    <cmd>`: the summary, every invocation form, then each subcommand with its own args
    nested beneath it, command-level args flat. All generated from help.csv."""
    command = c['command']
    forms = ([f"yoga {command}   (status)"] if subcommands_of(command) else []) + command_forms(command)
    out = [f"yoga {command} — {c['summary']}", '', *[f'  {f}' for f in forms]]
    order, bysub = _by_subcommand(command)
    argrows = [r for r in command_rows(command) if r['arg-name']]
    descs = {s: next((r['help'] for r in bysub[s] if not r['arg-name']), None) for s in order}
    # A subcommand's DESCRIPTION is worth printing even when it takes no arguments:
    # for `completions install-latest`, `xref check` or `memories sync`, that line is
    # the only place -h says what the subcommand does. Returning early on "no arg rows"
    # dropped it silently — and dropped it for more commands each time an argument was
    # removed, which is how memories and xref lost theirs.
    if not argrows and not any(s and descs[s] for s in order):
        return '\n'.join(out) + '\n'
    label = {(r['subcommand'], r['arg-name']): _render_arg(r['arg-name'], r['arg-type'])
             for r in argrows}
    w = max((len(v) for v in label.values()), default=0)
    out.append('')
    for s in order:
        rows = [r for r in bysub[s] if r['arg-name']]
        if s:
            out.append(f"  {s}" + (f" — {descs[s]}" if descs[s] else ''))
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


def _subcommand_desc(command: str, subcommand: str) -> str:
    """A subcommand's one-line description — its blank-arg-name row in help.csv."""
    return next((r['help'] for r in command_rows(command)
                 if r['subcommand'] == subcommand and not r['arg-name']), '')


# The arg-types whose value IS a filesystem path — the only values file completion
# suits. Matched exactly against help.csv's arg-type, never by substring: a metavar
# is a name, and reading meaning from its spelling would make <redirect> a directory.
# An arg-type absent here simply gets no completion, which is the safe way to be wrong.
PATH_ARG_TYPES = {'<dir>', '<path>', '<file>', '<scratch-dir>', '<machine|dir>'}


def _path_flags(command: str) -> list[str]:
    """The flags whose value is a filesystem path. A uuid8, a concept, an enum or a
    number is not a file, so file completion has no business at those positions."""
    typed = {r['arg-name'] for r in command_rows(command)
             if r['arg-type'] in PATH_ARG_TYPES}
    return [f for f in flags_of(command) if f in typed]


def _takes_command_name(command: str) -> bool:
    """True where a positional names another command (`yoga commands <command>`), so
    that position can complete the command list rather than nothing."""
    return any(r['arg-name'] and not r['arg-name'].startswith('--')
               and r['arg-type'] == '<command>' for r in command_rows(command))


def completion_script(cmds: list[dict]) -> str:
    """A static zsh completion function derived from the tables (regenerate via
    `./yoga completions`; never edit the emitted file). Each position offers only what
    applies there: the command word, then that command's subcommands, then its flags
    after a '-'. A FILE list is offered only as the value of a flag that takes a path;
    where nothing takes an argument, nothing is offered — a stray listing of the
    working directory is noise pretending to be help."""
    def esc(s: str) -> str:
        return (s.replace('\\', '\\\\').replace("'", "'\\''").replace(':', '\\:'))

    def arm(command: str) -> str | None:
        parts = []
        if subcommands := subcommands_of(command):
            slist = ' '.join(f"'{esc(s)}:{esc(_subcommand_desc(command, s))}'" for s in subcommands)
            parts.append(f'subcommands=({slist})')
        if flags := flags_of(command):
            parts.append(f"opts=({' '.join(flags)})")
        if paths := _path_flags(command):
            parts.append(f"pathopts=({' '.join(paths)})")
        if _takes_command_name(command):
            parts.append('wantcmd=1')
        return f"    {command}) {'; '.join(parts)} ;;" if parts else None

    lines = [
        '#compdef yoga',
        '# derived from rsc/cli/commands.csv + help.csv by `./yoga completions` — regenerate, never edit',
        '',
        '_yoga() {',
        '  local -a cmds subcommands opts pathopts',
        '  local wantcmd=0',
        '  cmds=(',
        *[f"    '{esc(c['command'])}:{esc(c['summary'])}'" for c in cmds],
        '  )',
        '  if (( CURRENT == 2 )); then',
        "    _describe -t commands 'yoga command' cmds",
        '    return',
        '  fi',
        '  case "${words[2]}" in',
        *[a for c in cmds if (a := arm(c['command']))],
        '  esac',
        '  # A file completes ONLY as the value of a flag that takes a path.',
        '  if (( ${#pathopts} )) && (( ${pathopts[(I)${words[CURRENT-1]}]} )); then',
        '    _files',
        '    return',
        '  fi',
        '  if [[ ${words[CURRENT]} == -* ]]; then',
        '    (( ${#opts} )) && compadd -- "${opts[@]}"',
        '    return',
        '  fi',
        '  if (( CURRENT == 3 )) && (( ${#subcommands} )); then',
        "    _describe -t subcommands 'subcommand' subcommands",
        '    return',
        '  fi',
        '  if (( wantcmd )); then',
        "    _describe -t commands 'command' cmds",
        '    return',
        '  fi',
        '  # Nothing here takes an argument — offer nothing, not a stray file list.',
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


def without_yoga_block(lines: list[str]) -> tuple[list[str], int]:
    """~/.zshrc's lines with the yoga block gone; returns (kept, how many removed).

    Reads a list and returns a new one; nothing is written here. Uninstall keeps the
    result, install uses it to converge on one current block.

    The block is delimited (marker … end marker) and goes wholesale, so this never
    needs to know what is inside it. Only COMPLETION_MARKER is recognised: a block
    carrying any other marker, or none, is not a block here and is left untouched.
    One adjacent blank (install leaves one on a side) goes with it."""
    start = next((i for i, l in enumerate(lines) if l.strip() == COMPLETION_MARKER), None)
    if start is None:
        return lines, 0
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() == COMPLETION_END), None)
    if end is None:
        return lines, 0
    first, last = start, end
    if last + 1 < len(lines) and lines[last + 1].strip() == '':
        last += 1
    elif first > 0 and lines[first - 1].strip() == '':
        first -= 1
    return lines[:first] + lines[last + 1:], last - first + 1


def install_completion() -> int:
    """Wire cache/completions into ~/.zshrc — idempotently, and ABOVE compinit.

    Position is the whole difficulty, which is why this is a command and not
    printed advice: zsh scans fpath when compinit RUNS, so a line added after it
    silently does nothing. That is the mistake the old printed lines invited (the
    obvious move is to append), and a grep for the string could not tell it from
    success. We insert above the first fpath=/compinit line, first backing up over
    its comment header so we land OUTSIDE a managed block — Docker Desktop rewrites
    its own block and would eat a line placed inside it.

    The `yoga` alias is written INTO the block for the same reason the fpath line is:
    printed advice does not survive a shell restart, because nothing ever persisted
    it. That was this function's own first mistake, fixed for the fpath line and left
    standing for the alias until someone noticed the alias kept vanishing.

    Idempotence is by CONVERGENCE, not by bailing out: any existing block is removed
    and the current one written, so a re-run repairs a stale block rather than
    reporting "already wired" and leaving it wrong. The file is rewritten only when
    that actually changes it.
    """
    zshrc = Path.home() / '.zshrc'
    fpath_line = f'fpath=({tilde(COMPLETION_OUT.parent)} $fpath)'
    alias_line = f"alias yoga='{tilde(REPO / 'yoga')}'"
    block = [COMPLETION_MARKER, fpath_line, alias_line, COMPLETION_END]
    before = zshrc.read_text() if zshrc.exists() else ''
    lines, _ = without_yoga_block(before.splitlines())
    idx = next((i for i, l in enumerate(lines)
                if re.match(r'\s*(compinit\b|fpath=)', l)), None)
    if idx is None:
        lines += ['', *block, 'autoload -Uz compinit', 'compinit']
        where = 'appended, with its own compinit (this ~/.zshrc had none)'
    else:
        while idx > 0 and lines[idx - 1].lstrip().startswith('#'):
            idx -= 1                      # step above the block's comment header
        lines[idx:idx] = [*block, '']
        where = f'inserted at line {idx + 1}, above compinit'
    # No backup is written. The block is delimited (COMPLETION_MARKER … COMPLETION_END)
    # and positioned, so uninstall is better
    # than a whole-file copy the user would have to remember to delete. Nothing lands
    # outside ~/.zshrc itself.
    text = '\n'.join(lines) + '\n'
    if text == before:
        print(f'{tilde(zshrc)}: already wired — nothing to do')
    else:
        zshrc.write_text(text)
        print(f'{tilde(zshrc)}: {where}')
        for line in block[1:-1]:
            print(f'    {line}')
        print('  remove anytime: ./yoga completions uninstall')
    # ~/.zcompdump is compinit's cache of which completion functions exist, and
    # its staleness heuristic can judge a pre-install dump current — the first
    # new terminal then falls back to filename completion while every LATER one
    # works (observed 2026-07-22, home-room: _yoga written 09:43:56, the first
    # fresh terminal stale, the dump only rebuilt at 09:46:34 by a later shell).
    # Deleting the dump makes the restart the line below prescribes sufficient,
    # not merely necessary. Runs even when the block was already wired: the
    # freshly regenerated _yoga is exactly what a kept dump would not know.
    dumps = sorted(Path.home().glob('.zcompdump*'))
    for d in dumps:
        d.unlink()
    if dumps:
        print(f'  ~/.zcompdump*: {len(dumps)} removed — the next shell\'s compinit rebuilds it')
    print('→ now start a new shell (exec zsh)')
    return 0


def uninstall_completion() -> int:
    """Removes the delimited yoga block from ~/.zshrc,
    leaving everything else byte-identical. Because the block has an END, its whole
    extent goes — fpath line, alias, and anything added between them — without this
    function needing to know what any of those lines are; both directions share
    without_yoga_block, so they cannot drift apart. A compinit that install added to a
    ~/.zshrc which had none is deliberately LEFT (it sits outside the block): it is
    generic zsh a later config may now rely on, and an idle compinit harms nothing;
    removing it could break what was built on top."""
    zshrc = Path.home() / '.zshrc'
    if not zshrc.exists():
        print(f'{tilde(zshrc)}: no such file — nothing to remove')
        return 0
    kept, removed_line_count = without_yoga_block(zshrc.read_text().splitlines())
    if not removed_line_count:
        print(f'{tilde(zshrc)}: no yoga block found — nothing to remove')
        return 0
    zshrc.write_text('\n'.join(kept) + '\n')
    print(f'{tilde(zshrc)}: removed the yoga block ({removed_line_count} lines) — nothing else touched')
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
    state = ('not written — `yoga completions install-latest`' if not written else
             'current' if current else 'STALE — `yoga completions install-latest`')
    print(f'completions: {tilde(COMPLETION_OUT)} — {state}')
    print('  ~/.zshrc: ' + ('wired' if wired
                            else 'not wired — `yoga completions install-latest`'))
    return 0


def _sync_completion() -> None:
    """The `sync` operation: (re-)write cache/completions/_yoga from the table.
    `install` calls this before wiring, so it never wires a stale or absent file —
    install IS sync, then wire."""
    COMPLETION_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMPLETION_OUT.write_text(completion_script(commands()))
    print(f'wrote {COMPLETION_OUT.relative_to(REPO)}')


def completion(rest: list[str]) -> int:
    """`yoga completions` — bare shows status, each subcommand acts.

    argparse owns the structure, help.csv the wording (enrich): the pattern every
    other command's target already follows. That cli.py handles this command itself
    instead of exec'ing a target is no reason to hand-roll the dispatch and a second
    copy of the help — that copy is how the text came to disagree with the table
    about install-latest. A parser cannot advertise a subcommand it does not
    dispatch, and -h is argparse's own business at every level, so it can never fall
    through and RUN the subcommand it was asked to describe. Command-level -h never
    reaches here: main() renders it from the table, uniformly for every command."""
    parser = argparse.ArgumentParser(          # prog is enrich's, for every command alike
        description=next(c['summary'] for c in commands() if c['command'] == 'completions'))
    subs = parser.add_subparsers(dest='subcommand', metavar='<subcommand>')
    for s in subcommands_of('completions'):
        subs.add_parser(s)
    enrich(parser, 'completions')
    args = parser.parse_args(rest)
    if args.subcommand is None:
        return completion_status()                  # bare noun → status
    if args.subcommand == 'sync':
        _sync_completion()          # the registry's producer: writes the file, wires nothing
        return 0
    if args.subcommand == 'install-latest':
        _sync_completion()          # install-latest IS sync, then wire
        return install_completion()
    assert args.subcommand == 'uninstall', args.subcommand   # argparse allows nothing else
    return uninstall_completion()


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
    # command-level help (`yoga <cmd> -h`, no subcommand before the flag) → the uniform
    # standard help. A subcommand before it (`yoga <cmd> <sub> -h`) falls through to
    # argparse, which carries that subcommand's own flags: the target's parser, or the
    # one cli.py builds for a command it handles itself.
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
    if not rest and subcommands_of(row['command']):
        rc = _run_status(row)
        print(usage_line(row))
        return rc
    return dispatch(row, rest)


if __name__ == '__main__':
    sys.exit(main())
