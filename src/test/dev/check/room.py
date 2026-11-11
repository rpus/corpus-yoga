"""room.py - the dev gate's checks of the statuses: the facts printer, the room report, drafters, providers and the forge."""
import ast
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from gate import (
    GATE_FILES,
    CLI,
    PLAIN_PHRASE_REMEDY,
    REPO_ROOT,
    SRC,
    check,
)
from member import members
import cli
import send
import tier
import offer as cli_offer


@check(tier='code', on=['src/main/cli', 'src/main/facts.py', 'src/main/corpus.py', 'src/main/metamodel/metamodel.py', 'src/main/browser/audit.py'], says=(
    'cli.bare_suggests_and_runs_nothing',
    'cli.no_send_flag',
    'environment.names_carry_the_prefix',
    'phrase.each_is_said',
    'report.gives_no_verdict_on_itself',
    'report.every_standing_noun_ends_on_now',
    'report.now_is_the_fold',
    'report.fail_is_the_findings',
    'report.rows_are_keyed_by_subject',
    'report.says_what_the_nouns_say',
    'status.lines_load_as_yaml',
    'status.pipeline_says_declarations_and_units',
    'status.remedy_names_a_command',
    'status.room_round_trip_holds_no_pair',
    'status.value_holds_no_pair',
))
def check_status_facts(run) -> None:
    """Every noun's bare status is its facts as YAML: run as the reader runs it, in
    this checkout with sends refused, what it prints loads as one mapping - the lines are
    the data - and the usage line the CLI appends is one of its pairs. A key that stands
    twice in one mapping is refused, where YAML's own reader keeps the last in silence, and a list holds only scalars: a dash means a bare value, and a collection of
    named things is a mapping keyed by their names. And a remedy the reader types names a command: every Command a status
    constructs from a literal is a corpus-yoga command the CLI declares, with a verb it
    has, or a standard tool - read from the constructor's call sites, so a remedy a rare
    state alone would say is held before that state."""
    import subprocess
    import importlib
    status_facts = importlib.import_module('facts')
    try:
        import yaml
    except ModuleNotFoundError:
        run('status: a YAML reader arbitrates the statuses', False,
            'PyYAML is not in the venv - it is in src/requirements.txt: corpus-yoga status satisfy',
            check='status.lines_load_as_yaml')
        return

    class Strict(yaml.SafeLoader):
        pass

    def mapping_without_duplicates(loader, node, deep=False):
        keys = [loader.construct_object(key, deep=deep) for key, _value in node.value]
        twice = sorted({str(key) for key in keys if keys.count(key) > 1})
        if twice:
            raise yaml.constructor.ConstructorError(None, None, f'the key {twice[0]!r} stands twice in one mapping', node.start_mark)
        return loader.construct_mapping(node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping_without_duplicates)

    def listed_structure(node, path: str = '') -> str | None:
        """Where a list in the loaded facts holds something that is not a scalar; None where none does."""
        if isinstance(node, dict):
            for key, value in node.items():
                found = listed_structure(value, f'{path}/{key}' if path else str(key))
                if found is not None:
                    return found
        elif isinstance(node, list):
            return path if any(isinstance(item, (dict, list)) for item in node) else None
        return None

    def named_nothing(node, path: str = '') -> str | None:
        """Where a key of the loaded facts is `stands`; None where none is."""
        if isinstance(node, dict):
            for key, value in node.items():
                here = f'{path}/{key}' if path else str(key)
                if key == 'stands':
                    return here
                found = named_nothing(value, here)
                if found is not None:
                    return found
        return None

    declared = {c['command'] for c in cli.commands()}
    STANDARD = {'rm', 'mv', 'cp', 'ln', 'git', 'gh', 'brew', 'echo', 'mkdir', 'open', 'pip', 'unset'}

    def no_command(words: list[str]) -> str | None:
        """Why the words name no command a reader types; None where they name one."""
        if words[0] == 'corpus-yoga':
            if len(words) > 1 and words[1] not in declared:
                return f'`corpus-yoga {words[1]}` is no declared command'
            if len(words) > 2 and not words[2].startswith(('-', '<')):
                verbs = set(cli.subcommands_of(words[1]))
                if verbs and words[2] not in verbs:
                    return f'`corpus-yoga {words[1]} {words[2]}` - its verbs are {sorted(verbs)}'
            return None
        if words[0] not in STANDARD:
            return f'`{words[0]}` is neither corpus-yoga nor a standard tool - a path is not a command a reader types'
        return None
    for path in sorted((SRC / 'main').rglob('*.py')):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.Call) and node.args
                    and (getattr(node.func, 'attr', None) == 'Command' or getattr(node.func, 'id', None) == 'Command')):
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                literal, whole = first.value, True
            elif isinstance(first, ast.JoinedStr) and first.values and isinstance(first.values[0], ast.Constant):
                literal, whole = str(first.values[0].value), False   # the head of an f-string: its tail is computed
            else:
                continue                  # computed elsewhere: a row's remedy, a field
            words = literal.split()
            if not whole and not literal.endswith(' '):
                words = words[:-1]        # the last word runs into the computed part
            if not words:
                continue
            words[0] = words[0].removeprefix('./')      # ./corpus-yoga names this tree's code
            why = no_command(words)
            run(f'remedy: {path.relative_to(REPO_ROOT)}:{node.lineno} names a command a reader types', why is None, why,
                check='status.remedy_names_a_command')

    # The status report's rows carry their commands as columns (issues/763): the same
    # judgement over each `todo` and `bad` call's command arguments, where they are literal.
    import shlex
    report = CLI / 'status' / 'status.sh'
    logical: list[tuple[int, str]] = []
    pending, opened = '', 0
    for number, text in enumerate(report.read_text().splitlines(), 1):
        if not pending:
            opened = number
        if text.rstrip().endswith('\\'):
            pending += text.rstrip()[:-1] + ' '
            continue
        logical.append((opened, pending + text))
        pending = ''
    for number, text in logical:
        call = re.match(r'\s*(?:\S+\)\s+)?(todo|bad) ', text)   # the call opens the statement, or a case arm
        if call is None:
            continue
        try:
            tokens = shlex.split(text[call.start(1):])
        except ValueError:
            run(f'remedy: {report.relative_to(REPO_ROOT)}:{number} is a row a reader can parse', False,
                'the call does not split into its arguments', check='status.remedy_names_a_command')
            continue
        arguments = tokens[1:]
        stop = next((i for i, token in enumerate(arguments) if token in (';;', ';', '&&', '||')), len(arguments))
        for command in arguments[2:stop:2]:        # after the row's subject and what stands
            words = command.split()
            if not words or words[0].startswith('$'):
                continue                  # computed where the row is emitted: a path the check found, a remedy another verb wrote
            words[0] = words[0].removeprefix('./')
            why = no_command(words)
            run(f'remedy: {report.relative_to(REPO_ROOT)}:{number} `{command[:40]}` names a command a reader types', why is None, why,
                check='status.remedy_names_a_command')

    def pair_in_a_value(node, at: str = ''):
        """The first text value that holds a colon followed by a space, or ends on a colon: (where, the value)."""
        if isinstance(node, dict):
            return next((found for key, value in node.items() if (found := pair_in_a_value(value, f'{at}/{key}'))), None)
        if isinstance(node, list):
            return next((found for index, value in enumerate(node) if (found := pair_in_a_value(value, f'{at}/{index}'))), None)
        return (at, node) if isinstance(node, str) and (': ' in node or node.endswith(':')) else None

    env = {**os.environ, 'CORPUS_YOGA_NO_SEND': '1'}
    for noun in sorted(c['command'] for c in cli.commands() if cli.subcommands_of(c['command'])):
        proc = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), noun], capture_output=True, text=True,
                              env=env, cwd=REPO_ROOT, timeout=300)
        try:
            loaded = yaml.load(proc.stdout, Loader=Strict)
            said_wrong = [line for line in proc.stderr.splitlines() if line.strip()]
            why = None if isinstance(loaded, dict) else (f'loads as {type(loaded).__name__}, not a mapping'
                                                         + (f' - it exits {proc.returncode}, saying {said_wrong[-1][:200]}' if said_wrong else ''))
            if why is None and getattr(status_facts, 'load', None) is not None:
                # the printer's own reader reads what the YAML reader reads (issues/766)
                try:
                    if status_facts.load(proc.stdout) != loaded:
                        why = 'the printer\'s reader and the YAML reader read it differently'
                except ValueError as error:
                    why = f'the printer\'s reader refuses it: {error}'
            if why is None:
                # no key names nothing (issues/771, issues/779): `stands` is a head that says nothing of what follows
                nothing = named_nothing(loaded)
                if nothing is not None:
                    why = f'the key at {nothing} names nothing - a probe\'s answer stands under what it is about'
            if why is None:
                # a dash means a bare value (issues/765): a collection of named things is a mapping keyed by their names
                nested = listed_structure(loaded)
                if nested is not None:
                    why = f'the list at {nested} holds a mapping or a list - a collection is keyed by its members\' names'
        except yaml.YAMLError as error:
            mark = getattr(error, 'problem_mark', None)
            where = f' at line {mark.line + 1}' if mark is not None else ''
            line = proc.stdout.splitlines()[mark.line] if mark is not None and mark.line < len(proc.stdout.splitlines()) else ''
            why = f'{getattr(error, "problem", error)}{where}: {line.strip()[:100]}'
        run(f'status: corpus-yoga {noun}: its lines load as one mapping', why is None, why,
            check='status.lines_load_as_yaml')
        # no value holds a pair (issues/792): the first colon-space on a line ends its key
        try:
            paired = pair_in_a_value(yaml.load(proc.stdout, Loader=Strict))
        except yaml.YAMLError:
            paired = None                         # said above
        run(f'status: corpus-yoga {noun}: the printer\'s round trip over this room holds no colon followed by a space', paired is None,
            None if paired is None else f'the value at {paired[0]} holds one: {paired[1][:120]} - a pair is a fact of its own beneath, or the phrase says it without the colon',
            check='status.room_round_trip_holds_no_pair')

    # The machine report says what a noun's status says, taken from that status (issues/777):
    # each section it grafts is, in the full report, the noun's own facts at that spot.
    said_text: dict[tuple[str, ...], str] = {}      # each command's output, read once a section
    def said_by(*words: str) -> dict:
        out = said_text.setdefault(words, subprocess.run([str(REPO_ROOT / 'corpus-yoga'), *words], capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=300).stdout)
        try:
            loaded = yaml.load(out, Loader=Strict)
        except yaml.YAMLError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    def at(node, *keys):
        for key in keys:
            node = node.get(key) if isinstance(node, dict) else None
        return node
    whole = said_by('status', '--show-all')
    # a grafted section is headed by its command (issues/812): `corpus-yoga <noun>`, and beneath it what
    # stands at each pointer under the pointer's last key, or the noun's whole status
    grafts = [('completions', 'completions'), ('test', 'test', 'pre-commit hook'), ('test', 'test', 'signature hook'),
              ('server', 'server', 'render assets'), ('forge', 'forge settings'), ('forge', 'branches'),
              ('stage', 'invalid'), ('stage', 'unlicensed'), ('grammar',), ('migration',)]
    for noun, *spot in grafts:
        own = at(said_by(noun), *spot)
        if not spot and isinstance(own, dict):
            own = {key: value for key, value in own.items() if key != 'now'}   # a noun's now: is the room's, folded (issues/1050)
        section = whole.get(f'corpus-yoga {noun}')
        last = spot[-1] if spot else ''
        said = section if not last or last == noun else (section.get(last) if isinstance(section, dict) else None)
        same = own is not None and said == own or own is None and str(said).startswith(f'corpus-yoga {noun} says nothing at')
        run(f'report: its corpus-yoga {noun} section{" / " + last if last and last != noun else ""} is what corpus-yoga {noun} says', same,
            None if same else f'the report says {str(said)[:120]} where corpus-yoga {noun} says {str(own)[:120]}',
            check='report.says_what_the_nouns_say')
    by_forge = at(said_by('forge'), 'this checkout', 'pre-commit')
    by_forge = str(next(iter(by_forge.values())) if isinstance(by_forge, dict) else by_forge)   # a row that owes a remedy says its state first
    by_test = str(at(said_by('test'), 'test', 'pre-commit hook', 'installed'))
    same = by_test.removeprefix('yes - ') == by_forge or by_forge.endswith(by_test)
    run('report: the forge says the commit hook as corpus-yoga test says it', same,
        None if same else f'the forge says {by_forge[:100]} where corpus-yoga test says {by_test[:100]}', check='report.says_what_the_nouns_say')
    # The room's standing is the fold of every noun's own now: (issues/949), each gathered from that
    # noun's own body (issues/1028), with an act two nouns name over one unit taken once; and
    # the report's now: is that fold with the acts its own rows name, which are MUST - a row
    # names a fault (issues/1050).
    import importlib
    nouns_with_now = importlib.import_module('standing').NOUNS   # as each noun declares `standing` (issues/1034)
    own_now = {noun: at(said_by(noun), 'now') for noun in nouns_with_now}
    nowless = sorted(noun for noun, now in own_now.items() if now is None)
    run('report: every noun that declares standing ends its bare status on now:', not nowless,
        None if not nowless else f'{", ".join(nowless)}: bare corpus-yoga <noun> says no now: - say the status through facts.say_standing',
        check='report.every_standing_noun_ends_on_now')
    import copy
    folded = importlib.import_module('standing').fold(own_now)
    room_now = whole.get('now')
    room_now = room_now if isinstance(room_now, dict) else {}
    holds_fold = importlib.import_module('facts').merge(copy.deepcopy(room_now), folded, once=True) == room_now
    may_is_fold = set(room_now.get('MAY', {})) == set(folded.get('MAY', {}))
    in_order = list(room_now) == [m for m in ('MAY', 'MUST') if m in room_now]
    same = holds_fold and may_is_fold and in_order and (room_now or whole.get('now') == 'none - nothing to do')
    run('report: its now: is the fold of every noun\'s own now:, with the MUST acts its own rows name', bool(same),
        None if same else f'the report says {str(whole.get("now"))[:160]} where the fold gives {str(folded)[:160]}', check='report.now_is_the_fold')

    # The report's FAIL: is every finding the nouns' statuses hold, gathered under each noun's
    # command (issues/1058): an error is a fact of its noun, said once more where the room is read,
    # and never an entry of now:, whose every entry is a command.
    gather = getattr(importlib.import_module('standing'), 'failing', None)
    findings = {f'corpus-yoga {noun}': found for noun in nouns_with_now if gather is not None and (found := gather(said_by(noun))) is not None}
    commands = all(str(line).removeprefix('./').startswith('corpus-yoga ') and isinstance(does, dict) and not any(key == 'reports the noun' for key in does)
                   for line, does in room_now.get('MUST', {}).items())
    same = gather is not None and whole.get('FAIL') == (findings or None) and commands
    run('report: its FAIL: is every finding the nouns hold, and every entry of its now: MUST: is a command', same,
        None if same else 'src/main/standing.py has no failing(said)' if gather is None
        else f'the report says FAIL: {str(whole.get("FAIL"))[:160]} where the nouns hold {str(findings)[:160]}; MUST: holds {list(room_now.get("MUST", {}))}',
        check='report.fail_is_the_findings')

    paired = pair_in_a_value(whole)
    run('status: the full machine report: the printer\'s round trip over this room holds no colon followed by a space', paired is None,
        None if paired is None else f'the value at {paired[0]} holds one: {paired[1][:120]}', check='status.room_round_trip_holds_no_pair')
    # The phrases a status can say are its noun's declared phrase array (issues/909, issues/914, issues/935), each its
    # own identity: the one property - no value holds a colon followed by a space - judged
    # over every phrase, in every room alike, with no room's state; each phrase declared
    # once across the nouns; and every declared phrase said by its noun, quoted - in the
    # noun's own sources, its target, or any module under src/main, since a status composes
    # through the shared modules and through the pipelines' (the audit's, the measures', the page comparison's).
    held_by: dict[str, str] = {}
    for declaration in sorted(CLI.glob('*/*.json')):
        noun = declaration.parent.name
        if declaration.stem != noun:
            continue
        worded = json.loads(declaration.read_text()).get('phrase') or []
        if not worded:
            continue
        faults = [said[:80] for said in worded if ': ' in said or said.endswith(':') or ' #' in said or '\u2014' in said]
        run(f'status: corpus-yoga {noun}: no declared phrase holds a colon followed by a space', not faults,
            None if not faults else '; '.join(faults)[:300] + ' - ' + PLAIN_PHRASE_REMEDY,
            check='status.value_holds_no_pair')
        twice = [said for said in worded if said in held_by]
        run(f'phrase: corpus-yoga {noun}: each phrase is declared once', not twice,
            None if not twice else f'also declared by corpus-yoga {held_by[twice[0]]}: {twice[0][:80]}', check='phrase.each_is_said')
        held_by.update({said: noun for said in worded})
        sources = ''.join(f.read_text() for f in [*declaration.parent.glob('*'), *CLI.parent.rglob('*.py'), *CLI.parent.rglob('*.sh')] if f.suffix in ('.py', '.sh'))
        target = REPO_ROOT / json.loads(declaration.read_text())['target']
        sources += target.read_text() if target.is_file() else ''
        unsaid = [said for said in worded if said not in sources]
        run(f'phrase: corpus-yoga {noun}: every declared phrase is said by its noun, quoted', not unsaid,
            None if not unsaid else f'declared and said by no row: {"; ".join(s[:60] for s in unsaid)}', check='phrase.each_is_said')
    # what a measure says of a unit is a value of the stage's and the store's statuses, read here
    # without a store: the worktree a commit is gated in holds none
    import corpus as corpus_relations
    worded = {name: words({'a': b'x'}, {'a': b'x'}, None) for name, (_, _, words) in corpus_relations.MEASURE.items() if name in ('mirror', 'message-uuids')}
    paired = pair_in_a_value(worded)
    run('status: what a measure says of a unit holds no colon followed by a space', paired is None,
        None if paired is None else f'the {paired[0][1:]} measure says {paired[1]}', check='status.room_round_trip_holds_no_pair')

    # Every environment variable the repository reads carries the command's name as its
    # prefix (issues/703): no code reads an old name, and a python read of the environment names
    # either CORPUS_YOGA_<name> or a variable that is another's - the OS's, the provider's.
    old_names = ('YOGA_NO_SEND', 'YOGA_JOBS', 'YOGA_GATE_TIMINGS')
    foreign = {'HOME', 'PATH', 'TMPDIR', 'TERM', 'SHELL', 'USER', 'PWD', 'COLUMNS', 'LINES', 'ZDOTDIR', 'USER_ZDOTDIR',
               'GIT_INDEX_FILE', 'PYTHONUNBUFFERED', 'PYTHON_COLORS', 'NO_COLOR', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL'}
    read_badly: list[str] = []
    # two files name the old names in order to find them: this check, and the status report's
    # row that tells a machine it still exports one (issues/703)
    detectors = {*GATE_FILES, CLI / 'status' / 'status.sh'}
    for path in [REPO_ROOT / 'corpus-yoga', *sorted(SRC.rglob('*.py')), *sorted(SRC.rglob('*.sh'))]:
        if not path.is_file() or 'gen/' in path.as_posix() or path in detectors:
            continue
        text = path.read_text(errors='ignore')
        rel = path.relative_to(REPO_ROOT)
        for name in old_names:
            if re.search(rf'(?<![A-Z_]){name}\b', text):
                read_badly.append(f'{rel} names {name}')
        if re.search(r'\$\{VENV[:}]|\bVENV=|environ(\.get)?\(?\[?[\'"]VENV[\'"]', text):
            read_badly.append(f'{rel} reads VENV')
        if path.suffix == '.py':
            for found in re.findall(r"""os\.environ(?:\.get)?\(?\[?['"]([A-Z_]+)['"]""", text):
                if not found.startswith('CORPUS_YOGA_') and found not in foreign:
                    read_badly.append(f'{rel} reads {found}')
    run('environment: every variable the repository reads carries the prefix CORPUS_YOGA_', not read_badly,
        None if not read_badly else '; '.join(sorted(set(read_badly))[:6]), check='environment.names_carry_the_prefix')
    # --no-send before the command word refuses every send (issues/703), so a reader need not
    # know the variable: the forge's status, which sends, says so.
    sendless = {k: v for k, v in os.environ.items() if k not in ('YOGA_NO_SEND', 'CORPUS_YOGA_NO_SEND')}
    for words in (['--no-send', 'forge'], ['forge', '--no-send']):
        without_sends = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), *words], capture_output=True, text=True, env=sendless, cwd=REPO_ROOT, timeout=120)
        run(f'cli: corpus-yoga {" ".join(words)} runs it with every send refused', 'refuses the send' in without_sends.stdout,
            None if 'refuses the send' in without_sends.stdout else f'it says {(without_sends.stdout + without_sends.stderr).strip()[:160]!r}', check='cli.no_send_flag')
    offered = cli_offer.completion_script(cli.commands())
    declared_flags = ' '.join(a['name'] for a in json.loads((CLI / 'corpus-yoga.json').read_text()).get('args', []))
    run(f'cli: tab offers the launcher\'s flags, {declared_flags}, at every position (issues/510)',
        f'launcher=({declared_flags})' in offered and 'compadd -- "${launcher[@]}"' in offered and '--no-send' in declared_flags and '-h' in declared_flags.split(),
        None if f'launcher=({declared_flags})' in offered else f'what zsh evaluates names {offered.count("launcher")} launcher line(s), the flags declared being {declared_flags!r}', check='cli.no_send_flag')

    # The pipeline noun says each pipeline by its declaration and each staged unit by its
    # facts (issues/800): under `pipelines:` the pipelines alone, each with its declared input and
    # the steps its plan names; under `staged:` a mapping of units, each a mapping of facts;
    # the counts left to `corpus-yoga stage`; its acts under now: (issues/1050).
    pipeline_said = said_by('pipeline')
    declared_pipelines = sorted(d.name for d in (SRC / 'main').iterdir() if (d / 'pipeline.json').is_file())
    def planned(name: str) -> list[str]:
        out = subprocess.run([str(SRC / 'main' / name / 'run.sh'), '--plan'], capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=120).stdout
        steps: list[str] = []
        for line in out.splitlines():
            if line.startswith('  ') and not line.rstrip().endswith(':'):
                words = line.split()
                word = ' '.join(words[:3]) if words[0] == 'corpus-yoga' else words[0]   # a step that is a corpus-yoga verb keeps its verb
                if word not in steps:
                    steps.append(word)
        return steps
    shown = pipeline_said.get('pipelines')
    shown = shown if isinstance(shown, dict) else {}
    why = (f'pipelines: holds {sorted(shown) or pipeline_said.get("pipelines")}, where the pipelines are {declared_pipelines}'
           if sorted(shown) != declared_pipelines else None)
    for name in declared_pipelines if why is None else []:
        each = shown[name]
        declared = json.loads((SRC / 'main' / name / 'pipeline.json').read_text())
        if not isinstance(each, dict):
            why = f'{name} is said as {str(each)[:80]!r}, not by its declaration'
        elif each.get('input') != declared['input']:
            why = f'{name} says input {each.get("input")!r}, where its declaration says {declared["input"]!r}'
        elif not set(planned(name)) <= set(each.get('steps') or []):
            why = f'{name} says steps {each.get("steps")}, where its plan names {planned(name)}'
        if why:
            break
    staged = pipeline_said.get('staged')
    if why is None and 'stage' in pipeline_said:
        why = f'it ends with a stage: sentence, {str(pipeline_said["stage"])[:80]!r}, where corpus-yoga stage says the counts'
    if why is None and not isinstance(staged, dict):
        why = f'staged: is {str(staged)[:80]!r}, not a mapping of units'
    if why is None and isinstance(staged, dict):
        for address, unit in staged.items():
            if not isinstance(unit, dict) or 'judged' not in unit:
                why = f'the unit {address[:60]} is said as {str(unit)[:80]!r}, not by its facts'
                break
    run('status: corpus-yoga pipeline says each pipeline by its declaration and each staged unit by its facts', why is None, why,
        check='status.pipeline_says_declarations_and_units')
    for noun in ('agent', 'browser', 'export'):
        own = said_by(noun)                       # a noun that refuses to report at all (an unbound room, issues/758) says neither key
        why = (f'it ends with a stage: sentence, {str(own["stage"])[:80]!r}' if 'stage' in own
               else 'its staged: is not a mapping of units' if 'staged' in own and not isinstance(own['staged'], dict) else None)
        run(f'status: corpus-yoga {noun} says its staged units by their facts, and no counts', why is None, why,
            check='status.pipeline_says_declarations_and_units')

    # The default report of a room with no row to say is still one mapping (issues/807): the
    # worktree the gate runs in always has rows, so the empty case is made here.
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.rows', delete=False) as empty:
        empty.write('x\tgraft\tnonesuch\t/nowhere\n')
        empty_rows = empty.name
    said_empty = subprocess.run([sys.executable, str(CLI / 'status' / 'report.py'), 'report', empty_rows, '0'],
                                capture_output=True, text=True, env={**env, 'CORPUS_YOGA_VENV': sys.prefix}, cwd=REPO_ROOT, timeout=120).stdout
    Path(empty_rows).unlink()
    try:
        loaded_empty = yaml.load(said_empty, Loader=Strict)
    except yaml.YAMLError as error:
        loaded_empty = f'does not load - {getattr(error, "problem", error)}'
    alone = isinstance(loaded_empty, dict) and list(loaded_empty) in (['now'], ['FAIL', 'now'])   # the nouns' findings and standing are the room's, rows or none
    run('status: the report of a room with no row to say loads as one mapping - its now:, after FAIL: where a noun holds a finding - and no section', alone,
        None if alone else f'it says {said_empty.strip()[:120]!r}',
        check='status.lines_load_as_yaml')

    # The machine report gives no verdict on itself (issues/786): it ends at its last section,
    # and what needs doing is read from its now:.
    verdict = whole.get('status')
    run('report: it gives no verdict on itself', bool(whole) and verdict is None,
        None if whole and verdict is None else f'the report ends `status: {str(verdict)[:120]}`' if whole else 'corpus-yoga status --show-all loads as nothing',
        check='report.gives_no_verdict_on_itself')

    # The bare word suggests what to run next, and runs none of it (issues/786): asked in this
    # process with nothing allowed to run, it says commands a reader can type, each with
    # the summary its own declaration gives.
    import contextlib
    import io
    ran: list = []
    def refused(*args, **kwargs):
        ran.append(args[0] if args else kwargs.get('args'))
        return subprocess.CompletedProcess([], 0, '', '')
    # both ways the CLI hands over are refused: a child, and the exec that replaces this process
    real_run, real_exec, real_argv, heard = subprocess.run, os.execv, sys.argv, io.StringIO()
    try:
        subprocess.run, os.execv, sys.argv = refused, refused, ['corpus-yoga']
        with contextlib.redirect_stdout(heard):
            cli.main()
    finally:
        subprocess.run, os.execv, sys.argv = real_run, real_exec, real_argv
    try:
        suggested = yaml.load(heard.getvalue(), Loader=Strict)
    except yaml.YAMLError:
        suggested = None
    suggested = suggested if isinstance(suggested, dict) and suggested else None
    summaries = {f"corpus-yoga {c['command']}": c['summary'] for c in cli.commands()}
    root_summary = json.loads((CLI / 'corpus-yoga.json').read_text())['summary'] if (CLI / 'corpus-yoga.json').is_file() else None
    why = (f'it runs {", ".join(str(a if isinstance(a, str) else a[0]).removeprefix(f"{REPO_ROOT}/") for a in ran)}' if ran
           else f'it says {heard.getvalue().strip()[:120] or "nothing"}, not what this is and the commands' if suggested is None
           else f'its first line is {next(iter(suggested))!r}, not `corpus-yoga: <what this is>`' if next(iter(suggested)) != 'corpus-yoga' or suggested['corpus-yoga'] != root_summary
           else next((f'`{line}` is no command a reader types' for line in suggested if line not in summaries and line not in ('corpus-yoga', 'corpus-yoga -h')), None)
           or next((f'`{line}` is said as {str(does)[:80]}, where its declaration says {summaries[line][:80]}'
                    for line, does in suggested.items() if line in summaries and does != summaries[line]), None)
           or (None if 'corpus-yoga status' in suggested else 'the room\'s status is not among what it suggests'))
    run('bare: corpus-yoga says what this is, suggests what to run next, and runs none of it', why is None, why, check='cli.bare_suggests_and_runs_nothing')

    # The machine report's rows are keyed by what each is about (issues/771): in the full
    # report no key names a kind - ok, note, todo, stands, missing - and no list holds rows.
    said_by('status', '--show-all')
    report_text = said_text[('status', '--show-all')]
    try:
        report = yaml.load(report_text, Loader=Strict)
        def keyed_by_kind(node, path: str = '') -> list[str]:
            if not isinstance(node, dict):
                return []
            return [f'{path}/{key}' for key in node if key in ('ok', 'note', 'todo', 'stands', 'missing')] + [
                found for key, value in node.items() for found in keyed_by_kind(value, f'{path}/{key}' if path else str(key))]
        kinds = sorted(keyed_by_kind(report))
        listed = listed_structure(report) or next((section for section, rows in report.items() if isinstance(rows, list)), None)
        why = (f'rows stand under a kind that names nothing: {", ".join(kinds[:4])}' if kinds
               else f'the rows of {listed} are a list' if listed else None)
    except yaml.YAMLError as error:
        why = f'the full report does not load: {getattr(error, "problem", error)}'
    run('report: every row of the machine report is keyed by what it is about', why is None, why,
        check='report.rows_are_keyed_by_subject')


@check(tier='code', on=['src/main/facts.py'], says=(
    'facts.lines_are_yaml',
    'facts.reads_back_what_it_prints',
    'facts.wraps_and_reads_back',
    'facts.wraps_only_for_a_terminal',
))
def check_facts(run) -> None:
    """A status's facts print as YAML a reader loads back: a mapping's keys in order,
    a list's items with a dash, a nested fact indented beneath its heading, and a string
    quoted exactly where YAML would read it as a number, a boolean, null, a time or a
    mapping - so that the lines are the data."""
    import importlib
    try:
        facts = importlib.import_module('facts')
    except ModuleNotFoundError:
        run('facts: a status prints its facts as YAML a reader loads back', False,
            'src/main has no printer of facts: every status prints prose of its own', check='facts.lines_are_yaml')
        return
    got = facts.lines({'held': {'a/b capture': 121}, 'twice': [{'memory': 'x/memory', 'identical to': 'y/memory'}],
                       'odd': ['121', 'true', '2026-09-30T121242Z', '-Users-x', 'a: b', 'word #tag', '', None, 2],
                       'empty': {}, 'none': []})
    expected = ['held:', '  a/b capture: 121', 'twice:', '  - memory: x/memory', '    identical to: y/memory', 'odd:',
                '  - "121"', '  - "true"', '  - 2026-09-30T121242Z', '  - -Users-x', '  - "a: b"', '  - "word #tag"',
                '  - ""', '  - null', '  - 2', 'empty: {}', 'none: []']
    run('facts: a status prints its facts as YAML a reader loads back', got == expected,
        None if got == expected else f'the lines read {got}', check='facts.lines_are_yaml')
    # The printer's own reader is its inverse (issues/766): what it prints it reads back, and
    # a YAML reader reads the same - so a reader of a status needs nothing but the printer.
    load = getattr(facts, 'load', None)
    if load is None:
        run('facts: the printer reads back what it prints', False,
            'src/main/facts.py prints and does not read: a reader of a status needs a YAML library', check='facts.reads_back_what_it_prints')
        return
    sample = {'held': {'a/b capture': 121}, 'odd': ['121', 'true', '2026-09-30T121242Z', '2026-09-30T12:12:42Z', '2026-09-30', '-Users-x', 'a: b', 'word #tag', '', None, 2, 1.5, '34e10310', 1e-05, 1e+16, '1.0e+16'],
              'empty': {}, 'none': [], 'deep': {'x': {'y': {'z': ['p', 'q']}}}, 'a: key': 'v', 'of lists': [['a', 'b'], ['c']],
              'of mappings': [{'memory': 'x/memory', 'identical to': 'y/memory'}]}
    text = '\n'.join(facts.lines(sample))
    try:
        import yaml
        theirs = yaml.safe_load(text)
    except ModuleNotFoundError:
        theirs = sample
    try:
        mine = load(text)
        why = None if mine == sample == theirs else f'read back {mine}; a YAML reader read {theirs}'
    except ValueError as error:
        why = f'the reader refused what the printer wrote: {error}'
    run('facts: the printer reads back what it prints', why is None, why, check='facts.reads_back_what_it_prints')
    try:
        load('a: 1\na: 2')
        twice = 'a key that stands twice in one mapping was read'
    except ValueError:
        twice = None
    run('facts: the reader refuses a key that stands twice', twice is None, twice, check='facts.reads_back_what_it_prints')
    # A value too long for the terminal continues on indented lines and loads as the same
    # value (issues/790): at a given width no line passes it, each fact unbroken is one line, and
    # what was broken loads as what was printed - under a YAML reader and under the
    # printer's own - at every depth, plain or quoted, in a mapping or a list, and with no
    # line opening on a dash the value held.
    long = {'top': {'plain': 'walk the room - each word of this value is one a break may fall before, and - a dash - opens none',
                    'quoted': 'said: a value YAML would misread, so it is quoted, and long enough to be broken more than once',
                    'bare': ['a bare value in a list, long enough that it too continues on the lines beneath it'],
                    'members': [{'name': 'a mapping in a list, whose first pair shares the dash and is long enough to continue', 'n': 1}],
                    'short': 'stays'}}
    width = 40
    try:
        narrow = facts.lines(long, width=width)
    except TypeError:
        narrow = None
    if narrow is None:
        why = 'the printer takes no width: a long value is one long line, and a terminal continues it at column 0, left of its own key'
    else:
        joined = '\n'.join(narrow)
        try:
            import yaml
            theirs = yaml.safe_load(joined)
        except ModuleNotFoundError:
            theirs = long
        except Exception as error:               # a YAML reader refusing the broken lines is the finding
            theirs = f'refused - {error}'
        try:
            mine = load(joined)
        except ValueError as error:
            mine = f'refused - {error}'
        over = [line for line in narrow if len(line) > width]
        # a width at which the break would fall before the dash, were it allowed to
        dashed = [line for line in facts.lines({'k': 'aaaa bbbb - cccc'}, width=12) if line.strip().startswith('-')]
        why = (f'{len(over)} line(s) pass {width} columns: {over[0]!r}' if over
               else f'a fact printed with no width is not one line: {len(facts.lines(long))} lines for 9 facts' if len(facts.lines(long)) != 9
               else f'a YAML reader reads the broken lines as {str(theirs)[:160]}' if theirs != long
               else f'the printer\'s reader reads the broken lines as {str(mine)[:160]}' if mine != long
               else f'a continuation opens on a dash the value held: {dashed[0]!r}' if dashed
               else None)
    run('facts: a value too long for the width continues on indented lines and loads as the same value', why is None, why,
        check='facts.wraps_and_reads_back')
    # The width is the terminal's, read when the lines are printed (issues/790): said to a
    # terminal 40 columns wide a long value is broken to fit it; said to a pipe it is one line.
    import fcntl
    import pty
    import struct
    import subprocess
    import termios
    said = 'a value long enough that a terminal forty columns wide cannot hold it on one line with its key'
    program = (f'import facts; from dataclasses import dataclass\n'
               f'@dataclass\nclass Said:\n    said: str\nfacts.say(Said({said!r}))')
    quiet = {key: value for key, value in os.environ.items() if key not in ('COLUMNS', 'LINES')}
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
        saying = subprocess.Popen([sys.executable, '-c', program], stdout=slave, env=quiet)
        os.close(slave)                           # the child holds the terminal; what it writes is read before it closes
        shown = b''
        while True:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            shown += chunk
        saying.wait(timeout=60)
    finally:
        os.close(master)
    to_terminal = shown.decode().replace('\r', '').strip('\n').split('\n')
    to_pipe = subprocess.run([sys.executable, '-c', program], capture_output=True, text=True, env=quiet, timeout=60).stdout.strip('\n').split('\n')
    why = (f'said to a pipe it is {len(to_pipe)} lines, not one' if len(to_pipe) != 1
           else f'said to a terminal {width} columns wide it is {len(to_terminal)} line(s), the longest {max(map(len, to_terminal))} columns'
           if len(to_terminal) < 2 or max(map(len, to_terminal)) > width else None)
    run('facts: the width is the terminal\'s, and a pipe is given one line a fact', why is None, why, check='facts.wraps_only_for_a_terminal')


@check(tier='code', on=['src/main/provider.py', 'src/main/cli/agent/drafters.py'], says=(
    'drafters.first_signature_is_the_drafter',
    'drafters.signature_is_read_as_written',
))
def check_drafters(run) -> None:
    """A Signature is read by the grammar that writes it, and a message's first Signature
    is its drafter: the join of main's messages to the store's sessions rests on
    both, and neither needs a store to be shown."""
    import provider
    read = getattr(provider, 'read_signature', None)
    if read is None:
        run('drafters: a Signature is read by the grammar that writes it', False,
            'src/main/provider.py writes the Signature and reads none: nothing joins a message to its session',
            check='drafters.signature_is_read_as_written')
        return
    cases = {'Signature: reading-room/claude/be12fa7c': ('reading-room', 'claude', 'be12fa7c'),
             'Signature: home-room': ('home-room', None, None),
             f'Signature: {provider.signature()}': tuple((provider.signature().split('/') + [None, None])[:3]),
             'Signature: <machine>/<provider>/<session>': None,
             'Signature: reading-room/claude': None,
             'Signature: reading-room   # typed by hand': None,
             '  Signature: reading-room': None}
    wrong = [f'{line!r} read {read(line)}, not {want}' for line, want in cases.items() if read(line) != want]
    run('drafters: a Signature is read by the grammar that writes it', not wrong,
        '; '.join(wrong) if wrong else None, check='drafters.signature_is_read_as_written')
    import importlib.util
    spec = importlib.util.spec_from_file_location('drafters', SRC / 'main' / 'cli' / 'agent' / 'drafters.py')
    assert spec and spec.loader
    drafters = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(drafters)
    body = ('* one message (pull/1): its text\n\nSignature: home-room/claude/41ff13e9\n'
            'Signature: reading-room/claude/be12fa7c\nSignature: reading-room\n\n'
            '* a second, by the room\'s own shell\n\nSignature: reading-room\n\nthe forge\'s own closing words\n')
    expected = [('* one message (pull/1): its text', [('home-room', 'claude', '41ff13e9'),
                                                  ('reading-room', 'claude', 'be12fa7c'),
                                                  ('reading-room', None, None)]),
                ("* a second, by the room's own shell", [('reading-room', None, None)])]
    got = drafters.drafted(body)
    run("drafters: a message's first Signature is its drafter, the rest its co-drafters", got == expected,
        None if got == expected else f'the body read {got}', check='drafters.first_signature_is_the_drafter')


@check(tier='code', says=('provider.names_declared', 'provider.registry_parses'), on=['rsc/provider', 'src'])
def check_provider_registry(run) -> None:
    """The provider registry (rsc/provider/providers.csv) parses, and every
    provider src/ names - by a directory under the two browser trees or the agent command, or by a
    data/input/<provider>/chat/ or /code/ path in a script or declaration, the two
    modalities a provider has (data/input/github/ is the forge's, not a provider's) - is a row of it: the
    registry is the one source of provider names, and a name it does not declare is a
    provider the hook cannot attest and the report cannot iterate."""
    registry = REPO_ROOT / 'rsc' / 'provider' / 'providers.csv'
    try:
        with registry.open(newline='') as f:
            declared = [r['provider'].strip() for r in csv.DictReader(f) if r['provider'].strip()]
    except (OSError, KeyError) as e:
        declared = []
        run('provider: registry parses: rsc/provider/providers.csv', False, str(e), check='provider.registry_parses')
    else:
        run('provider: registry parses: rsc/provider/providers.csv', bool(declared),
            None if declared else 'rsc/provider/providers.csv declares no provider', check='provider.registry_parses')
    named: dict[str, set[str]] = {}
    for tree in ('src/main/cli/browser', 'src/main/browser', 'src/main/cli/agent'):
        for d in members(REPO_ROOT / tree):
            named.setdefault(d.name, set()).add(f'{tree}/{d.name}/')
    for path in sorted((REPO_ROOT / 'src').rglob('*')):
        if path.is_file() and path.suffix in ('.py', '.sh', '.json'):
            for m in re.finditer(r'data/input/([a-z][a-z0-9_-]*)/(?:chat|code)/', path.read_text(errors='ignore')):
                named.setdefault(m.group(1), set()).add(str(path.relative_to(REPO_ROOT)))
    undeclared = {n: sorted(where) for n, where in named.items() if n not in declared}
    run('provider: every provider src/ names is declared in rsc/provider/providers.csv', not undeclared,
        None if not undeclared else '; '.join(f'{n} named by {", ".join(w[:3])}' for n, w in sorted(undeclared.items()))
        + ' - declare it in rsc/provider/providers.csv, or the name is not a provider', check='provider.names_declared')


@check(tier='code', on=['src/main/cli/forge', 'src/test'], says=(
    'forge.aim_one_line_per_issue',
    'forge.issue_is_a_should_with_wired_relations',
    'forge.merge_names_its_issues',
    'forge.squash_read_back',
))
def check_forge_aim(run) -> None:
    """A PR's aim is one line per issue in the aim's one grammar: the merge reads
    the aimed set from it and refuses any other spelling, so that the set the flip
    rewrites and the set the forge closes are one. A body aiming at two issues in one line is
    refused, never read as aiming at one."""
    import importlib
    try:
        aim = importlib.import_module('forge.aim')
    except ModuleNotFoundError:
        run('forge: a PR\'s aim is one line per issue in one grammar', False,
            'src/main/cli/forge has no aim grammar: the merge reads aims by a regex over prose', check='forge.aim_one_line_per_issue')
        return
    one_line_two_issues = '## why\n\n- aims to complete #876 - every effecting verb not on the flow reports through the act\'s one shape - and, with #877 merged, #801, whose every effecting verb then reports\n'  # GitHub's grammar, hashed
    refused = False
    try:
        aim.aimed(one_line_two_issues)
    except ValueError:
        refused = True
    run('forge: a line that aims at two issues is refused', refused,
        None if refused else 'pull/879\'s aim line was read as one aim and issues/801 stayed open', check='forge.aim_one_line_per_issue')
    body = '\n'.join(['Signature: a/b/0123abcd', '', '## why', '', aim.line(876, 'the first should'), aim.line(801, 'the second should'),
                      '', '## what', '', 'a mention wears backticks: `aims to complete #1` is said about, not aimed'])  # GitHub's grammar, hashed
    read = aim.aimed(body)
    run('forge: the aim lines raise writes are the aims merge reads', read == [876, 801],
        None if read == [876, 801] else f'read {read}', check='forge.aim_one_line_per_issue')
    armed = aim.flipped(body)
    flipped_ok = '- closes #876 - the first should' in armed and '- closes #801 - the second should' in armed and aim.PHRASE not in armed.replace('`aims to complete #1`', '')  # GitHub's grammar, hashed
    run('forge: the flip rewrites each aim line to closes and nothing else', flipped_ok,
        None if flipped_ok else f'the armed body reads {armed[:200]}', check='forge.aim_one_line_per_issue')
    # An issue is raised from its should and its relations (issues/887): a title that is not a
    # should, and a relation narrated in prose, are refused before any send.
    try:
        should = importlib.import_module('forge.should')
    except ModuleNotFoundError:
        run('forge: an issue\'s title is a should and its relations are wired, never narrated', False,
            'src/main/cli/forge has no issue grammar: the title and the relations are checked by review alone', check='forge.issue_is_a_should_with_wired_relations')
        return
    def refuses(call) -> bool:
        try:
            call()
        except ValueError:
            return True
        return False
    title_held = (refuses(lambda: should.check_title('the forge noun becomes dev'))
                  and refuses(lambda: should.check_title('the merge should close #801'))  # GitHub's grammar, hashed
                  and not refuses(lambda: should.check_title('an issue should be raised by the forge')))
    run('forge: an issue\'s title is a should and its relations are wired, never narrated', title_held,
        None if title_held else 'a title without the word, or with an issue number, passed as a should', check='forge.issue_is_a_should_with_wired_relations')
    clean = '## currently\n\n### as is\n\n- a fact.\n\n## but, in future\n\n- a should; `part of #1` said about.\n'  # GitHub's grammar, hashed
    body_held = (not refuses(lambda: should.check_body(clean))
                 and refuses(lambda: should.check_body(clean.replace('a fact.', 'a fact, blocked by #3.')))  # GitHub's grammar, hashed
                 and refuses(lambda: should.check_body(clean.replace('a should;', 'a should, part of #740;')))  # GitHub's grammar, hashed
                 and refuses(lambda: should.check_body(clean.replace('## currently', '## currently\n\n### as at\n\nmain @ abc')))
                 and refuses(lambda: should.check_body('## but, in future\n\n- a should.\n\n## currently\n\n### as is\n')))
    run('forge: an issue\'s body is the template\'s sections, and narrates no relation', body_held,
        None if body_held else 'a narrated relation, a hand-written as-at, or sections out of order passed', check='forge.issue_is_a_should_with_wired_relations')

    # The squash step over a stub forge (issues/931): a merge call whose reply is lost over a
    # PR the forge has merged concludes, one over a PR the forge holds open refuses. The
    # fixture is the live bug: pull/930's squash went through, gh's reply was reset, and the
    # merge restored the body and called the squash refused.
    forge_sh = SRC / 'main' / 'cli' / 'forge' / 'forge.sh'
    has_step = re.search(r'^squashed\(\)', forge_sh.read_text(), re.M) is not None
    exits: dict[str, int] = {}
    if has_step:
        import tempfile
        for state in ('MERGED', 'OPEN'):
            with tempfile.TemporaryDirectory() as stub:
                gh = Path(stub) / 'gh'
                gh.write_text('#!/bin/bash\ncase "$1 $2" in "pr merge") exit 1 ;; "pr view") echo ' + state + ' ;; *) exit 1 ;; esac\n')
                gh.chmod(0o755)
                done = subprocess.run(['bash', '-c', 'source "$1"; squashed 1 deadbeef 1 0', '_', str(forge_sh)], capture_output=True, text=True,
                                      env={**{k: v for k, v in os.environ.items() if k != 'CORPUS_YOGA_NO_SEND'},   # the stub forge is local
                                           'PATH': f'{stub}:{os.environ["PATH"]}', tier.DECLARATION: send.dispatched('src/main/cli/forge/merge.json')},
                                      cwd=REPO_ROOT)
                exits[state] = done.returncode
    # The merge's verdict names each aimed issue it closed, and each it did not, by its anchor (issues/1044)
    said = subprocess.run(['bash', '-c', 'source "$1"; merged 7 0123abcd "issues/5 issues/6" "issues/8"', '_', str(forge_sh)],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    named = 'did close issues/5, issues/6; did NOT close issues/8' in said
    run('forge: a merge\'s verdict names each issue it closed and each it did not', named,
        None if named else f'merged 7 with issues/5 and issues/6 closed and issues/8 open says {said[:160]!r}', check='forge.merge_names_its_issues')
    run('forge: a squash whose reply is lost is read back from the forge - merged concludes, open refuses',
        has_step and exits.get('MERGED') == 0 and exits.get('OPEN') == 1,
        'forge.sh has no squashed step: the merge reads gh pr merge\'s exit alone' if not has_step
        else f'over a merged PR the step exited {exits["MERGED"]}, over an open one {exits["OPEN"]}', check='forge.squash_read_back')
