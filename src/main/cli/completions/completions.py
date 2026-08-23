#!/usr/bin/env python
"""
completions.py (corpus-yoga completions) — the zsh tab-completion derived from src/main/cli/.

Its own file because a command determines its target's name (#40): `corpus-yoga completions` is
answered here, not by a branch inside the dispatcher. cli.py holds the declaration readers
and the renderers every command shares; what only this command needs lives here.

stdlib-only, like cli.py: the completion must be installable on a fresh clone before any
venv exists.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
SELF = 'src/main/cli/completions/completions.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))   # src/, for declared_parser
from declared_parser import command_parser  # noqa: E402
from cli import (  # noqa: E402 — one reader of the declaration, and it is cli
    PATH_ARG_TYPES, REPO, commands, command_rows, subcommands_of, _subcommand_desc,
)

COMPLETION_OUT = REPO / 'tmp' / 'cache' / 'completions' / '_yoga'


# The comments that DELIMIT the block `install` writes into ~/.zshrc, and by which
# `uninstall` finds it again. A start AND an end, so the block has an extent: uninstall
# removes everything between them, and a line added inside it later leaves with it
# without uninstall having to learn that line's shape. One pair of constants, so
# install and uninstall can never disagree about where the block begins or ends.
#
# IDENTITY is COMPLETION_ID alone, and it is matched as a PREFIX. The written marker
# carries advice after it, and advice is editable: when `./corpus-yoga` became bare `corpus-yoga`,
# equality on the whole line stopped recognising every block the earlier version had
# written — so install could not converge on it (it inserted a second block beside it),
# uninstall could not remove it, and status reported "not wired" about a shell that was.
# A token that doubles as documentation cannot serve as identity when the documentation
# is the part that changes.
COMPLETION_ID = '# corpus-yoga tab-completion'
# Every id this command has EVER written into ~/.zshrc (G20: the installed token must
# stay recognisable) - a rename of the CLI word adds the former id here, or install
# cannot find that vintage's block and a dangling alias survives every re-run.
COMPLETION_FORMER_IDS = ('# yoga tab-completion',)
COMPLETION_MARKER = f'{COMPLETION_ID} (refresh: corpus-yoga completions install-latest)'
COMPLETION_END = '# end corpus-yoga tab-completion'
COMPLETION_ENDS = tuple(f'# end {i.removeprefix("# ")}'
                        for i in (COMPLETION_ID, *COMPLETION_FORMER_IDS))


def is_completion_marker(line: str) -> bool:
    """Does this line open a corpus-yoga block? — the one recogniser install, uninstall and
    status share, so they cannot disagree about what is already there. Prefix, not
    equality: everything after COMPLETION_ID is advice to the reader, not identity.
    COMPLETION_END is excluded because it starts with '# end'."""
    return line.strip().startswith((COMPLETION_ID, *COMPLETION_FORMER_IDS))


def _scoped_flags(command: str, subcommand: str) -> tuple[list[str], list[str]]:
    """(flags, path-flags) for ONE scope of a command: a verb's own rows, or the
    command-level rows (subcommand ''). The completion offers exactly these at
    that position — never the across-verbs union, which TAB-completed flags the
    dispatched verb then rejects (found 2026-07-23: `cache sync --apply` was
    offered, and dies in sync's argparse; --apply is clean's)."""
    rows = [r for r in command_rows(command) if r['subcommand'] == subcommand]
    flags, paths = [], []
    for r in rows:
        f = r['arg-name']
        if f.startswith('--') and f not in flags:
            flags.append(f)
            if r['arg-type'] in PATH_ARG_TYPES:
                paths.append(f)
    return flags, paths


def _takes_command_name(command: str) -> bool:
    """True where a positional names another command (`corpus-yoga commands <command>`), so
    that position can complete the command list rather than nothing."""
    return any(r['arg-name'] and not r['arg-name'].startswith('--')
               and r['arg-type'] == '<command>' for r in command_rows(command))


def completion_script(cmds: list[dict]) -> str:
    """A static zsh completion function derived from the tables (regenerate via
    `corpus-yoga completions`; never edit the emitted file). Each position offers only what
    applies there: the command word, then that command's subcommands, then its flags
    after a '-'. A FILE list is offered only as the value of a flag that takes a path;
    where nothing takes an argument, nothing is offered — a stray listing of the
    working directory is noise pretending to be help."""
    def esc(s: str) -> str:
        return (s.replace('\\', '\\\\').replace("'", "'\\''").replace(':', '\\:'))

    def scope_parts(flags: list[str], paths: list[str]) -> str:
        parts = []
        if flags:
            parts.append(f"opts=({' '.join(flags)})")
        if paths:
            parts.append(f"pathopts=({' '.join(paths)})")
        return '; '.join(parts)

    def arm(command: str) -> str | None:
        parts = []
        subcommands = subcommands_of(command)
        if subcommands:
            slist = ' '.join(f"'{esc(s)}:{esc(_subcommand_desc(command, s))}'" for s in subcommands)
            parts.append(f'subcommands=({slist})')
        cmd_flags, cmd_paths = _scoped_flags(command, '')
        verb_scopes = {s: _scoped_flags(command, s) for s in subcommands}
        if any(f for f, _ in verb_scopes.values()):
            # Flags are scoped to their verb (src/main/cli/README.md): offer each
            # verb ONLY its own rows' flags — the across-verbs union completed
            # flags the dispatched verb rejects. The *) scope is pre-verb: the
            # command-level rows, which argparse accepts only BEFORE the verb.
            inner = [f"      case \"${{words[3]}}\" in"]
            for s in subcommands:
                f, p = verb_scopes[s]
                inner.append(f'        {s}) {scope_parts(f, p)} ;;' if f
                             else f'        {s}) ;;')
            inner.append(f'        *) {scope_parts(cmd_flags, cmd_paths)} ;;'
                         if cmd_flags else '        *) ;;')
            inner.append('      esac')
            body = '; '.join(parts)
            tail = ' wantcmd=1;' if _takes_command_name(command) else ''
            return f"    {command}) {body}\n" + '\n'.join(inner) + f'\n     {tail} ;;'
        if cmd_flags:
            parts.append(scope_parts(cmd_flags, cmd_paths))
        if _takes_command_name(command):
            parts.append('wantcmd=1')
        return f"    {command}) {'; '.join(parts)} ;;" if parts else None

    lines = [
        '#compdef corpus-yoga',
        '# derived from src/main/cli/ by `corpus-yoga completions` — regenerate, never edit',
        '',
        '_yoga() {',
        '  local -a cmds subcommands opts pathopts',
        '  local wantcmd=0',
        '  cmds=(',
        *[f"    '{esc(c['command'])}:{esc(c['summary'])}'" for c in cmds],
        '  )',
        '  if (( CURRENT == 2 )); then',
        "    _describe -t commands 'corpus-yoga command' cmds",
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
    """~/.zshrc's lines with the corpus-yoga block gone; returns (kept, how many removed).

    Reads a list and returns a new one; nothing is written here. Uninstall keeps the
    result, install uses it to converge on one current block.

    The block is delimited (marker … end marker) and goes wholesale, so this never
    needs to know what is inside it. A block is recognised by is_completion_marker,
    so blocks written by earlier versions — whose marker carried different advice —
    are found too. Anything else is not a block here and is left untouched.
    One adjacent blank (install leaves one on a side) goes with it.

    EVERY block goes, not the first. Removing one and writing one is not convergence
    if two exist: whichever install did not recognise survived every re-run, and the
    surviving fpath entry went on shadowing the current one."""
    kept, removed = list(lines), 0
    while True:
        start = next((i for i, l in enumerate(kept) if is_completion_marker(l)), None)
        if start is None:
            return kept, removed
        end = next((i for i in range(start + 1, len(kept))
                    if kept[i].strip() in COMPLETION_ENDS), None)
        if end is None:
            return kept, removed
        first, last = start, end
        if last + 1 < len(kept) and kept[last + 1].strip() == '':
            last += 1
        elif first > 0 and kept[first - 1].strip() == '':
            first -= 1
        removed += last - first + 1
        kept = kept[:first] + kept[last + 1:]


def install_completion() -> int:
    """Wire tmp/cache/completions into ~/.zshrc — idempotently, and ABOVE compinit.

    Position is the whole difficulty, which is why this is a command and not
    printed advice: zsh scans fpath when compinit RUNS, so a line added after it
    silently does nothing. That is the mistake the old printed lines invited (the
    obvious move is to append), and a grep for the string could not tell it from
    success. We insert above the first fpath=/compinit line, first backing up over
    its comment header so we land OUTSIDE a managed block — Docker Desktop rewrites
    its own block and would eat a line placed inside it.

    The `corpus-yoga` alias is written INTO the block for the same reason the fpath line is:
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
    alias_line = f"alias corpus-yoga='{tilde(REPO / 'corpus-yoga')}'"
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
        print('  remove anytime: corpus-yoga completions uninstall')
    # ~/.zcompdump is compinit's cache of which completion functions exist, and
    # its staleness heuristic can judge a pre-install dump current — the first
    # new terminal then falls back to filename completion while every LATER one
    # works — the dump is rebuilt by some shell after the one the user opened to
    # test it. Deleting the dump makes the restart the line below prescribes sufficient,
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
    """Removes the delimited corpus-yoga block from ~/.zshrc,
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
        print(f'{tilde(zshrc)}: no corpus-yoga block found — nothing to remove')
        return 0
    zshrc.write_text('\n'.join(kept) + '\n')
    print(f'{tilde(zshrc)}: removed the corpus-yoga block ({removed_line_count} lines) — nothing else touched')
    print('→ start a new shell (exec zsh) for it to take effect')
    return 0


def completion_status() -> int:
    """The bare-noun default: show current state, write nothing. Whether the _yoga
    file is written (and current with the table) and whether ~/.zshrc is wired."""
    written = COMPLETION_OUT.exists()
    current = written and COMPLETION_OUT.read_text() == completion_script(commands())
    zshrc = Path.home() / '.zshrc'
    # the same recogniser install and uninstall use, so status cannot report "not
    # wired" about a block those two can see (or would refuse to see)
    blocks = sum(1 for l in (zshrc.read_text().splitlines() if zshrc.exists() else [])
                 if is_completion_marker(l))
    state = ('not written — `./corpus-yoga completions install-latest`' if not written else
             'current' if current else 'STALE — `./corpus-yoga completions install-latest`')
    print(f'completions: {tilde(COMPLETION_OUT)} — {state}')
    # A count, not a yes/no: two blocks is a state the file can reach and the reader
    # cannot see from here, and the second one's fpath entry shadows the first.
    print('  ~/.zshrc: ' + ('not wired — `./corpus-yoga completions install-latest`' if not blocks
                            else 'wired' if blocks == 1
                            else f'wired {blocks} times — `./corpus-yoga completions install-latest` '
                                 f'removes every block and writes one'))
    return 0


def _sync_completion() -> None:
    """The `sync` operation: (re-)write tmp/cache/completions/_yoga from the table.
    `install` calls this before wiring, so it never wires a stale or absent file —
    install IS sync, then wire."""
    COMPLETION_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMPLETION_OUT.write_text(completion_script(commands()))
    print(f'wrote {COMPLETION_OUT.relative_to(REPO)}')


def completion(rest: list[str]) -> int:
    """`corpus-yoga completions` — bare shows status, each subcommand acts.

    The parser is generated from the declaration (#476): the pattern every
    other command's target already follows. That cli.py handles this command itself
    instead of exec'ing a target is no reason to hand-roll the dispatch and a second
    copy of the help — that copy is how the text came to disagree with the table
    about install-latest. A parser cannot advertise a subcommand it does not
    dispatch, and -h is argparse's own business at every level, so it can never fall
    through and RUN the subcommand it was asked to describe. Command-level -h never
    reaches here: main() renders it from the table, uniformly for every command."""
    args = command_parser('completions', dest='subcommand').parse_args(rest)
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


if __name__ == '__main__':
    raise SystemExit(completion(sys.argv[1:]))
