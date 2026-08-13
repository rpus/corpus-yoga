#!/usr/bin/env python
"""
cli.py — the machinery behind `yoga`, the repo's terminal surface.

Two curated tables are the interface (format: src/main/cli/README.md): src/main/cli/
names each command and its target; src/main/cli/ describes the arguments.
`yoga <command> [args...]` execs the row's target with the args forwarded verbatim.
`yoga -h` lists the commands; `yoga <command> -h` renders that command's help from
the tables; a subcommand one level down (`yoga <command> <subcommand> --help`) is
answered by the target's own parser — argparse for a python target (or the parser
cli.py builds for a command it handles itself), parse_argv for a bash target (#474),
both wording their answer from the declaration. `yoga completions` derives static zsh tab-completion from
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
    yoga                       # render the table
    yoga <command> [args...]   # exec the target
    yoga completions install-latest  # regenerate the zsh tab-completion and wire it
    yoga commands              # every command's syntax: a SYNOPSIS derived from the table

This module is deliberately STDLIB-ONLY: the yoga launcher falls back to
system python3 when the venv does not exist yet, so a fresh clone can render
the table, print the calculus, and generate completion before src/main/cli/pipeline/pipeline.sh has
run. Adding a third-party import here would silently break that.
"""
import argparse
import csv
import json
import pathlib
import os
import re
import subprocess
import sys
from pathlib import Path

SELF = 'src/main/cli/cli.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
from argparse_help import enrich  # noqa: E402 — stdlib-only itself, so the bootstrap holds

REPO = REPO_ROOT
CLI = Path(__file__).resolve().parent  # the declarations live beside this machinery
COLUMNS = ('command', 'target', 'calculus', 'summary')
COMPLETION_OUT = REPO / 'tmp' / 'cache' / 'completions' / '_yoga'
def _declaration(command: str) -> pathlib.Path:
    """Where a command declares itself: <command>/<command>.json, always. EVERY command is
    a directory, including one with no subcommands — so gaining a verb is adding a file
    beside its siblings, not converting a file into a directory first."""
    return CLI / command / f'{command}.json'


def _declared_commands() -> list[str]:
    """Every command, from the tree itself — one directory each. Sorted, because a listing
    has no other order to be in; uniqueness needs no check because a directory cannot hold
    two entries of one name (G4, by construction). This level also holds the schemas, the
    two documents, and the machinery sources; the one non-command DIRECTORY is python's
    __pycache__, excluded by name — the gate polices any other stray."""
    return sorted(p.name for p in CLI.iterdir() if p.is_dir() and p.name != '__pycache__')


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
                     'cardinality': a.get('cardinality', ''), 'help': a.get('help', '')})
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
    """The compact usage sketch (subcommands ' | '-joined), GENERATED from the declaration —
    the string the command table used to store. One source now, so it cannot drift."""
    order, bysub = _by_subcommand(command)
    subcommands = [s for s in order if s]
    bare = _render_args(bysub.get('', []))
    if not subcommands:
        return bare
    # The bare noun is an alternative like any other (G2: bare is status), and the flags
    # that attach to it — `pipeline --names`, `prerequisites --show-all` — are typeable. Dropping the
    # command-level rows once a subcommand exists left both unsayable in the one place
    # the whole surface is listed.
    return ' | '.join([bare or '(status)'] + [_join(s, _render_args(bysub[s])) for s in subcommands])


def command_forms(command: str) -> list[str]:
    """`yoga <command> …` invocation forms, generated from the declaration: one per
    subcommand (with its own args), or a single form carrying the command-level args
    when there are no subcommands."""
    order, bysub = _by_subcommand(command)
    subcommands = [s for s in order if s]
    base = f'yoga {command}'
    # ALWAYS the bare form first, then one per subcommand. It is not conditional in the
    # grammar, so it is not conditional here: making it depend on whether a command has
    # subcommands puts `yoga commands` at odds with `yoga commands <one>`, which lists the
    # bare form either way.
    forms = [_join(base, _render_args(bysub.get('', [])))]
    return forms + [_join(f'{base} {s}', _render_args(bysub[s])) for s in subcommands]


def _forms(c: dict) -> list[str]:
    return command_forms(c['command'])


def render_command_help(c: dict) -> str:
    """The standard command help, shared by `yoga <cmd> -h` and `yoga commands
    <cmd>`: the summary, every invocation form, then each subcommand with its own args
    nested beneath it, command-level args flat. All generated from the declaration."""
    command = c['command']
    forms = command_forms(command)
    if subcommands_of(command):
        forms[0] += '   (status)'   # the same first form, annotated — never a second one
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
        # Declared sends render where the reader decides to run the verb (#29): an
        # outward call is part of what the invocation DOES, not an implementation note.
        for call, occasions in sends_of(command, s).items():
            for line in (f'{call} — {occasion}' for occasion in occasions):
                out.append(f"      {'sends:':<{max(w, 6)}}  {line}" if s else f"  sends: {line}")
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
    """A subcommand's one-line description — the `help` line of its declaration."""
    return next((r['help'] for r in command_rows(command)
                 if r['subcommand'] == subcommand and not r['arg-name']), '')


def verb_usage(command: str, verb: str) -> str:
    """One verb's invocation form, from its declaration — the line a refusal cites."""
    argrows = [r for r in command_rows(command)
               if r['subcommand'] == verb and r['arg-name']]
    return _join(f'yoga {command} {verb}', _render_args(argrows))


def render_verb_help(command: str, verb: str) -> str:
    """One verb's help, from its declaration (#474) — the description, the invocation
    form, each argument, the declared sends. parse_argv.py serves this text when a
    bash target's verb is asked -h: those targets have no parser of their own to
    answer with, so the declaration answers. A python target keeps answering through
    its enriched argparse — same declaration wording either way."""
    rows = [r for r in command_rows(command) if r['subcommand'] == verb]
    argrows = [r for r in rows if r['arg-name']]
    desc = _subcommand_desc(command, verb)
    head = f'yoga {command} {verb}' + (f' — {desc}' if desc else '')
    out = [head, '', '  ' + verb_usage(command, verb)]
    label = {r['arg-name']: _render_arg(r['arg-name'], r['arg-type']) for r in argrows}
    w = max((len(v) for v in label.values()), default=0)
    body = [f"  {label[r['arg-name']]:<{w}}  {r['help']}" for r in argrows]
    body += [f'  sends: {call} — {occasion}'
             for call, occasions in sends_of(command, verb).items()
             for occasion in occasions]
    if body:
        out += ['', *body]
    return '\n'.join(out) + '\n'


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
    if not (d.get('w') or d.get('sends')) or d.get('log') == 'self':
        return
    import time
    stamp = time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())
    log_dir = REPO / 'tmp' / 'logs' / row['command'] / verb
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
    name_file = REPO / 'machine-name.txt'
    room = name_file.read_text().strip() if name_file.is_file() else ''
    head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()
    print(f"{row['command']} {verb} — {stamp} · room: {room or '(unbound)'} · {head or '(no git)'}",
          flush=True)
    print(' '.join(['yoga', row['command'], *rest]), flush=True)


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


def usage_line(c: dict) -> str:
    """The tail every bare noun-status carries: the command's usage, GENERATED from
    the declaration. It names EVERY verb and flag that applies — so there is no need to
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
