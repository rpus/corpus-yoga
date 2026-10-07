#!/usr/bin/env python
"""
grammar.py - the parsers generated from the house grammars (#597): for every
project under rsc/rpus/grammar/<project>/ (its top-level .g4 files, with
<project>/imports/ as the library where present), the Python-target lexer and
parser ANTLR generates (no listener, no visitor: the readers walk the tree
themselves), under src/gen/grammar/<project>/ - machine-local and
gitignored, like the editor's .antlr/ output beside each grammar, generated on
each machine from the committed grammar by a declared tool at a declared version
(antlr4-tools and antlr4-python3-runtime in src/requirements.txt, one version).
Every reader of a grammar runs from it: the mcp extraction reads schema.ts through
src/gen/grammar/TypeScript, so the mcp verbs and the dev gate's mcp checks need it
generated first - `corpus-yoga status sync --apply` generates it with the
rest of what a machine needs.

`grammar` is a NOUN: the generated parsers. A bare invocation reports whether each
project's parser is present and what the tool generates from its grammar now, and
writes nothing; only `sync` writes, generating what is absent, regenerating what
differs and removing what the grammar no longer produces. Both need the tool:
`antlr4` from antlr4-tools in the venv, which on first use fetches
antlr4-<version>-complete.jar into ~/.m2 (a send, refused under CORPUS_YOGA_NO_SEND=1 - the
status then reports presence only) and runs it on the machine's java. Re-running
is silence (L1). The dev gate holds every parser present and, where the tool is
present, current (grammar.parser_current), and every mcp lineage's schema.ts parsed
through it (mcp.lineages_parse).

Usage:
    corpus-yoga grammar          # status: is every parser generated, and what its grammar generates?
    corpus-yoga grammar sync     # generate what is absent, regenerate what differs, remove what is no longer generated
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
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
import facts  # noqa: E402 - the one printer of a status's facts (#753)
from send import may_send, assert_may_send, SendRefused  # noqa: E402

GRAMMARS = REPO / 'rsc' / 'rpus' / 'grammar'
GENERATED = REPO / 'src' / 'gen' / 'grammar'
TOOL_VERSION = '4.13.2'      # the runtime src/requirements.txt pins is this version's
REMEDY = 'antlr4 (antlr4-tools) is not in the venv - corpus-yoga status sync --apply installs src/requirements.txt'


def projects() -> list[Path]:
    """A project is a directory under rsc/rpus/grammar holding a top-level .g4 - the one
    rule; the machine report reads it here (#638)."""
    return sorted(p for p in GRAMMARS.iterdir() if p.is_dir() and list(p.glob('*.g4')))


def orphans() -> list[Path]:
    """A directory under rsc/rpus/grammar holding no grammar: a leftover no sync can
    generate from, named for the reader with its rm, never removed here (#638)."""
    return sorted(p for p in GRAMMARS.iterdir() if p.is_dir() and not list(p.glob('*.g4')))


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
        argv = [command, '-v', TOOL_VERSION, '-Dlanguage=Python3', '-no-listener', '-o', scratch, '-Xexact-output-dir']
        if (project / 'imports').is_dir():
            argv += ['-lib', str(project / 'imports')]
        argv += [g.name for g in sorted(project.glob('*.g4'))]
        proc = subprocess.run(argv, cwd=project, capture_output=True, text=True)
        assert proc.returncode == 0, f'{project.name}: antlr4 refused the grammar:\n{proc.stdout}{proc.stderr}'
        return {p.name: p.read_text() for p in sorted(Path(scratch).glob('*.py'))}


def held(project: Path) -> dict[str, str]:
    out = GENERATED / project.name
    return {p.name: p.read_text() for p in sorted(out.glob('*.py'))} if out.is_dir() else {}


@dataclass
class Project:
    generated: str                # where the generated parsers lie, or that they are absent
    files: int | None = None
    currency: str | None = None   # against the grammar they are generated from
    differing: list[str] | None = None
    remedy: facts.Command | None = None


@dataclass
class Status:
    projects: dict[str, Project]
    grammar: str                  # the verdict

    def facts(self) -> dict:
        return {**self.projects, 'grammar': self.grammar}


def status() -> int:
    """Each project's generated parsers against its grammar, as facts (#753); 1 while any
    is absent or stale."""
    stale = 0
    projects_: dict[str, Project] = {}
    for project in projects():
        rel = (GENERATED / project.name).relative_to(REPO)
        have = held(project)
        source = f'rsc/rpus/grammar/{project.name}'
        if not have:
            stale += 1
            projects_[project.name] = Project(
                f'no - {rel} is absent; the mcp extraction and corpus-yoga test run\'s mcp checks need it',
                remedy=facts.Command('corpus-yoga grammar sync', f'generates it from {source}, antlr4 from the venv and java from the machine'))
            continue
        item = Project(rel.as_posix(), files=len(have))
        if not tool() or not may_send():
            item.currency = 'UNVERIFIED - ' + ('CORPUS_YOGA_NO_SEND=1 refuses the tool' if tool() else 'antlr4 not in the venv')
        else:
            want = generated(project)
            differing = sorted(n for n in set(have) | set(want) if have.get(n) != want.get(n))
            if differing:
                stale += 1
                item.currency, item.differing = f'STALE against {source}', differing
                item.remedy = facts.Command('corpus-yoga grammar sync', 'regenerates')
            else:
                item.currency = f'current with {source} (antlr4 {TOOL_VERSION})'
        projects_[project.name] = item
    for orphan in orphans():
        address = orphan.relative_to(REPO).as_posix()
        projects_[address] = Project('no - it holds no grammar, a .g4 at its top level: a leftover no sync generates from',
                                     remedy=facts.Command(f'rm -r {address}', 'removes it'))
    facts.say(Status(projects_, f'{len(projects())} project(s), {stale} absent or stale'))
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
