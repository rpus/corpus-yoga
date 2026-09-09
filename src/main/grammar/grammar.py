#!/usr/bin/env python
"""
grammar.py - the parsers generated from the house grammars (#597): for every
project under rsc/rpus/grammar/<project>/ (its top-level .g4 files, with
<project>/imports/ as the library where present), the Python-target lexer, parser
and listener ANTLR generates, committed under src/main/grammar/<project>/ so every
reader of a grammar - the mcp extraction reads schema.ts through
src/main/grammar/TypeScript - runs from committed code with the runtime
src/requirements.txt pins (antlr4-python3-runtime, the tool's own version).

`grammar` is a NOUN: the generated parsers. A bare invocation reports whether each
project's committed parser is what the tool generates from its grammar now and
writes nothing; only `sync` writes, regenerating what differs and removing what the
grammar no longer produces. Both need the tool: `antlr4` from antlr4-tools in the
venv, which on first use fetches antlr4-<version>-complete.jar into ~/.m2 (a send,
refused under YOGA_NO_SEND=1 - the status then reports UNVERIFIED and holds what is
committed) and runs it on the machine's java. Re-running is silence (L1). The dev
gate holds the committed parsers current where the tool is present
(grammar.parser_current) and holds every mcp lineage's schema.ts parsed through the
committed parser everywhere (mcp.lineages_parse).

Usage:
    corpus-yoga grammar          # status: is every committed parser what its grammar generates?
    corpus-yoga grammar sync     # regenerate what differs, remove what is no longer generated
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SELF = 'src/main/grammar/grammar.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ - modules both tiers import
from declared_parser import command_parser  # noqa: E402
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main - the tier's shared modules
from send import may_send, assert_may_send, SendRefused  # noqa: E402

GRAMMARS = REPO / 'rsc' / 'rpus' / 'grammar'
GENERATED = REPO / 'src' / 'main' / 'grammar'
TOOL_VERSION = '4.13.2'      # the runtime src/requirements.txt pins is this version's
REMEDY = 'antlr4 (antlr4-tools) is not in the venv - corpus-yoga prerequisites sync --apply installs src/requirements.txt'


def projects() -> list[Path]:
    return sorted(p for p in GRAMMARS.iterdir() if p.is_dir() and list(p.glob('*.g4')))


def tool() -> str | None:
    """The antlr4 command: the venv's, else the PATH's."""
    beside = Path(sys.executable).parent / 'antlr4'
    return str(beside) if beside.is_file() else shutil.which('antlr4')


def generated(project: Path) -> dict[str, str]:
    """{file name: text} of the Python-target files the tool generates from the
    project's grammars now."""
    command = tool()
    assert command, REMEDY
    with tempfile.TemporaryDirectory() as scratch:
        argv = [command, '-v', TOOL_VERSION, '-Dlanguage=Python3', '-o', scratch, '-Xexact-output-dir']
        if (project / 'imports').is_dir():
            argv += ['-lib', str(project / 'imports')]
        argv += [g.name for g in sorted(project.glob('*.g4'))]
        proc = subprocess.run(argv, cwd=project, capture_output=True, text=True)
        assert proc.returncode == 0, f'{project.name}: antlr4 refused the grammar:\n{proc.stdout}{proc.stderr}'
        return {p.name: p.read_text() for p in sorted(Path(scratch).glob('*.py'))}


def held(project: Path) -> dict[str, str]:
    out = GENERATED / project.name
    return {p.name: p.read_text() for p in sorted(out.glob('*.py'))} if out.is_dir() else {}


def status() -> int:
    stale = 0
    for project in projects():
        rel = (GENERATED / project.name).relative_to(REPO)
        have = held(project)
        if not tool() or not may_send():
            reason = 'YOGA_NO_SEND=1 refuses the tool' if tool() else 'antlr4 not in the venv'
            print(f'grammar: {project.name}: {len(have)} committed file(s) under {rel} - currency UNVERIFIED ({reason})')
            continue
        want = generated(project)
        differing = sorted(n for n in set(have) | set(want) if have.get(n) != want.get(n))
        if differing:
            stale += 1
            print(f'grammar: {project.name}: {rel} STALE against rsc/rpus/grammar/{project.name} - '
                  f'{", ".join(differing)} differ - corpus-yoga grammar sync regenerates')
        else:
            print(f'grammar: {project.name}: {rel} current with rsc/rpus/grammar/{project.name} ({len(want)} files, antlr4 {TOOL_VERSION})')
    return 1 if stale else 0


def sync() -> int:
    assert_may_send('running antlr4-tools, which fetches the tool jar on first use')
    if not tool():
        print(f'grammar: NOT done - {REMEDY}')
        return 1
    for project in projects():
        out = GENERATED / project.name
        have, want = held(project), generated(project)
        if have == want:
            continue                          # current means no write and nothing said (L1)
        out.mkdir(parents=True, exist_ok=True)
        for name, text in want.items():
            if have.get(name) != text:
                (out / name).write_text(text)
                print(f'  ✓ {(out / name).relative_to(REPO)}')
        for name in have:
            if name not in want:
                (out / name).unlink()
                print(f'  ✓ {(out / name).relative_to(REPO)} removed - the grammar no longer generates it')
    return 0


def main():
    parser = command_parser('grammar')
    args = parser.parse_args()
    try:
        sys.exit(sync() if args.verb == 'sync' else status())
    except SendRefused as refused:
        print(f'grammar: NOT done - {refused}')
        sys.exit(1)


if __name__ == '__main__':
    main()
