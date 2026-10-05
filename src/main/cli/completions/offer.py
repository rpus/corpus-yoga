#!/usr/bin/env python
"""
offer.py - prints the zsh statements that complete `corpus-yoga`, derived from the
declarations under src/main/cli/ as they stand when it runs.

src/main/cli/completions/offer.zsh evaluates what this prints each time tab is pressed.

stdlib-only, like cli.py.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/completions/offer.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main' / 'cli'))
from cli import (  # noqa: E402 - one reader of the declaration, and it is cli
    PATH_ARG_TYPES, commands, command_rows, subcommands_of, _subcommand_desc,
)


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
    """The zsh statements that complete one command line, derived from the declarations.
    Each position offers only what applies there: the command word, then that command's subcommands, then its flags
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
            inner = [f"    case \"${{words[3]}}\" in"]
            for s in subcommands:
                f, p = verb_scopes[s]
                inner.append(f'      {s}) {scope_parts(f, p)} ;;' if f
                             else f'      {s}) ;;')
            inner.append(f'      *) {scope_parts(cmd_flags, cmd_paths)} ;;'
                         if cmd_flags else '      *) ;;')
            inner.append('    esac')
            body = '; '.join(parts)
            tail = ' wantcmd=1;' if _takes_command_name(command) else ''
            return f"  {command}) {body}\n" + '\n'.join(inner) + f'\n   {tail} ;;'
        if cmd_flags:
            parts.append(scope_parts(cmd_flags, cmd_paths))
        if _takes_command_name(command):
            parts.append('wantcmd=1')
        return f"  {command}) {'; '.join(parts)} ;;" if parts else None

    lines = [
        'local -a cmds subcommands opts pathopts',
        'local wantcmd=0',
        'cmds=(',
        *[f"  '{esc(c['command'])}:{esc(c['summary'])}'" for c in cmds],
        ')',
        'if (( CURRENT == 2 )); then',
        "  _describe -t commands 'corpus-yoga command' cmds",
        '  return',
        'fi',
        'case "${words[2]}" in',
        *[a for c in cmds if (a := arm(c['command']))],
        'esac',
        '# A file completes ONLY as the value of a flag that takes a path.',
        'if (( ${#pathopts} )) && (( ${pathopts[(I)${words[CURRENT-1]}]} )); then',
        '  _files',
        '  return',
        'fi',
        'if [[ ${words[CURRENT]} == -* ]]; then',
        '  (( ${#opts} )) && compadd -- "${opts[@]}"',
        '  return',
        'fi',
        'if (( CURRENT == 3 )) && (( ${#subcommands} )); then',
        "  _describe -t subcommands 'subcommand' subcommands",
        '  return',
        'fi',
        'if (( wantcmd )); then',
        "  _describe -t commands 'command' cmds",
        '  return',
        'fi',
        '# Nothing here takes an argument — offer nothing, not a stray file list.',
    ]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    sys.stdout.write(completion_script(commands()))
