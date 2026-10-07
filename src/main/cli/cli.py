#!/usr/bin/env python
"""
cli.py — the machinery behind `corpus-yoga`, the repo's terminal surface.

Two curated tables are the interface (format: src/main/cli/README.md): src/main/cli/
names each command and its target; src/main/cli/ describes the arguments.
`corpus-yoga <command> [args...]` execs the row's target with the args forwarded verbatim.
`corpus-yoga -h` lists the commands; `corpus-yoga <command> -h` renders that command's help from
the tables; a subcommand one level down (`corpus-yoga <command> <subcommand> --help`) is
answered by the target's own parser — argparse for a python target (or the parser
cli.py builds for a command it handles itself), parse_argv for a bash target (#474),
both wording their answer from the declaration. Presentation is re-derived on every invocation and stored nowhere (L5);
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
    corpus-yoga                       # suggest what to run next; run none of it
    corpus-yoga -h                    # every command with its summary
    corpus-yoga <command> -h          # the command's declaration: its forms, arguments and effects
    corpus-yoga <command> [args...]   # exec the target

This module is deliberately STDLIB-ONLY: the surface must never depend on
what pip installed, so reading the table, printing the calculus and deriving
completion stay independent of src/requirements.txt. The launcher runs it in
the venv — the venv supplies the interpreter, never imports (#478).
"""
import json
import pathlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/cli.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main - the main tier's shared modules
import tier  # noqa: E402 — the tiers, one home (#702)
import facts  # noqa: E402 - the one printer of a status's facts (#753)
from member import members  # noqa: E402
from provider import signature  # noqa: E402 - the Signature triad, one home (#704)

REPO = REPO_ROOT
CLI = Path(__file__).resolve().parent  # the declarations live beside this machinery
COLUMNS = ('command', 'target', 'calculus', 'summary')
def _declaration(command: str) -> pathlib.Path:
    """Where a command declares itself: <command>/<command>.json, always. EVERY command is
    a directory, including one with no subcommands — so gaining a verb is adding a file
    beside its siblings, not converting a file into a directory first."""
    return CLI / command / f'{command}.json'


def _declared_commands() -> list[str]:
    """Every command, from the tree itself — one directory each. Sorted, because a listing
    has no other order to be in; uniqueness needs no check because a directory cannot hold
    two entries of one name (G4, by construction). This level also holds the schemas, the
    two documents, and the machinery sources; a directory holding nothing but bytecode
    is no command (member.py, #669) — the gate polices any other stray."""
    return [p.name for p in members(CLI)]


def commands() -> list[dict]:
    """The command table, walked from src/main/cli/ rather than parsed from a CSV. The shape
    returned is unchanged — command, target, calculus, summary — so every consumer of it
    is untouched by where it now comes from."""
    out = []
    for name in _declared_commands():
        d = json.loads(_declaration(name).read_text())
        out.append({'command': name, 'target': d['target'],
                    'calculus': d.get('calculus', ''), 'summary': d['summary']})
    return out


_HELP_ROWS: list[dict] | None = None


def help_rows() -> list[dict]:
    """Every declared argument and subcommand, in the row shape the renderers already
    speak — command, subcommand, arg-name, arg-type, cardinality, help, step. The rows
    are now FLATTENED from src/main/cli/<command>[/<verb>].json rather than read from a CSV,
    so a subcommand's declaration sits beside its siblings instead of being row 14 of a
    shared file, and adding one is adding a file.

    Subcommands come in listing order, which is alphabetical: the filesystem has no other
    order to offer, and that is the point — there is no out-of-order state for a check to
    assert against (G4, by construction)."""
    global _HELP_ROWS
    if _HELP_ROWS is None:
        rows: list[dict] = []
        for name in _declared_commands():
            top = json.loads(_declaration(name).read_text())
            rows += _rows_for(name, '', top)
            d = CLI / name
            if d.is_dir():
                for f in sorted(d.glob('*.json')):
                    if f.stem != name:
                        rows += _rows_for(name, f.stem, json.loads(f.read_text()))
        _HELP_ROWS = rows
    return _HELP_ROWS


def _rows_for(command: str, subcommand: str, d: dict) -> list[dict]:
    """One declaration file → the rows the renderers expect: a describing row when it has
    a help line, then one per argument."""
    # `step` belongs to the subcommand, so it rides its DESCRIBING row only — spreading it
    # over the argument rows too would make one step look like several to cli.steps()
    base = {'command': command, 'subcommand': subcommand, 'step': ''}
    rows = []
    if d.get('help'):
        rows.append({**base, 'arg-name': '', 'arg-type': '', 'cardinality': '',
                     'help': d['help'], 'step': d.get('step', '')})
    for a in d.get('args', []):
        rows.append({**base, 'arg-name': a['name'], 'arg-type': a.get('type', ''),
                     'cardinality': a.get('cardinality', ''), 'help': a.get('help', ''),
                     'default': a.get('default')})
    return rows


def command_rows(command: str) -> list[dict]:
    return [r for r in help_rows() if r['command'] == command]


def sends_of(command: str, subcommand: str = '') -> dict[str, list[str]]:
    """The declared outward calls of one declaration file (#29): the command's own for
    subcommand '', a verb's for its name. Read from the tree directly — sends are not
    argument rows, and flattening them into row shape would be a second vocabulary.
    Keyed by the call, each value listing that call's occasions (#316)."""
    f = _declaration(command) if not subcommand else CLI / command / f'{subcommand}.json'
    if not f.exists():
        return {}
    return json.loads(f.read_text()).get('sends', {})


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
    steps, declared by the declared `step` (its value names the pipeline). The gate
    holds `src/main/cli/pipeline/pipeline.sh --plan` to these: each must appear as a plan line naming the command
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


GRAMMAR = CLI / 'README.md'
# The four states a law may declare. `gated` obliges a check to cite the law;
# `by construction` asserts the shape admits no violation; `unenforced` names the issue
# that will hold it; `doctrine` states it deliberately WITHOUT a check, because none is
# feasible or none is worth its cost. A law declaring none of them is an error, not a
# default: silence is how an unheld law passes for a held one.
#
# `doctrine` exists so that stating a law does not oblige inventing a check for it. Without
# it every law must promise enforcement, which pressures the repo into checks that need a
# curated vocabulary just to be codable — maintenance added to police prose. A law nobody
# can check honestly is better marked than left as a permanent promise.
LAW_STATES = ('gated', 'by construction', 'unenforced', 'doctrine')


def grammar_laws() -> dict[str, dict]:
    """The CLI's laws, parsed from the grammar section of src/main/cli/README.md — id ->
    {title, state, issues}. Same shape as calculus_terms() over rsc/CALCULUS.md: the
    document is the authority, and a check cites a law rather than restating it.

    A law may cite a parent corpus law (`from L5`): it is that law applied to the surface,
    and rsc/CALCULUS.md stays the authority for the principle — cited, never paraphrased.

    A law reads `- **G4 — Rows are unique and ordered.** `gated` — …`; the state is the
    first backticked token after the lead, and any #N inside it are the issues that will
    hold an unenforced law. A lead may WRAP across lines (markdown reflows prose, and a
    law whose title is long is not a law the parser may skip), so the match runs to the
    next bullet rather than to end-of-line."""
    text = GRAMMAR.read_text()
    laws: dict[str, dict] = {}
    for m in re.finditer(r'^- \*\*(G\d+) — (.+?)\*\*(.*?)(?=\n- \*\*|\n#|\Z)',
                         text, re.M | re.S):
        gid, title, rest = m.group(1), ' '.join(m.group(2).split()), m.group(3)
        marker = re.search(r'`(' + '|'.join(LAW_STATES) + r')([^`]*)`', rest)
        parent = re.search(r'`from (L\d+)`', rest)
        laws[gid] = {'title': title,
                     'state': marker.group(1) if marker else None,
                     'issues': re.findall(r'#(\d+)', marker.group(2)) if marker else [],
                     'from': parent.group(1) if parent else None}
    return laws


def calculus_laws() -> dict[str, dict]:
    """The corpus laws, parsed from rsc/CALCULUS.md — id -> {title, state, issues}. The
    SAME shape and the same marker as grammar_laws(), because it is the same mechanism one
    level up: #48 built it for the surface laws, and the laws that govern the data had the
    identical gap with higher stakes.

    The Laws section already promised this in prose — "Each law names its current
    enforcement (or the incident that taught it)" — and nothing read it, so a law could
    quietly stop being held and the document would still say it was."""
    text = (REPO / 'rsc' / 'CALCULUS.md').read_text()
    laws: dict[str, dict] = {}
    for m in re.finditer(r'^- \*\*(L\d+) — (.+?)\*\*(.*?)(?=\n- \*\*|\n#|\Z)',
                         text, re.M | re.S):
        lid, title, rest = m.group(1), ' '.join(m.group(2).split()), m.group(3)
        marker = re.search(r'`(' + '|'.join(LAW_STATES) + r')([^`]*)`', rest)
        laws[lid] = {'title': title,
                     'state': marker.group(1) if marker else None,
                     'issues': re.findall(r'#(\d+)', marker.group(2)) if marker else []}
    return laws


def _render_arg(name: str, arg_type: str) -> str:
    """One argument's usage fragment: a flag shows its name then its metavar; a
    positional shows its metavar (arg-type) alone."""
    if name.startswith('--'):
        return f'{name} {arg_type}' if arg_type else name
    return arg_type or name


def _render_args(rows: list[dict]) -> str:
    """The argument portion of a subcommand's usage, from its declared rows in order.
    cardinality is a literal count: blank -> optional [x]; a bare count '1' -> required,
    exactly that many x; 'N/<class>' -> N over the SET QUOTIENT <class> — the members
    share that value (one equivalence class) and render as the exclusive choice (a | b),
    emitted once at the first member."""
    pieces, seen = [], set()
    args = [r for r in rows if r['arg-name']]
    for r in args:
        card, frag = r['cardinality'], _render_arg(r['arg-name'], r['arg-type'])
        if card == '*':
            pieces.append(f'[{frag} ...]')
        elif not card:
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
    """The compact usage sketch (subcommands ' | '-joined), GENERATED from the declaration —
    the string the command table used to store. One source now, so it cannot drift."""
    order, bysub = _by_subcommand(command)
    subcommands = [s for s in order if s]
    bare = _render_args(bysub.get('', []))
    if not subcommands:
        return bare
    # The bare noun is an alternative like any other (G2: bare is status), and the flags
    # that attach to it — `pipeline --names`, `status --show-all` — are typeable. Dropping the
    # command-level rows once a subcommand exists left both unsayable in the one place
    # the whole surface is listed.
    return ' | '.join([bare or '(status)'] + [_join(s, _render_args(bysub[s])) for s in subcommands])


def command_forms(command: str) -> list[str]:
    """`corpus-yoga <command> …` invocation forms, generated from the declaration: one per
    subcommand (with its own args), or a single form carrying the command-level args
    when there are no subcommands."""
    order, bysub = _by_subcommand(command)
    subcommands = [s for s in order if s]
    base = f'corpus-yoga {command}'
    # ALWAYS the bare form first, then one per subcommand: it is not conditional in the
    # grammar, so it is not conditional here.
    forms = [_join(base, _render_args(bysub.get('', [])))]
    return forms + [_join(f'{base} {s}', _render_args(bysub[s])) for s in subcommands]


def _forms(c: dict) -> list[str]:
    return command_forms(c['command'])


EFFECT = {'r': 'reads', 'w': 'writes', 'consumes': 'consumes', 'x': 'runs', 'sends': 'sends'}   # a declaration's effects, in words


def _said(declared: dict, summary: str, form: str, usage: str | None = None) -> dict:
    """One declaration as help shows it: what it is for, its form as typed, its
    explanation where it has one, its arguments each with its help, and its effects."""
    out: dict = {'summary': declared.get(summary, ''), 'form': form}
    if usage is not None:
        out['usage'] = usage                  # the one line that names every verb and flag at once
    if declared.get('explanation'):
        out['explanation'] = declared['explanation']
    arguments = {a['name']: a['help'] for a in declared.get('args', [])}
    if arguments:
        out['arguments'] = arguments
    out.update({word: declared[key] for key, word in EFFECT.items() if declared.get(key)})
    return out


def help_of(command: str) -> dict:
    """A command's help: its declaration, then each verb's beneath its name - what
    `corpus-yoga <command> -h` says and the walk shows at /<command>/help, loaded from the
    declaration alone. Each form is generated from the same declaration (command_forms)."""
    forms = dict(zip([''] + subcommands_of(command), command_forms(command)))
    sketch = usage_of(command)
    out = _said(json.loads(_declaration(command).read_text()), 'summary', forms[''], f'corpus-yoga {command} {sketch}' if sketch else None)
    verbs = {verb: _said(json.loads((CLI / command / f'{verb}.json').read_text()), 'help', forms[verb])
             for verb in subcommands_of(command)}
    if verbs:
        out['verbs'] = verbs
    return out


@dataclass
class Help:
    """What `corpus-yoga <command> -h` prints: the command's help under its name."""
    command: str
    declared: dict

    def facts(self) -> dict:
        return {self.command: self.declared}


# the top's own declaration, src/main/cli/corpus-yoga.json, validated against src/main/cli/root.schema.json:
# what the tool is, and the commands bare `corpus-yoga` suggests
ROOT_DECLARATION = CLI / 'corpus-yoga.json'


def root() -> dict:
    return json.loads(ROOT_DECLARATION.read_text())


@dataclass
class Top:
    """What bare `corpus-yoga` and `corpus-yoga -h` say: what this is, then the way in -
    commands a reader types, each with its own declared summary."""
    summary: str
    commands: dict[str, str]

    def facts(self) -> dict:
        return {'corpus-yoga': self.summary, **self.commands}


def suggestions(cmds: list[dict]) -> Top:
    """Bare `corpus-yoga`: what this is, how to know whether everything is well, and how to
    navigate for more - the commands the top's declaration suggests, and the menu."""
    declared = root()
    summary = {c['command']: c['summary'] for c in cmds}
    return Top(declared['summary'], {**{f'corpus-yoga {name}': summary[name] for name in declared['suggests']},
                                     'corpus-yoga -h': 'every command, each with its summary'})


def root_flags() -> dict[str, str]:
    """The flags the launcher takes wherever they stand among the words, each with its help."""
    return {a['name']: a['help'] for a in root().get('args', [])}


def menu(cmds: list[dict]) -> Top:
    """`corpus-yoga -h`: what this is, then every command with its summary, then the flags
    the launcher takes with any command."""
    return Top(root()['summary'], {**{f'corpus-yoga {c["command"]}': c['summary'] for c in cmds},
                                  **{f'corpus-yoga <command> {flag}': help for flag, help in root_flags().items()}})


def _subcommand_desc(command: str, subcommand: str) -> str:
    """A subcommand's one-line description — the `help` line of its declaration."""
    return next((r['help'] for r in command_rows(command)
                 if r['subcommand'] == subcommand and not r['arg-name']), '')




# The arg-types whose value IS a filesystem path — the only values file completion
# suits. Matched exactly against the declared arg-type, never by substring: a metavar
# is a name, and reading meaning from its spelling would make <redirect> a directory.
# An arg-type absent here simply gets no completion, which is the safe way to be wrong.
PATH_ARG_TYPES = {'<dir>', '<path>', '<file>', '<scratch-dir>', '<machine|dir>'}


def _log_enacting(row: dict, rest: list[str]) -> None:
    """#453: the run-log obligation derives from the declaration - a verb with
    declared w or sends is enacting and leaves an anchored log under
    tmp/logs/<command>/<verb>/; a read-only face (no rows) leaves none, and a
    verb declaring "log": "self" writes its own. The log is a tee child the
    target's fds flow through: exec still hands signals, exit codes and stdin
    to the target - tee is a sink beside it, never a process between. stderr
    merges into the one stream, and python targets run unbuffered so an
    interrupt loses nothing."""
    verb = rest[0] if rest else ''
    declaration = CLI / row['command'] / f'{verb}.json'
    if not verb or verb.startswith('-') or not declaration.exists():
        return
    if any(t in ('-h', '--help') for t in rest):
        return  # a help invocation is a read-only face, log-free by construction (#474)
    d = json.loads(declaration.read_text())
    if not (d.get('w') or d.get('consumes') or d.get('sends')) or d.get('log') == 'self':
        return
    import time
    stamp = time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())
    log_dir = tier.TMP / 'logs' / row['command'] / verb
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f'{stamp}.log'
    suffix = 2
    while log.exists():
        log = log_dir / f'{stamp}-{suffix}.log'
        suffix += 1
    tee = subprocess.Popen(['tee', str(log)], stdin=subprocess.PIPE)
    assert tee.stdin is not None  # stdin=PIPE guarantees the handle
    os.dup2(tee.stdin.fileno(), 1)
    os.dup2(tee.stdin.fileno(), 2)
    tee.stdin.close()
    os.environ['PYTHONUNBUFFERED'] = '1'
    head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()
    # the header names who ran the verb by the Signature triad the commit hook stamps (#704)
    print(f"{row['command']} {verb} — {stamp} · {signature()} · {head or '(no git)'}",
          flush=True)
    print(' '.join(['corpus-yoga', row['command'], *rest]), flush=True)


def dispatch(row: dict, rest: list[str]) -> int:
    """Exec the row's target, args forwarded verbatim; a .md target is printed.
    exec (not subprocess) so signals, exit codes, and interactivity are the
    target's own — the CLI leaves no process between the user and the script.
    An enacting verb's output flows through a tee into its run log first
    (_log_enacting) - the sink beside the target, not between."""
    target = REPO / row['target']
    if target.suffix == '.md':
        print(target.read_text(), end='')
        return 0
    _log_enacting(row, rest)
    if target.suffix == '.py':
        runner = REPO / 'src' / 'run_python_script.sh'
        os.execv(str(runner), [runner.name, str(target), *rest])
    os.execv(str(target), [str(target), *rest])
    return 1  # unreachable


def main() -> int:
    argv = sys.argv[1:]
    cmds = commands()
    if not argv:
        facts.say(suggestions(cmds))      # the bare word runs nothing
        return 0
    if argv[0] in ('-h', '--help'):
        facts.say(menu(cmds))                 # help is the -h/--help flag, uniformly —
        return 0                              # not a bareword `help` the table never declared
    row = next((c for c in cmds if c['command'] == argv[0]), None)
    if row is None:
        print(f'corpus-yoga: unknown command {argv[0]!r} - the commands:', file=sys.stderr)
        print('\n'.join(facts.lines(facts.plain(menu(cmds)))), file=sys.stderr)
        return 2
    rest = argv[1:]
    # command-level help (`corpus-yoga <cmd> -h`, no subcommand before the flag) → the uniform
    # standard help. A subcommand before it (`corpus-yoga <cmd> <sub> -h`) falls through to
    # argparse, which carries that subcommand's own flags: the target's parser, or the
    # one cli.py builds for a command it handles itself.
    if rest and rest[0] in ('-h', '--help'):
        facts.say(Help(row['command'], help_of(row['command'])))
        return 0
    return dispatch(row, rest)                # a bare noun is its status, facts alone; how it is typed is -h's to say


if __name__ == '__main__':
    sys.exit(main())
