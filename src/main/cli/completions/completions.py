#!/usr/bin/env python
"""
completions.py (corpus-yoga completions) — whether zsh completes `corpus-yoga`, and the lines
in ~/.zshrc that make it. What tab offers is src/main/cli/completions/offer.py's, asked by
src/main/cli/completions/offer.zsh each time tab is pressed; src/main/cli/completions/_corpus-yoga
is the file zsh loads, and only sources that.

Its own file because a command determines its target's name (#40): `corpus-yoga completions` is
answered here, not by a branch inside the dispatcher. cli.py holds the declaration readers
and the renderers every command shares; what only this command needs lives here.

stdlib-only, like cli.py: the completion must be installable on a fresh clone before any
venv exists.
"""
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
SELF = 'src/main/cli/completions/completions.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))   # src/, for declared_parser
from declared_parser import command_parser  # noqa: E402
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))   # src/main/, for send
import facts  # noqa: E402 - the one printer of a status's facts (#753)
from send import SendRefused, assert_may_send  # noqa: E402 — ~/.zshrc is outside the tree: a send (#29)
from cli import REPO  # noqa: E402

# The directory ~/.zshrc puts on zsh's fpath: it holds _corpus-yoga, the one file zsh loads.
COMPLETION_HOME = REPO / 'src' / 'main' / 'cli' / 'completions'
LAUNCHER = REPO / 'corpus-yoga'


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
COMPLETION_MARKER = f'{COMPLETION_ID} - corpus-yoga completions uninstall removes these lines'
COMPLETION_END = '# end corpus-yoga tab-completion'
COMPLETION_ENDS = tuple(f'# end {i.removeprefix("# ")}'
                        for i in (COMPLETION_ID, *COMPLETION_FORMER_IDS))


def is_completion_marker(line: str) -> bool:
    """Does this line open a corpus-yoga block? — the one recogniser install, uninstall and
    status share, so they cannot disagree about what is already there. Prefix, not
    equality: everything after COMPLETION_ID is advice to the reader, not identity.
    COMPLETION_END is excluded because it starts with '# end'."""
    return line.strip().startswith((COMPLETION_ID, *COMPLETION_FORMER_IDS))


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


def block() -> list[str]:
    """The lines `install` writes into ~/.zshrc for this copy of corpus-yoga."""
    return [COMPLETION_MARKER, f'fpath=({tilde(COMPLETION_HOME)} $fpath)',
            f"alias corpus-yoga='{tilde(LAUNCHER)}'", COMPLETION_END]


def blocks_of(lines: list[str]) -> list[list[str]]:
    """Each corpus-yoga block the lines hold, without its two markers."""
    found, at = [], 0
    while (start := next((i for i in range(at, len(lines)) if is_completion_marker(lines[i])), None)) is not None:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() in COMPLETION_ENDS), None)
        if end is None:
            break
        found.append([line.strip() for line in lines[start + 1:end] if line.strip()])
        at = end + 1
    return found


def install_completion() -> int:
    """Writes this copy's block into ~/.zshrc, above compinit.

    zsh scans fpath when compinit RUNS, so a line added after it does nothing: the block
    goes above the first fpath=/compinit line, and above that line's comment header, so
    that it lands outside a block another tool manages and rewrites.

    Every block already there is removed and one written, so two blocks, a block for
    another copy and a block an earlier corpus-yoga wrote all converge on this one. The
    file is written only where that changes it.
    """
    zshrc = Path.home() / '.zshrc'
    before = zshrc.read_text() if zshrc.exists() else ''
    lines, _ = without_yoga_block(before.splitlines())
    idx = next((i for i, l in enumerate(lines)
                if re.match(r'\s*(compinit\b|fpath=)', l)), None)
    if idx is None:
        lines += ['', *block(), 'autoload -Uz compinit', 'compinit']
        where = 'added at the end, with a compinit of their own (this ~/.zshrc had none)'
    else:
        while idx > 0 and lines[idx - 1].lstrip().startswith('#'):
            idx -= 1                      # step above the block's comment header
        lines[idx:idx] = [*block(), '']
        where = f'added at line {idx + 1}, above compinit'
    text = '\n'.join(lines) + '\n'
    if text == before and loads() is not False:
        print(f'{tilde(zshrc)}: tab-completion is already set up - nothing written')
        return 0
    if text == before:
        print(f'{tilde(zshrc)}: the four lines stand as they should, and zsh does not load them')
    else:
        try:
            assert_may_send('write ~/.zshrc (completions install)')
        except SendRefused as refused:
            print(f'completions install: NOT DONE - {refused}')
            return 1
        zshrc.write_text(text)
        print(f'{tilde(zshrc)}: four lines {where}')
        for line in block():
            print(f'    {line}')
    # compinit keeps the list of completion files it found in ~/.zcompdump and can judge
    # a list made before these lines current; the next terminal would then not complete.
    dumps = sorted(Path.home().glob('.zcompdump*'))
    for d in dumps:
        d.unlink()
    if dumps:
        print(f'  ~/.zcompdump*: {len(dumps)} removed - the next terminal rebuilds it')
    print('open a new terminal for tab to complete corpus-yoga')
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
        print(f'{tilde(zshrc)}: no corpus-yoga lines found - nothing to remove')
        return 0
    try:
        assert_may_send('write ~/.zshrc (completions uninstall)')
    except SendRefused as refused:
        print(f'completions uninstall: NOT DONE - {refused}')
        return 1
    zshrc.write_text('\n'.join(kept) + '\n')
    print(f'{tilde(zshrc)}: removed the corpus-yoga lines ({removed_line_count}) - nothing else touched')
    print('open a new terminal for it to take effect')
    return 0


@dataclass
class Completions:
    standing: str = facts.named('tab-completion')
    remedy: facts.Command | None = None


@dataclass
class Status:
    completions: Completions


def loads() -> bool | None:
    """Whether an interactive zsh has a completion for corpus-yoga, asked of zsh: a line
    in ~/.zshrc below compinit stands there and does nothing, so the file's text is not
    the fact. None where there is no zsh."""
    import shutil
    import subprocess
    if shutil.which('zsh') is None:
        return None
    asked = subprocess.run(['zsh', '-ic', 'print -r -- ${+_comps[corpus-yoga]}'], capture_output=True, text=True)
    return (asked.stdout.strip().splitlines() or [''])[-1] == '1'


# ./corpus-yoga in the remedy: the bare word is the alias the block binds to one copy,
# and where a remedy is owed it is unbound or bound to another copy (#514).
INSTALL = './corpus-yoga completions install'


def standing() -> Completions:
    """Whether tab completes corpus-yoga in zsh from this copy, and the remedy where not."""
    zshrc = Path.home() / '.zshrc'
    found = blocks_of(zshrc.read_text().splitlines() if zshrc.exists() else [])
    loaded = loads()
    if loaded is None:
        return Completions('not applicable - this machine has no zsh')
    if not found:
        return Completions('not set up in zsh',
                           facts.Command(INSTALL, 'adds four lines to ~/.zshrc; open a new terminal afterwards'))
    if found == [block()[1:-1]]:
        return Completions('set up') if loaded else Completions(
            'written in ~/.zshrc, but zsh does not load it',
            facts.Command(INSTALL, 'puts its lines where zsh reads them; open a new terminal afterwards'))
    aliased = [match.group(1) for lines in found for line in lines
               if (match := re.fullmatch(r"alias corpus-yoga='(.*)'", line))]
    other = next((Path(a).expanduser() for a in aliased if Path(a).expanduser() != LAUNCHER), None)
    if other is None:
        return Completions('set up, but not as corpus-yoga completions install sets it up',
                           facts.Command(INSTALL, 'rewrites its lines in ~/.zshrc; open a new terminal afterwards'))
    return Completions(f'set up for a different copy of corpus-yoga, at {tilde(other.parent)}' if other.exists()
                       else f'set up for a copy of corpus-yoga that is gone, at {tilde(other.parent)}',
                       facts.Command(INSTALL, 'points ~/.zshrc at this copy; open a new terminal afterwards'))


def completion_status() -> int:
    facts.say(Status(standing()))
    return 0


def completion(rest: list[str]) -> int:
    """`corpus-yoga completions` — bare shows status, each subcommand acts.

    The parser is generated from the declaration (#476): the pattern every
    other command's target already follows. That cli.py handles this command itself
    instead of exec'ing a target is no reason to hand-roll the dispatch and a second
    copy of the help — that copy is how the text came to disagree with the table. A parser cannot advertise a subcommand it does not
    dispatch, and -h is argparse's own business at every level, so it can never fall
    through and RUN the subcommand it was asked to describe. Command-level -h never
    reaches here: main() renders it from the table, uniformly for every command."""
    args = command_parser('completions', dest='subcommand').parse_args(rest)
    if args.subcommand is None:
        return completion_status()                  # bare noun → status
    if args.subcommand == 'install':
        return install_completion()
    assert args.subcommand == 'uninstall', args.subcommand   # argparse allows nothing else
    return uninstall_completion()


if __name__ == '__main__':
    raise SystemExit(completion(sys.argv[1:]))
