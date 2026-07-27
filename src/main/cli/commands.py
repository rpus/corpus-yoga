#!/usr/bin/env python
"""
commands.py (yoga commands) — each command's standard help; bare, every command's forms.

Its own file because a command determines its target's name (#40): `yoga commands` is
answered here rather than by a branch inside the dispatcher, so the dispatch path is
uniform and the declaration's `target` names something specific to this command.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli import commands, render_command_help, _forms  # noqa: E402


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


def main() -> int:
    name = next((a for a in sys.argv[1:] if not a.startswith('-')), None)
    print(render_synopsis(commands(), name), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
