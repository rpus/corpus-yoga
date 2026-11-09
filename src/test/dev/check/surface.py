"""surface.py - the dev gate's checks of the command surface: declarations, help, effects, replies, completions and the laws they cite."""
import ast
import io
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gate import (  # noqa: F401 - the gate's shared vocabulary
    GATE_FILES,
    CLI,
    PLAIN_PHRASE_REMEDY,
    REPO_ROOT,
    SEND_SWITCH,
    SRC,
    check,
    cli,
    cli_completions,
    cli_offer,
    facts,
    is_member,
    members,
    tier,
)


@check(tier='code', on=['src', 'rsc/CALCULUS.md', 'corpus-yoga.code-workspace'], says=(
    'cli.advertised_flags_exist',
    'cli.block_convergence',
    'cli.block_identity_stable',
    'cli.calculus_defined',
    'cli.commands_alphabetical',
    'cli.commands_unique',
    'cli.completions_parse',
    'cli.docstring_flags_advertised',
    'cli.every_form_listed',
    'cli.flag_not_axis_value',
    'cli.help_is_the_declaration',
    'cli.prose_holds_no_pair',
    'cli.step_invokes_verb',
    'cli.subcommands_dispatch',
    'cli.table_parses',
    'cli.target_exists',
    'cli.target_flags_advertised',
    'cli.verb_accepts_command_flags',
    'effects.enact_faces_agree',
    'effects.send_switch_read_once',
    'effects.sends_declared',
    'naming.log_path_derives_from_command',
    'naming.target_stem_matches_command',
    'naming.venv_default_agrees',
    'output.plan_lines_name_their_target',
    'python.pyright_clean',
    'shell.shellcheck_clean',
    'structure.cli_declaration_mirrors_the_api',
    'structure.cli_declaration_validates',
    'structure.file_at_level_of_subject',
))
def check_cli_surface(run) -> None:
    """The corpus-yoga CLI's table (src/main/cli/) is an interface and must not
    lie: it parses, command names are unique, every target exists, every
    calculus term a row cites is defined in rsc/CALCULUS.md (the vocabulary is
    parsed from the document itself), every flag a usage sketch advertises
    appears in the target's source or its stem-sibling .py/.sh pair (wrapper
    and implementation share a stem — the repo idiom), every subcommand VERB it
    advertises appears in the target's own --help (the live dispatch surface —
    a source grep is vacuous for ordinary words like build/accept), and every command
    a declared `step` marks is invoked BY COMMAND AND VERB in the src/main/cli/pipeline/pipeline.sh --plan
    output (which is itself the executing list, so the chain cannot drift, and a step
    cannot quietly drop to a bare noun that the bare=status convention no-ops). Committed
    files and the deterministic plan only, so deterministic on any clone:
    code tier."""
    try:
        cmds = cli.commands()
    except Exception as e:
        run('cli: table parses: src/main/cli/', False, str(e), law='G4', check='cli.table_parses')
        return
    run('cli: table parses: src/main/cli/', True, law='G4', check='cli.table_parses')
    names = [c['command'] for c in cmds]
    dupes = sorted({n for n in names if names.count(n) > 1})
    run('cli: command names unique', not dupes, ', '.join(dupes) if dupes else None,
        law='G4', check='cli.commands_unique')
    # alphabetical by contract: every surface derived from the table
    # (help, synopsis, completion) inherits its order, so the table carries it
    run('cli: commands alphabetical', names == sorted(names),
        None if names == sorted(names) else
        f'first out of order: {next(a for a, b in zip(names, sorted(names)) if a != b)}',
        law='G4', check='cli.commands_alphabetical')
    vocab = cli.calculus_terms()
    for c in cmds:
        target = REPO_ROOT / c['target']
        run(f'cli: {c["command"]}: target exists: {c["target"]}', target.exists(), law='G7', check='cli.target_exists')
        unknown = [t for t in c['calculus'].split() if t not in vocab]
        run(f'cli: {c["command"]}: cited calculus defined', not unknown,
            f'not defined in rsc/CALCULUS.md: {", ".join(unknown)}' if unknown else None,
            law='G6', check='cli.calculus_defined')
        # subcommands and flags are read from src/main/cli/ — the single source the
        # usage is generated from — so there is no usage cell to reconcile it against, and
        # no completeness check: the two cannot drift because there is only one.
        flags = cli.flags_of(c['command'])
        subcommands = cli.subcommands_of(c['command'])
        if not (flags or subcommands) or not target.exists():
            continue
        sources = [target] + [s for s in (target.with_suffix('.py'), target.with_suffix('.sh'))
                              if s != target and s.exists()]
        text = ''.join(s.read_text() for s in sources)
        where = ('not in ' + ' or '.join(str(s.relative_to(REPO_ROOT)) for s in sources) + ': ')
        if flags:
            missing = [f for f in flags if f not in text]
            run(f'cli: {c["command"]}: advertised flags exist', not missing,
                (where + ', '.join(missing)) if missing else None, law='G5', check='cli.advertised_flags_exist')
        # Docstring honesty (issues/33): a module docstring's Usage block is a
        # declared surface too, and nothing read it against the parser —
        # memories' documented three flags no parser defined, and both checks
        # here were satisfied (the declaration honestly advertised none; the lie lived
        # only in the docstring). Every --flag a Usage block cites must be
        # advertised; real ⊆ advertised is held below, so advertised is the one
        # universe a documented flag can exist in.
        doc: set[str] = set()
        for m in re.finditer(r'^Usage.*?(?=\n"""|\n\'\'\'|\Z)', text, flags=re.M | re.S):
            doc.update(re.findall(r'--[a-z][\w-]+', m.group(0)))
        doc.discard('--help')
        undeclared = sorted(doc - set(flags))
        run(f'cli: {c["command"]}: docstring Usage flags advertised', not undeclared,
            f'documented in a Usage block but not declared: {", ".join(undeclared)}'
            if undeclared else None, law='G5', check='cli.docstring_flags_advertised')
        # the target's own --help is the authority on its live surface — fetched
        # once here for both directions of the honesty check
        runner = REPO_ROOT / 'src' / 'run_python_script.sh'
        help_cmd = ([str(runner), str(target), '--help'] if target.suffix == '.py'
                    else [str(target), '--help'])
        proc = subprocess.run(help_cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        help_text = proc.stdout + proc.stderr
        if subcommands:
            # An advertised subcommand must be REALLY dispatched, not a word in the help
            # prose, and a bare-word grep cannot tell the two apart. argparse
            # renders its subparsers as a {a,b,c} choice block — parse it and require
            # each advertised subcommand to be an actual choice. Shell targets carry no such
            # block, so there we fall back to matching their printed usage.
            choice_blocks = re.findall(r'\{([a-z0-9][a-z0-9,_-]*)\}', help_text)
            if choice_blocks:
                real = {v for blk in choice_blocks for v in blk.split(',')}
                missing_sub = [s for s in subcommands if s not in real]
                detail = (f'not real subcommands (target dispatches {sorted(real)}): '
                          f'{", ".join(missing_sub)}') if missing_sub else None
            else:
                # No {…} block: a shell target (subcommands in its printed usage), or a
                # cli.py-targeted row — `cli.py --help` renders the command TABLE, not the
                # parser cli.py builds for a command it handles itself, so that parser's
                # choice block never reaches this text. Accept a subcommand that appears
                # as a word in the target's --help OR as a dispatch literal in its source
                # — either is real evidence it is handled, not prose.
                missing_sub = [s for s in subcommands
                               if not re.search(rf'\b{re.escape(s)}\b', help_text)
                               and not re.search(rf'\b{re.escape(s)}\b', text)]
                detail = (f'{c["target"]} neither prints nor dispatches: {", ".join(missing_sub)}'
                          if missing_sub else None)
            run(f'cli: {c["command"]}: advertised subcommands dispatch', not missing_sub, detail,
                law='G5', check='cli.subcommands_dispatch')
        # The REVERSE direction: every flag the target itself declares must be
        # advertised in the usage cell. Checked one way only, the table may under-tell
        # — a synopsis hiding flags the target accepts — and nothing notices until a
        # reader types one that is not there. Harvest only DECLARING lines: argparse option lines (leading
        # whitespace, then --flag) and invocation lines naming the command or
        # target, with trailing '# …' comments stripped (prose cites foreign
        # flags: `git diff --cached`). Under-harvest is safe — the claim is
        # real ⊆ advertised, so a missed declaration weakens, never falsifies.
        real: set[str] = set()
        for line in help_text.splitlines():
            m = re.match(r'\s+(--[a-z][\w-]*)', line)
            if m:
                real.add(m.group(1))
                continue
            if f'corpus-yoga {c["command"]} ' in line or f'{target.name} ' in line or '$0' in line:
                real.update(re.findall(r'--[a-z][\w-]+', line.split(' # ')[0]))
        real.discard('--help')
        real -= set(cli.root_flags())        # the launcher's flags, said at every level as inherited (issues/973), advertised at the top
        unadvertised = sorted(real - set(flags))
        run(f'cli: {c["command"]}: target flags all advertised', not unadvertised,
            f'target --help declares flags the usage cell omits: {", ".join(unadvertised)}'
            if unadvertised else None, law='G5', check='cli.target_flags_advertised')
        # Positionally usable where advertised (issues/33): the declaration renders a
        # command-level flag beside the verbs and completion offers it after
        # them, but summaries' four lived only on the command parser — argparse
        # hands a subparser everything after the verb token, so the advertised
        # `corpus-yoga summaries sync --summaries-output …` died with `unrecognized
        # arguments`. The observable: an argparse verb's own --help lists every
        # flag that verb accepts, so each command-level flag must appear there
        # (declared_parser.command_parser re-accepts them on each verb). cli.py
        # targets are excluded as above; shell targets parse no verbs.
        cmd_level = [r['arg-name'] for r in cli.command_rows(c['command'])
                     if not r['subcommand'] and r['arg-name'].startswith('--')]
        if cmd_level and subcommands and target.suffix == '.py' and not c['target'].endswith('cli.py'):
            for verb in subcommands:
                vproc = subprocess.run([str(runner), str(target), verb, '--help'],
                                       capture_output=True, text=True, cwd=REPO_ROOT)
                vhelp = vproc.stdout + vproc.stderr
                rejected = [f for f in cmd_level if f not in vhelp]
                run(f'cli: {c["command"]}: {verb} accepts the command-level flags', not rejected,
                    f'`corpus-yoga {c["command"]} {verb}` rejects advertised flag(s): {", ".join(rejected)}'
                    if rejected else None, law='G5', check='cli.verb_accepts_command_flags')
    # The emitted completion is a zsh PROGRAM, not prose — it must parse. A
    # '(--a|--b)' usage can leak '--b)' through flags_of, and what zsh evaluates then
    # fails: completion is lost silently, because nothing else parses it. zsh-less clones skip the parse
    # invisibly (constant label, no detail) so the committed log stays
    # byte-identical; every machine runs macOS, where the check is real.
    import shutil, tempfile
    zsh = shutil.which('zsh')
    parse_ok, parse_err = True, None
    if zsh:
        with tempfile.NamedTemporaryFile('w', suffix='_corpus-yoga', delete=False) as f:
            f.write(cli_offer.completion_script(cmds))
            tmp = f.name
        proc = subprocess.run([zsh, '-n', tmp], capture_output=True, text=True)
        Path(tmp).unlink()
        parse_ok, parse_err = proc.returncode == 0, (proc.stderr.strip() or None)
    run('cli: completions: emitted script parses (zsh -n)', parse_ok,
        parse_err if not parse_ok else None, law='G9', check='cli.completions_parse')

    # A command determines its target's name (issues/40): the target column is verification
    # rather than curation. Every row complies, so the record that declared the ones that
    # did not is gone — the last two left it when `corpus-yoga commands` and `corpus-yoga completions`
    # were extracted to files of their own, and a disposal record with nothing to dispose
    # of is a file that can only rot.
    for c in cmds:
        stem = Path(c['target']).stem
        # Case is part of a name, and the two kinds of target carry different conventions,
        # so each is held to ITS OWN rather than both to a case-folded comparison:
        #   executable → named for its command exactly:      status.sh
        #   document   → the repo's SHOUTING doc convention: CALCULUS.md
        # A .md target is PRINTED, not executed (see dispatch), and all 18 markdown
        # documents here are uppercase — four READMEs, eleven CHANGELOGs, WORKFLOW.
        want = c['command'].upper() if Path(c['target']).suffix == '.md' else c['command']
        run(f'cli: {c["command"]}: target is named for the command', stem == want,
            None if stem == want else
            f'target {c["target"]} has stem `{stem}`, not `{want}` — a command determines '
            f'its target\'s name, so rename the target or the command',
            check='naming.target_stem_matches_command')

    # Shell files are linted by shellcheck rather than by anything hand-rolled here: a
    # second vocabulary to police a first is exactly what a check should not be. It found
    # `corpus-yoga test run` written in backticks inside a double-quoted echo — command
    # substitution, not quoting, so the plan RAN the gate it was describing while
    # promising "nothing executed" — and an `echo "$(cmd)"` wrapping a command that
    # already prints.
    #
    # Absent, it skips with a CONSTANT label and no detail, so the committed report stays
    # byte-identical on a clone without it (the zsh -n precedent). `corpus-yoga status`
    # is the one voice that says whether this machine has it.
    shellcheck = shutil.which('shellcheck')
    # src/ AND rsc/: rsc/test/pre-commit-hook.sh is shell that gets installed and run, and
    # a lint scoped to src/ would leave the one file whose breakage surfaces only at commit
    # time unchecked.
    sh_files = sorted(str(f) for d in ('rsc', 'src') for f in (REPO_ROOT / d).rglob('*.sh'))
    sc_ok, sc_detail = True, None
    if shellcheck and sh_files:
        # -x follows the `# shellcheck source=` directives the sourcing files write;
        # without it those lines are decoration and the sourced vocabulary is unknown
        proc = subprocess.run([shellcheck, '-x', '-f', 'gcc', *sh_files],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        findings = [l for l in proc.stdout.splitlines() if l.strip()]
        sc_ok = not findings
        sc_detail = None if sc_ok else '; '.join(
            f.replace(str(REPO_ROOT) + '/', '') for f in findings[:4])
    run('shell: shellcheck reports nothing', sc_ok, sc_detail,
        check='shell.shellcheck_clean')
    # A command's log path derives from the command (issues/54): having typed `corpus-yoga <noun>
    # <verb>`, a reader can guess where the log went without reading the script that
    # wrote it. Held over the SOURCE — every tmp/logs/ path any file names must open
    # with a command word — because the directories themselves exist only on a machine
    # that has run something, and a check that passes for want of evidence is worse
    # than none. Validation logs are exempt by living under tmp/cache/ beside the datum
    # they memoise: the log IS the memoisation (L1), not run history.
    commands_words = {c['command'] for c in cmds}
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sh', '.applescript', '.md'):
            continue
        # RELATIVE to the repo: an absolute-parts test excluded every file whenever the
        # checkout itself sat under a directory called tmp — which a scratch worktree
        # does, so the check examined nothing and passed. `every expected check ran`
        # caught it; a vacuous check that reports success is worse than no check.
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] in ('tmp', '.git', 'data') or rel.parts[:2] == ('rsc', 'migration'):
            continue                      # a migration names a retired address: that is its purpose
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.finditer(r"tmp/logs/([A-Za-z0-9_.-]+)", text):
            seg = m.group(1)
            ok = seg in commands_words or seg in ('...', '<command>')
            run(f'logs: {rel}: tmp/logs/{seg}/ opens with a command word', ok,
                None if ok else
                f'{rel} writes or names tmp/logs/{seg}/, and `{seg}` is no command — a '
                f"reader cannot derive it from what they typed",
                check='naming.log_path_derives_from_command')

    # One venv, declared in several shell entrypoints and once more for the editor —
    # so they are read and compared here rather than described. A comment naming which
    # files set it is a list that rots: a file is added and nothing points at it.
    venv_defaults = {}
    for sh in sorted((REPO_ROOT / 'src').rglob('*.sh')):
        for m in re.finditer(r'\$\{CORPUS_YOGA_VENV:=([^}]+)\}', sh.read_text()):
            venv_defaults.setdefault(m.group(1), []).append(str(sh.relative_to(REPO_ROOT)))
    agree = len(venv_defaults) == 1
    run('venv: every entrypoint defaults it to the same place', agree,
        None if agree else '; '.join(f'{v} in {", ".join(f_)}' for v, f_ in venv_defaults.items()),
        check='naming.venv_default_agrees')
    if agree:
        declared = next(iter(venv_defaults)).replace('$HOME', '${env:HOME}')
        want = f'{declared}/bin/python'
        # Found by SHAPE: the editor config has one home at the root, and a name here
        # would bind this check to what the repository is called.
        workspaces = sorted(REPO_ROOT.glob('*.code-workspace'))
        found = (re.search(r'"python\.defaultInterpreterPath":\s*"([^"]+)"',
                           workspaces[0].read_text()) if len(workspaces) == 1 else None)
        editor_ok = bool(found) and found.group(1) == want
        if len(workspaces) != 1:
            detail = (f'{len(workspaces)} *.code-workspace at the repository root '
                      f'({", ".join(p.name for p in workspaces) or "none"}) — the editor '
                      'config has one home')
        elif not found:
            detail = (f'{workspaces[0].name} sets no python.defaultInterpreterPath, the '
                      f'entrypoints {want}')
        else:
            detail = (f'{workspaces[0].name} names {found.group(1)}, the entrypoints {want} '
                      '— an editor resolving against a different venv sees different packages')
        run('venv: the editor interpreter is that same venv', editor_ok,
            None if editor_ok else detail, check='naming.venv_default_agrees')

    # A send is refusable through one switch, and src/main/send.py is the only place that
    # reads it out of the environment. One reading means refusal cannot come to mean two
    # things: raise for a send that IS the work, skip for one that only checks stored data.
    #
    # Read by AST, not by pattern. A regex over the literal name is blind to the reading
    # that imports SWITCH and passes it as a variable — which is the reading a second
    # module would most naturally write, having found the constant. Naming the switch in
    # prose stays free; only reaching into the environment for it is confined.
    def _reads_switch(path):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return False
        aliases = {SEND_SWITCH}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'send':
                for a in node.names:
                    if a.name == 'SWITCH':
                        aliases.add(a.asname or a.name)
        for node in ast.walk(tree):
            arg = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ('get', 'getenv') and node.args:
                arg = node.args[0]
            elif isinstance(node, ast.Subscript):
                arg = node.slice
            if isinstance(arg, ast.Constant) and arg.value == SEND_SWITCH:
                return True
            if isinstance(arg, ast.Name) and arg.id in aliases:
                return True
        return False

    # ONE fact, one face per language (the pull/113 census, carried to issues/29): bash cannot
    # import a python module, so before send.sh existed no shell command could honour the
    # switch at all. Two DECLARED readers, each named here, is not the accidental pair
    # this check exists to prevent — that pair is any reader beyond these two.
    faces = {REPO_ROOT / 'src' / 'main' / 'send.py',
             REPO_ROOT / 'src' / 'main' / 'send.sh'}
    readers = sorted(str(f.relative_to(REPO_ROOT))
                     for f in (REPO_ROOT / 'src').rglob('*')
                     if f.is_file() and f not in faces
                     and (_reads_switch(f) if f.suffix == '.py' else
                          f.suffix == '.sh' and re.search(rf'\$\{{?{SEND_SWITCH}', f.read_text())))
    run(f'send: only the two send faces read {SEND_SWITCH}', not readers,
        None if not readers else
        f'{", ".join(readers)} reads the switch directly — python imports may_send (skip '
        f'and pass) or assert_may_send (raise) from src/main/send.py; shell sources '
        f'src/main/send.sh, so refusal cannot come to mean two things by accident',
        check='effects.send_switch_read_once')

    # One contract, two faces (issues/277): enact.sh and enact.py speak the same relay
    # words, and no third file speaks them. The pair's one ruled asymmetry is
    # behavior, not words — sh's query returns the status, py's raises — stated in
    # the faces' own headers; the WORDS are held here.
    enact_faces = {REPO_ROOT / 'src' / 'main' / 'enact.sh',
                   REPO_ROOT / 'src' / 'main' / 'enact.py'}
    relay_words = ('did', 'done', 'did NOT', 'exit ')      # the outcome pairs beneath an act's item (issues/805)
    face_texts = {face: face.read_text() for face in enact_faces}
    unspoken = sorted(f'{face.name} lacks {word!r}'
                      for face, face_text in face_texts.items()
                      for word in relay_words if word not in face_text)
    third_speakers = sorted(str(f.relative_to(REPO_ROOT))
                            for f in (REPO_ROOT / 'src').rglob('*')
                            if f.is_file() and f not in enact_faces
                            and f.suffix in ('.py', '.sh')
                            and re.search(r'^(def (enact|labour|query|quote|quiet)\(|(enact|labour|query|quote|quiet)\(\)\s*\{)',
                                          f.read_text(), re.M))
    run('enact: the two faces speak identical relay words, and only they speak',
        not unspoken and not third_speakers,
        '; '.join(unspoken + [f'{speaker} defines a face' for speaker in third_speakers]) or None,
        check='effects.enact_faces_agree')

    # The forward half of declared sends (issues/29): a target that holds a send face performs
    # sends, and its command must SAY so in the declaration tree. TWO tolerances, both
    # deliberate and both to be retired by the arc's primitives-behind-faces slice:
    # helpers reached through imports are untraced (under-catch, safe), and the hold is
    # COMMAND-level — any one file under src/main/cli/<command>/ carrying `sends` satisfies
    # it, so a single VERB can lose its declaration unnoticed while its siblings keep
    # the command green (the pull/114 review's finding: src/main/cli/forge/sync.json's
    # PATCH-write line, deleted alone, does not trip this). Per-verb needs the check to know which
    # verb sends, which is exactly what declared doors will make knowable.
    undeclared_senders = []
    for c in cli.commands():
        target = REPO_ROOT / c['target']
        sources = [s for s in (target, target.with_suffix('.py'), target.with_suffix('.sh'))
                   if s.exists()]
        text = ''.join(dict.fromkeys(s.read_text() for s in sources))
        if 'send.sh' not in text and 'from send import' not in text:
            continue
        declared = bool(cli.sends_of(c['command'])) or any(
            cli.sends_of(c['command'], v) for v in cli.subcommands_of(c['command']))
        if not declared:
            undeclared_senders.append(c['command'])
    run('send: every command holding a send face declares its sends', not undeclared_senders,
        None if not undeclared_senders else
        f'{", ".join(undeclared_senders)}: the target uses may_send/assert_may_send but no '
        f'declaration in src/main/cli/<command>/ carries a `sends` field — declare each outward '
        f'call where the reader decides to run the verb',
        check='effects.sends_declared')

    # Python is type-checked by pyright — Pylance's own engine — against
    # pyrightconfig.json, the ONE declaration of the import roots that the editor, this
    # gate and any CLI all read. `standard` mode, matching what an editor reports today;
    # strict would demand ~4000 annotations to surface a tail that is currently all
    # false positives (a heterogeneous PROVIDERS dict, and a call dispatched by
    # inspect.signature, neither of which a type checker can follow).
    #
    # --pythonpath names the venv explicitly: without it pyright resolves imports from
    # whatever python is on PATH, and a run without the venv reports 25 errors that are
    # nothing but unresolved third-party packages.
    # The CORPUS_YOGA_VENV the repo builds, ONE resolution for both halves: which pyright runs, and
    # which interpreter it analyses with. Looking pyright up on PATH alone made the check
    # depend on the reader's shell — it ran here only because that shell happens to put
    # the venv first, which is the same accident --pythonpath was added to avoid.
    venv = Path(os.environ.get('CORPUS_YOGA_VENV', str(Path.home() / 'venvs' / 'general')))
    venv_pyright, venv_python = venv / 'bin' / 'pyright', venv / 'bin' / 'python'
    pyright = str(venv_pyright) if venv_pyright.exists() else shutil.which('pyright')
    py_ok, py_detail = True, None
    if pyright:
        cmd = [pyright, '--outputjson']
        if venv_python.exists():
            cmd += ['--pythonpath', str(venv_python)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = None
        if report is not None:
            diags = [d for d in report['generalDiagnostics'] if d['severity'] == 'error']
            py_ok = not diags
            py_detail = None if py_ok else '; '.join(
                f"{d['file'].replace(str(REPO_ROOT) + '/', '')}:"
                f"{d['range']['start']['line'] + 1} {d['message'].splitlines()[0][:60]}"
                for d in diags[:4])
    run('python: pyright reports nothing', py_ok, py_detail, check='python.pyright_clean')

    # Every printed plan line names where its step is implemented (issues/45). The plan is the
    # one place the whole program is listed, and a bare label does not resolve there:
    # `validate` names a file in more than one pipeline. The line carries the path, so a reader needs
    # no rule about which namespace a label is in.
    plan = subprocess.run([str(CLI / 'pipeline' / 'pipeline.sh'), 'run', '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout
    # A STEP LINE is identified by its SHAPE, not by what it happens to carry: plan_line
    # pads the label into a column, so a line with a gap of two or more spaces between two
    # non-space tokens is a step. Selecting instead on "carries a src/ path" would let a
    # step line naming no file pass by never being looked at — which is how two prep-phase
    # lines printed a script path in the label column, with no file column at all, for as
    # long as this check has existed.
    step_lines = [l for l in plan.splitlines() if re.search(r'\S {2,}\S', l)]
    run('plan: some line is a step', bool(step_lines),
        None if step_lines else 'no plan line has the padded shape plan_line prints',
        law='G16', check='output.plan_lines_name_their_target')
    named = r'\S\s{2,}((?:src|rsc)/\S+?)(?:\s|$)'
    for line in step_lines:
        match = re.search(named, line)
        typeable = line.strip().startswith('corpus-yoga ')
        ok = bool(match) or typeable
        run(f'plan: `{line.strip()[:44]}` says where it is implemented', ok,
            None if ok else
            f'`{line.strip()}` is a step line naming neither a repo-relative file nor a '
            f'corpus-yoga command — a reader cannot tell whether to type it or where to find it',
            law='G16', check='output.plan_lines_name_their_target')
        if not match:
            continue
        impl = match.group(1)
        exists = (REPO_ROOT / impl).is_file()
        run(f'plan: {impl}: the file the line names exists', exists,
            None if exists else f'`{line.strip()}` names {impl}, which is not a file',
            law='G16', check='output.plan_lines_name_their_target')
    # A step that is also a command prints AS that command — the line says it is typeable
    # by being typeable, rather than by a marker a legend would have to explain.
    for st in cli.steps():
        want = f'corpus-yoga {st["command"]} {st["subcommand"]}'
        run(f'plan: `{want}` is printed as the command it is', want in plan,
            None if want in plan else f'the plan names {st["command"]} without `corpus-yoga`, so '
            f'nothing distinguishes it from a label you cannot type',
            law='G16', check='output.plan_lines_name_their_target')

    # A file lives at the level of its subject (issues/41). Which tier imports a module is a
    # fact about the import graph, not a curated list — so this needs no vocabulary: a
    # module both tiers import belongs at src/, one only its own tier imports belongs in
    # that tier. src/ was holding validation_matrix by instinct and declared_parser one
    # level down, with the same cross-tier subject and the opposite placement.
    src_root = REPO_ROOT / 'src'
    modules = {p.stem: p for p in src_root.rglob('*.py')
               if '__pycache__' not in p.parts}
    importers: dict[str, set[str]] = {name: set() for name in modules}
    for path in modules.values():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        rel = path.relative_to(src_root)
        if path.resolve() in GATE_FILES:
            continue   # the gate imports what it CHECKS, which is not a dependency: it
                       # reaches into markdown_projection, cli and safari to hold
                       # them to their contracts, and counting that as use would put
                       # every checked module at src/
        tier = 'test' if rel.parts[0] == 'test' else 'main'
        for node in ast.walk(tree):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                     [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for n in names:
                if n in importers and modules[n] != path:
                    importers[n].add(tier)
    for name, tiers in sorted(importers.items()):
        if not tiers:
            continue                      # imported by nothing: its own entrypoint
        rel = modules[name].relative_to(src_root)
        at_root = len(rel.parts) == 1
        shared = len(tiers) > 1
        ok = at_root == shared
        run(f'src: {rel}: lives at the level of its subject', ok,
            None if ok else
            (f'imported from {" and ".join(sorted(tiers))} but sits inside one tier — a '
             f'module both tiers import belongs at src/'
             if shared else
             f'imported only from the {tiers.pop()} tier but sits at src/, which is for '
             f'modules both tiers import'),
            check='structure.file_at_level_of_subject')

    # The declaration tree IS the API (issues/58): every command is a file or a directory
    # under src/main/cli/, every directory holds its own <command>.json plus one file per
    # subcommand, and nothing else lives there. Uniqueness and ordering need no check —
    # a directory cannot hold two entries of one name, and a listing has no out-of-order
    # state to be in (G4, by construction rather than by assertion).
    # The tree shares src/main/cli/ with the machinery that reads it (content type is
    # not purpose: the declarations are the program's self-description, so they live
    # with the program) — a stray is anything that is neither a declared command's
    # directory, a schema, a known document, a machinery source file, nor python's cache.
    # Admitting .py/.sh leaves that species to xref: an unreferenced source moves the
    # committed score, and THAT is the check that objects — absorb a stray into the
    # xref expectation and nothing else here will.
    cli_root = CLI  # noqa: kept as a local name for the checks below
    declared = {c['command'] for c in cmds}
    stray = sorted(p.name for p in cli_root.iterdir()
                   if (p.is_file() or is_member(p))
                   and p.name not in ('README.md', 'readings.md', 'corpus-yoga.json', '__pycache__')
                   and not p.name.endswith('.schema.json')
                   and p.suffix not in ('.py', '.sh')
                   and p.name not in declared)
    run('cli: src/main/cli/ holds declarations, machinery, and nothing else', not stray,
        None if not stray else f'{", ".join(stray)} is neither a command, a known document, '
        'nor machinery',
        law='G3', check='structure.cli_declaration_mirrors_the_api')
    # ONE shape, whether or not the command has verbs: a directory holding its own
    # declaration and one file per verb. Two shapes meant gaining a first verb converted
    # a file into a directory before the verb could be added — against the whole point,
    # which is that adding a verb is adding a file.
    for c in cmds:
        name = c['command']
        d = cli_root / name
        want = {f'{name}.json'} | {f'{v}.json' for v in cli.subcommands_of(name)}
        have = {f.name for f in d.glob('*.json')} if d.is_dir() else set()
        run(f'cli: {name}: its directory holds exactly its declarations', have == want,
            None if have == want else
            f'{d.relative_to(REPO_ROOT)} holds {sorted(have)}, declared {sorted(want)}',
            law='G3', check='structure.cli_declaration_mirrors_the_api')

    # Every declaration validates against the schema beside it. The schemas live in
    # src/main/cli/ and not under rsc/schema/, which is the DATA domain: this is the repo's
    # own interface, not corpus data. additionalProperties is false in all three, so a
    # field nobody reads cannot accumulate in a file nobody would notice it in.
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT4
    schemas = {k: json.loads((cli_root / f'{k}.schema.json').read_text())
               for k in ('command', 'subcommand', 'argument', 'root') if (cli_root / f'{k}.schema.json').is_file()}
    # the same resolution idiom validate.py uses — RefResolver is deprecated and warns,
    # and a warning on stderr would land in a committed report that must stay byte-stable
    registry = Registry().with_resource(
        'argument.schema.json',
        Resource.from_contents(schemas['argument'], default_specification=DRAFT4))
    # the top's own declaration (issues/807): what the tool is, and the commands bare `corpus-yoga` suggests
    top_declaration = cli_root / 'corpus-yoga.json'
    if 'root' in schemas and top_declaration.is_file():
        top_errors = sorted(jsonschema.Draft4Validator(schemas['root'], registry=registry).iter_errors(json.loads(top_declaration.read_text())), key=lambda e: list(e.path))
        unknown = [name for name in json.loads(top_declaration.read_text()).get('suggests', []) if name not in {c['command'] for c in cmds}]
        run('cli: corpus-yoga.json: validates as the top\'s declaration, suggesting declared commands', not top_errors and not unknown,
            None if not top_errors and not unknown else f'{top_errors[0].message}' if top_errors else f'suggests {unknown}, which no command is',
            law='G3', check='structure.cli_declaration_validates')
    else:
        run('cli: corpus-yoga.json: validates as the top\'s declaration, suggesting declared commands', False,
            'the top has no declaration: what bare corpus-yoga says is a tuple in cli.py', law='G3', check='structure.cli_declaration_validates')
    for c in cmds:
        name = c['command']
        d = cli_root / name
        decl = [(d / f'{name}.json', 'command')] if d.is_dir() else [(cli_root / f'{name}.json', 'command')]
        if d.is_dir():
            decl += [(f, 'subcommand') for f in sorted(d.glob('*.json')) if f.stem != name]
        for path, kind in decl:
            validator = jsonschema.Draft4Validator(schemas[kind], registry=registry)
            errors = sorted(validator.iter_errors(json.loads(path.read_text())),
                            key=lambda e: list(e.path))
            run(f'cli: {path.relative_to(cli_root)}: validates as a {kind} declaration',
                not errors,
                None if not errors else
                f'{errors[0].message} at {"/".join(str(x) for x in errors[0].path) or "(root)"}',
                law='G3', check='structure.cli_declaration_validates')

    # Every typeable form is listed (issues/85). The bare noun is an alternative like any
    # other, so the forms number one per subcommand PLUS one; what -h shows of them is
    # held above (cli.help_is_the_declaration).
    for c in cmds:
        forms = cli.command_forms(c['command'])
        expected = len([s for s in cli.subcommands_of(c['command'])]) + 1
        run(f'cli: {c["command"]}: every form is rendered (bare + one per subcommand)',
            len(forms) == expected,
            None if len(forms) == expected else
            f'{len(forms)} form(s) for {expected} expected — the bare noun is not '
            f'conditional in the grammar, so it cannot be conditional in the derivation',
            law='G3', check='cli.every_form_listed')

    # Every help face is the declaration, said by the printer (issues/794): `corpus-yoga <command> -h`
    # loads as what the walk shows at /<command>/help under the command's name, with each
    # form beside its summary; `corpus-yoga -h` loads as every command under `corpus-yoga:`,
    # each with its summary - the bare word's shape, whole.
    import yaml
    help_of = getattr(cli, 'help_of', None)
    env = {**os.environ, 'CORPUS_YOGA_NO_SEND': '1'}
    def loaded(*words):
        said = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), *words], capture_output=True, text=True, env=env, cwd=REPO_ROOT, timeout=120).stdout
        try:
            return yaml.safe_load(said), said
        except yaml.YAMLError as error:
            return f'does not load - {getattr(error, "problem", error)}', said
    menu, said = loaded('-h')
    root_declared = json.loads((CLI / 'corpus-yoga.json').read_text()) if (CLI / 'corpus-yoga.json').is_file() else {}
    expected_menu = {'corpus-yoga': root_declared.get('summary'), **{f'corpus-yoga {c["command"]}': c['summary'] for c in cmds},
                     **{f'corpus-yoga <command> {a["name"]}': a['help'] for a in root_declared.get('args', [])}}
    run('cli: corpus-yoga -h is every command under corpus-yoga, each with its summary', menu == expected_menu,
        None if menu == expected_menu else f'it says {str(menu)[:160] if isinstance(menu, str) else said.strip()[:160]!r}', law='G8', check='cli.help_is_the_declaration')
    for c in cmds:
        if help_of is None:
            run(f'cli: {c["command"]}: -h is its declaration, said by the printer', False,
                'cli has no help_of: -h is prose of its own, and does not load', law='G8', check='cli.help_is_the_declaration')
            continue
        shown, said = loaded(c['command'], '-h')
        declared = {c['command']: help_of(c['command'])}
        forms = [declared[c['command']].get('form')] + [v.get('form') for v in declared[c['command']].get('verbs', {}).values()]
        why = (f'it says {shown}' if isinstance(shown, str)
               else f'it loads as other than the declaration: {str(shown)[:160]}' if shown != declared
               else f'the forms it shows are {forms}, where the declaration generates {cli.command_forms(c["command"])}'
               if forms != cli.command_forms(c['command']) else None)
        run(f'cli: {c["command"]}: -h is its declaration, said by the printer', why is None, why, law='G8', check='cli.help_is_the_declaration')

    # A declaration's prose holds no colon followed by a space, no em dash and no hash after
    # a space - YAML's comment (issues/795): each summary, help, argument, send and explanation is
    # one plain sentence, so help, tab, the walk and the bare word say it unquoted.
    def prose(d: dict):
        yield 'summary', d.get('summary', '')
        yield 'help', d.get('help', '')
        for a in d.get('args', []):
            yield f'argument {a.get("name")}', a.get('help', '')
        for call, occasions in (d.get('sends') or {}).items():
            for occasion in occasions:
                yield f'send {call}', occasion
        for topic, said in (d.get('explanation') or {}).items():
            if isinstance(said, dict):
                for inner, sentence in said.items():
                    yield f'explanation {topic} / {inner}', sentence
            else:
                yield f'explanation {topic}', said
    for declared in sorted(CLI.glob('*/*.json')):
        faults = [f'{where}: {text[:80]}' for where, text in prose(json.loads(declared.read_text()))
                  if text and (': ' in text or text.endswith(':') or ' #' in text or '\u2014' in text)]
        run(f'cli: {declared.relative_to(CLI)}: its prose holds no colon followed by a space, no em dash and no hash after a space', not faults,
            None if not faults else '; '.join(faults)[:300] + ' - ' + PLAIN_PHRASE_REMEDY, check='cli.prose_holds_no_pair')

    # G21: an axis is an arg-type enumeration (`API|DOM`), and a flag named for one of
    # its values reads as a restriction to that value while behaving as an addition. Held
    # per command, over the declaration alone — the same table the surface is derived from.
    for cmd in sorted({r['command'] for r in cli.help_rows()}):
        rows = [r for r in cli.help_rows() if r['command'] == cmd]
        values = {v.strip().lower() for r in rows for v in (r['arg-type'] or '').split('|')
                  if v.strip() and '<' not in v}
        flags = [r['arg-name'] for r in rows if (r['arg-name'] or '').startswith('--')]
        clash = sorted(f for f in flags if f.lstrip('-').lower() in values)
        run(f'cli: {cmd}: no flag names a value of its own axis', not clash,
            None if not clash else
            f'{", ".join(clash)} names a value the command already enumerates — a reader '
            f'takes it for a restriction to that value, and the restriction it displaces '
            f'becomes unsayable', law='G21', check='cli.flag_not_axis_value')

    # G20, over a SYNTHETIC ~/.zshrc — the property is about the pure function, and the
    # gate must not read (much less converge) the machine's real shell config. The stale
    # marker below carries advice other than the one install writes: an earlier version's
    # wording is the case that escaped.
    stale = '# corpus-yoga tab-completion (advice an earlier corpus-yoga wrote)'
    block = ['fpath=(~/x $fpath)', "alias corpus-yoga='~/x/corpus-yoga'", cli_completions.COMPLETION_END]
    synthetic = ['# unrelated', '', stale, *block, '', cli_completions.COMPLETION_MARKER, *block, '',
                 'autoload -Uz compinit', 'compinit']
    kept, _ = cli_completions.without_completion_block(synthetic)
    # survivors counted by a LITERAL test-side predicate, never by the function under
    # test: asking cli.is_completion_marker what survived is asking the bug whether it
    # is present, and the answer under the old code was "converged" while the stale
    # block sat in the file
    left = [line for line in kept if line.startswith('# corpus-yoga tab-completion')]
    run('cli: completions: a marker with different advice is still the block',
        cli_completions.is_completion_marker(stale),
        None if cli_completions.is_completion_marker(stale) else
        f'{stale!r} is not recognised — identity is matching advice, so every block an '
        f'earlier version wrote is orphaned: install duplicates it, uninstall leaves it, '
        f'status calls a wired shell unwired', law='G20', check='cli.block_identity_stable')
    run('cli: completions: install converges on ONE block', not left,
        None if not left else f'{len(left)} block(s) survive removal: {left} — removing one '
        f'and writing one is not idempotence when two exist',
        law='G20', check='cli.block_convergence')
    run('cli: completions: the end marker does not open a block',
        not cli_completions.is_completion_marker(cli_completions.COMPLETION_END),
        None if not cli_completions.is_completion_marker(cli_completions.COMPLETION_END) else
        f'{cli_completions.COMPLETION_END!r} matches the start-marker test — a block would end where it '
        f'begins and removal would take the wrong extent',
        law='G20', check='cli.block_identity_stable')

    # The run pipeline's command-backed steps (the declared `step`). Each must
    # appear in `src/main/cli/pipeline/pipeline.sh --plan` as a line naming the COMMAND and its VERB — so the
    # plan speaks the command surface a reader would type, and a step can never invoke
    # a noun bare, which the bare-noun=status convention silently turns into a no-op.
    stepped = cli.steps()
    if not stepped:
        return
    plan = subprocess.run([str(CLI / 'pipeline' / 'pipeline.sh'), '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout
    for s in stepped:
        cmd, sub = s['command'], s['subcommand']
        # the plan line is the step label then its non-path args (steps.sh): the label
        # must BE the command, and the verb must be among the args after it
        # `corpus-yoga ` prefixes a step that IS a command (issues/45), which is how the plan says the
        # line is typeable — so the invocation it must name is the command form
        ok = bool(re.search(rf'^\s*(corpus-yoga )?{re.escape(cmd)}\b.*\b{re.escape(sub)}\b', plan, re.M))
        run(f'cli: {cmd}: run step invokes `{cmd} {sub}` in plan', ok,
            None if ok else f'no `{cmd} … {sub}` line in `src/main/cli/pipeline/pipeline.sh --plan` — a bare '
            f'`{cmd}` step would silently be a status no-op', law='G10', check='cli.step_invokes_verb')


@check(tier='code', on=['src/main/cli'], says=(
    'cli.refusal_is_the_declaration',
    'cli.verb_help_answered',
    'cli.verb_help_is_the_nouns_entry',
))
def check_cli_verb_help(run) -> None:
    """Every verb answers -h from its declaration, and what it answers is the verb's
    entry of the noun's help through the one printer: `corpus-yoga <command> <verb> -h`
    is invoked live, as the reader types it, and must print exactly the generated parser's
    own help and exit 0; and that help, in process, is the printer's render of the entry
    `corpus-yoga <command> -h` holds for the verb, one line a fact - never argparse's own
    prose, which says the verb in a second grammar and paints a terminal in colour since
    python 3.14. A verb-level -h
    never reaches a verb's own argv, so an enacting verb cannot take a flag-shaped token as
    its argument and start its chain. Live and
    local: every parser exits on -h before any verb body runs, so nothing here reaches
    the network or an enacting step."""
    import argparse
    from declared_parser import command_parser, verb_parser
    sys.path.insert(0, str(SRC / 'main'))
    import importlib
    facts = importlib.import_module('facts')
    env = {**os.environ, 'CORPUS_YOGA_NO_SEND': '1'}
    for c in cli.commands():
        # a python target parses through command_parser, whose subparsers re-accept the
        # command's own flags after the verb (issues/33) and say so; a bash target's verb
        # parses through verb_parser, whole from the verb's rows alone
        whole = c['target'].endswith('.py') and not c['target'].endswith('cli.py')
        parsers = (next(a for a in command_parser(c['command'])._actions if isinstance(a, argparse._SubParsersAction)).choices
                   if whole and cli.subcommands_of(c['command']) else {})
        declared = cli.help_of(c['command'])
        if cli.subcommands_of(c['command']):
            run(f'cli: {c["command"]}: help says the flags every level inherits from the launcher', 'inherited' in declared,
                None if 'inherited' in declared else 'the command\'s help has no inherited: head',
                check='cli.verb_help_is_the_nouns_entry')
        for verb in cli.subcommands_of(c['command']):
            selected = {**({'inherited': declared['inherited']} if 'inherited' in declared else {}),
                        'verbs': {verb: declared['verbs'][verb]}}
            if whole:
                selected = {**{key: declared[key] for key in ('arguments', 'defaults') if key in declared}, **selected}
            # at the narration depth the gate itself stands at: a verb run as a step of another
            # verb says its lines beneath the outer record, help included, and the merge's data
            # gate runs this gate three verbs deep
            expected = '\n'.join(facts.lines({c['command']: selected}, facts.depth(), width=None)) + '\n'
            generated = (parsers[verb] if whole else verb_parser(c['command'], verb)).format_help()
            run(f'cli: {c["command"]} {verb}: -h is the verb\'s entry of the noun\'s help', generated == expected,
                None if generated == expected else f'the generated parser says {generated.splitlines()[0]!r}',
                check='cli.verb_help_is_the_nouns_entry')
            proc = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), c['command'], verb, '-h'],
                                  capture_output=True, text=True, cwd=REPO_ROOT, env=env)
            ok = proc.returncode == 0 and proc.stdout == generated
            detail = None
            if not ok:
                first = ((proc.stdout + proc.stderr).strip().splitlines() or ['(no output)'])[0]
                detail = (f'exit {proc.returncode}, first line {first!r} - expected the '
                          f"declaration's generated parser (declared_parser.verb_parser)")
            run(f'cli: {c["command"]} {verb}: -h answered from the declaration', ok,
                detail, law='G5', check='cli.verb_help_answered')
    # A refusal restates the declaration (issues/973): argv the declaration does not express is
    # refused with the verb's form and what it requires, as facts on stderr, and the effect
    # line `<act>: NOT DONE - <what was refused>` closes the record - never argparse's usage
    # block, never "the verb handed up no effect line". One probe per parser path: a bash
    # verb through parse_argv, a python verb's own parser, a python command's subparser;
    # each refuses before any verb body runs.
    for words, message in ((['agent', 'capture'], 'one of the arguments --provider --all is required'),
                           (['cache', 'sync', '--nonsense'], 'unrecognized arguments: --nonsense'),
                           (['store', 'clean', '--nonsense'], 'unrecognized arguments: --nonsense')):
        command, verb = words[0], words[1]
        proc = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), *words], capture_output=True, text=True, cwd=REPO_ROOT, env=env)
        entry = cli.help_of(command)['verbs'][verb]
        form = f"form: {entry['form']}"
        wanted = [form] + (['required:'] if entry.get('required') else [])
        said = (proc.stdout + proc.stderr).splitlines()    # the launcher folds the act's stderr into its record
        missing = [line for line in wanted if not any(line_said.strip() == line for line_said in said)]
        effect = f'{command} {verb}: NOT DONE - {message}'
        # the effect closes the launcher's record on stdout where it wrapped the act; a query verb
        # is not wrapped, and its refusal closes on stderr
        last = ((proc.stdout.strip() or proc.stderr.strip()).splitlines() or [''])[-1]
        ok = proc.returncode != 0 and not missing and last == effect
        detail = None if ok else f'exit {proc.returncode}; the record lacks {missing}; the last line is {last!r}'
        run(f'cli: {" ".join(words)}: refused with the declaration', ok, detail, check='cli.refusal_is_the_declaration')


@check(tier='code', says=('cli.exclusive_class_parses',), on=['src/main/cli', 'src/declared_parser.py'])
def check_cli_exclusive_classes(run) -> None:
    """Every declared 1/-class parses as promised, IN PROCESS on the generated
    parser: each member alone (with the verb's other required arguments
    supplied) is accepted, and two members together are refused. A valid
    exclusive invocation is accepted as well as an invalid one refused, which no
    help-based check can see.
    parse_args never dispatches anything: hermetic by construction."""
    from declared_parser import verb_parser

    def minimal(row):
        return [row['arg-name']] + (['x'] if row['arg-type'] else [])

    for c in cli.commands():
        for verb in cli.subcommands_of(c['command']):
            rows = [r for r in cli.command_rows(c['command'])
                    if r['subcommand'] == verb and r['arg-name']]
            classes: dict[str, list[dict]] = {}
            for r in rows:
                if '/' in r['cardinality']:
                    classes.setdefault(r['cardinality'], []).append(r)
            if not classes:
                continue
            required = [t for r in rows if r['cardinality'] == '1' for t in minimal(r)]
            def parses(argv):
                # A probe's expected refusal is this check's evidence, never the
                # gate's output (issues/484): argparse writes the refusal to stderr
                # before the SystemExit caught here, so the probe runs under a
                # swallowed stderr and leaves no trace in the log.
                import contextlib
                import io
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        verb_parser(c['command'], verb).parse_args(argv)
                    return True
                except SystemExit:
                    return False
            for card, members in classes.items():
                accepted = [r['arg-name'] for r in members
                            if not parses(required + minimal(r))]
                run(f'cli: {c["command"]} {verb}: each {card} member parses alone',
                    not accepted,
                    f'refused despite the class: {", ".join(accepted)}' if accepted else None,
                    law='G5', check='cli.exclusive_class_parses')
                pair = required + minimal(members[0]) + minimal(members[1])
                run(f'cli: {c["command"]} {verb}: {card} members refuse together',
                    not parses(pair), None, law='G5', check='cli.exclusive_class_parses')


@check(tier='code', on=['src/main/cli'], says=(
    'effects.consumer_reads',
    'effects.extent_covered',
    'effects.writers_disjoint',
))
def check_effects(run):
    """The rwx triad's first gate: every declared w prefix is
    claimed by at most one COMMAND — exactly or by containment. Any verb carrying a
    step tag may nest inside `pipeline run`'s w (the pipeline writes through its
    steps); verbs of one command
    share its workshop; every other containment is two hands on one file."""
    cli_root = CLI  # noqa: kept as a local name for the checks below
    claims = []
    unread = []
    for f in sorted(cli_root.glob('*/*.json')):
        d = json.loads(f.read_text())
        owner = f'{f.parent.name} {f.stem}' if f.stem != f.parent.name else f.parent.name
        for w in d.get('w', []):
            claims.append((owner, w.rstrip('/'), bool(d.get('step')),
                           (f.parent.name, f.stem) == ('pipeline', 'run'), f.parent.name))
        # a consumed prefix is a dequeue from another command's w (issues/687): no claim on
        # the file, but the consumer reads what it removes - held here
        for c in d.get('consumes', []):
            if not any(c.rstrip('/') == r.rstrip('/') or c.startswith(r.rstrip('/') + '/') for r in d.get('r', [])):
                unread.append(f'{owner} consumes:{c} without an r row covering it')
    bad = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            a, b = claims[i], claims[j]
            if a[0] == b[0]:
                continue
            # ownership is per-COMMAND: two verbs of one command share its workshop
            # (site render and indexing capture both stage tmp/cache/dashboard — one owner)
            if a[4] == b[4]:
                continue
            pa, pb = a[1], b[1]
            if pa == pb or pa.startswith(pb + '/') or pb.startswith(pa + '/'):
                if (a[3] and b[2]) or (b[3] and a[2]):
                    continue   # a pipeline containing its own declared step's w
                bad.append(f'{a[0]} w:{pa} ∩ {b[0]} w:{pb}')
    run('effects: writers are disjoint (each w prefix claimed once)',
        not bad, '; '.join(bad[:5]) if bad else None, law='L6',
        check='effects.writers_disjoint')
    run('effects: every consumed prefix is read by its consumer',
        not unread, '; '.join(unread[:5]) if unread else None, law='L6',
        check='effects.consumer_reads')

    # -- extent coverage (issues/430): the suspicion list as a check ---------------
    # A path-shaped literal in a command's machinery that no declared r/w row
    # covers is either an undeclared effect or a stale spelling - both are
    # registry defects. The list is mechanical; the row judgment stays human:
    # rows are truer than literals, so a flagged path is fixed by declaring it
    # or by correcting the machinery, never by weakening the scan. Tolerances,
    # stated: literals composed from non-root variables (root / 'claude' / ...)
    # and paths built by helpers a command imports are not seen; targets under
    # src/test are not scanned (the gate names every path as its subject).
    roots = ('data', 'tmp', 'ext', 'rsc')
    ignore = ('tmp/logs',)          # the logging convention: never a declared row
    sh_token = re.compile(
        r'(?:^|[\s"\'=(:/])((?:data|tmp|ext|rsc)/[A-Za-z0-9_.\-/]*[A-Za-z0-9_\-]|machine-name\.txt)')

    def py_literals(path: Path):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return
        doc_ids = set()
        # a nested Div chain is a PREFIX of its parent chain - only the maximal
        # chain names the path (REPO / 'data' / 'output' / 'markdown' would
        # otherwise also yield data/output and data)
        div_lefts = {id(n.left) for n in ast.walk(tree)
                     if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.body and isinstance(node.body[0], ast.Expr) \
                        and isinstance(node.body[0].value, ast.Constant) \
                        and isinstance(node.body[0].value.value, str):
                    doc_ids.add(id(node.body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
                s = node.value
                if '\n' in s or ' ' in s:
                    continue          # prose and blobs; a subject path is one token
                if s.split('/')[0] in roots and '/' in s or s == 'machine-name.txt':
                    yield s.rstrip('/'), node.lineno
            elif isinstance(node, ast.JoinedStr) and node.values \
                    and isinstance(node.values[0], ast.Constant) \
                    and isinstance(node.values[0].value, str):
                s = node.values[0].value
                if ' ' not in s and s.split('/')[0] in roots and '/' in s:
                    yield s.rstrip('/'), node.lineno
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) \
                    and id(node) not in div_lefts:
                # REPO / 'data' / 'input' - join the leading Constant chain
                parts, cur = [], node
                while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
                    if isinstance(cur.right, ast.Constant) and isinstance(cur.right.value, str):
                        parts.append(cur.right.value)
                    else:
                        parts.append(None)
                    cur = cur.left
                parts.reverse()
                while parts and parts[-1] is None:
                    parts.pop()
                if parts and all(isinstance(x, str) for x in parts) and parts[0] in roots and len(parts) > 1:
                    yield '/'.join(parts), node.lineno

    def sh_literals(path: Path):
        # report prose is not an effect: a path spoken by echo/printf or the
        # report helpers (ok/info/bad/todo) teaches the reader, touches nothing
        prose = re.compile(r'\b(?:echo|printf|ok|info|bad|todo|warn|note)\b')
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if line.lstrip().startswith('#'):
                continue
            for m in sh_token.finditer(line):
                if prose.search(line[:m.start(1)]):
                    continue
                yield m.group(1).rstrip('/'), i

    uncovered = []
    for cmd_dir in members(cli_root):
        rows, machinery = set(), set()
        for j in cmd_dir.glob('*.json'):
            d = json.loads(j.read_text())
            rows |= {x.rstrip('/') for x in d.get('r', []) + d.get('w', []) + d.get('consumes', [])}
            tgt = d.get('target')
            if (tgt and not tgt.startswith('src/test/')
                    and tgt.endswith(('.py', '.sh', '.applescript'))
                    and Path(REPO_ROOT, tgt).exists()):
                machinery.add(Path(REPO_ROOT, tgt))
        for pat in ('*.py', '*.sh', '*.applescript'):
            machinery |= {f for f in cmd_dir.rglob(pat) if '__pycache__' not in f.parts}
        def covered(p):
            if any(p == q or p.startswith(q + '/') for q in ignore):
                return True
            return any(p == q or p.startswith(q + '/') or q.startswith(p + '/') for q in rows)
        for f in sorted(machinery):
            lits = py_literals(f) if f.suffix == '.py' else sh_literals(f)
            for lit, line in lits:
                if not covered(lit):
                    uncovered.append(f'{cmd_dir.name}: {lit} ({f.relative_to(REPO_ROOT)}:{line})')
    uncovered = sorted(set(uncovered))
    run('effects: every path-shaped literal in a command\'s machinery is covered by its declared rows',
        not uncovered,
        ('; '.join(uncovered[:8]) + (f'; ... {len(uncovered)} total' if len(uncovered) > 8 else '')) if uncovered else None,
        check='effects.extent_covered')


@check(tier='code', on=['src/main/facts.py', 'src/main/cli'], says=(
    'cli.every_act_declares_its_would',
    'status.now_is_gathered_from_the_body',
))
def check_acts_said_once(run) -> None:
    """What an act would do is said once: every acting verb declares its words,
    `would`, in its own declaration, and a status names an act as one value - the command
    and what it acts on - whose words are read from there; a noun's now: is every act its
    body names, gathered, never composed beside it."""
    sys.path.insert(0, str(SRC / 'main'))
    import facts
    cli_root = SRC / 'main' / 'cli'
    silent = []
    for declaration in sorted(cli_root.glob('*/*.json')):
        if declaration.stem == declaration.parent.name:
            continue
        declared = json.loads(declaration.read_text())
        if not isinstance(declared, dict) or not any(declared.get(k) for k in ('w', 'x', 'sends', 'consumes')):
            continue
        if not str(declared.get('would', '')).startswith('would '):
            silent.append(f'{declaration.parent.name} {declaration.stem}')
    run('cli: every acting verb declares what it would do, in its own declaration', not silent,
        None if not silent else f'{len(silent)} acting verb(s) declare no would - {", ".join(silent[:6])}', check='cli.every_act_declares_its_would')
    would, now_of = getattr(facts, 'Would', None), getattr(facts, 'now_of', None)
    if would is None or now_of is None:
        run("status: a noun's now: is every act its body names, gathered", False,
            'src/main/facts.py has no Would and no now_of: each noun composes its now: beside its body', check='status.now_is_gathered_from_the_body')
        return
    @dataclass
    class Body:
        first: object
        rest: list
        now: object = None
    one, other = 'tmp/logs/site/one', 'tmp/logs/site/other'
    body = Body({'a': {'remedy': would('corpus-yoga logs clean', {one: 1})}},
                [{'remedy': would('corpus-yoga logs clean', {other: 1})}, {'b': {'remedy': would('corpus-yoga logs clean', {one: 1})}}],
                {'corpus-yoga logs clean': {'would remove': {'tmp/logs/site/elsewhere': 1}}})
    gathered = now_of(body)
    said = facts.plain({'remedy': would('corpus-yoga logs clean', {one: 1})})
    want = {'corpus-yoga logs clean': {'would remove': {one: 2, other: 1}}}
    same = gathered == want and said == {'remedy': {'corpus-yoga logs clean': {'would remove': {one: 1}}}}
    run("status: a noun's now: is every act its body names, gathered", same,
        None if same else f'gathered {gathered!r} and said {said!r}', check='status.now_is_gathered_from_the_body')


@check(tier='code', says=('verbs.status_is_the_dry_run',), on=['src/main/cli'])
def check_status_is_the_dry_run(run) -> None:
    """A verb that takes --apply has no dry rendering of its own: its noun's status says
    what it would do, and the verb acts, so no declaration under src/main/cli carries the
    flag. A verb's own dry rendering would restate a
    section its noun's status says."""
    own = sorted(str(p.relative_to(REPO_ROOT)) for p in CLI.glob('*/*.json')
                 if any(a.get('name') == '--apply' for a in json.loads(p.read_text()).get('args', [])))
    run('verbs: no declaration takes --apply, the noun\'s status being the dry run', not own,
        None if not own else 'these take --apply and render a dry run of their own: ' + ', '.join(own),
        check='verbs.status_is_the_dry_run')


@check(tier='code', says=('logs.no_verb_logs_for_itself',), on=['src/main/cli'])
def check_record_is_the_launchers(run) -> None:
    """The record of an effective verb is the launcher's tee of the whole verb, and no verb
    writes a log of its own: no declaration under src/main/cli carries a `log` key, so every record has one
    shape and holds the verb's tail."""
    own = sorted(str(p.relative_to(REPO_ROOT)) for p in CLI.glob('*/*.json') if 'log' in json.loads(p.read_text()))
    run('logs: no declaration under src/main/cli lets its verb log for itself', not own,
        None if not own else 'these declare a log of their own, which the launcher would not tee: ' + ', '.join(own),
        check='logs.no_verb_logs_for_itself')


@check(tier='code', says=('record.names_read_once',), on=['src'])
def check_record_names_read_once(run) -> None:
    """The launcher's stamp and record names, CORPUS_YOGA_STAMP and CORPUS_YOGA_LOG, are read
    by the tier contract alone - tier.py's stamp_of and record_of, tier.sh's twins - and only
    for the act the launcher dispatched, so that a verb run inside another act cannot
    take the outer act's record or stamp as its own, and no verb writes into a record by
    path."""
    faces = {REPO_ROOT / 'src' / 'main' / 'tier.py', REPO_ROOT / 'src' / 'main' / 'tier.sh'}
    names = r'CORPUS_YOGA_(STAMP|LOG)'
    readers = sorted(str(f.relative_to(REPO_ROOT)) for f in (REPO_ROOT / 'src').rglob('*')
                     if f.is_file() and f not in faces and f not in GATE_FILES
                     and ((f.suffix == '.py' and re.search(rf"environ(\.get)?\(\s*['\"]{names}", f.read_text()))
                          or (f.suffix == '.sh' and re.search(rf'\$\{{?{names}', f.read_text()))))
    run('record: only the tier faces read the launcher\'s stamp and record names', not readers,
        None if not readers else f'{", ".join(readers)} reads them directly - a verb takes tier.stamp_of or '
        f'tier.record_of (stamp_of, record_of in the shell), which answer only for the act the launcher dispatched',
        check='record.names_read_once')


@check(tier='code', on=['src/main', 'src/test'], says=(
    'reply.is_the_bare_status',
    'reply.now_is_the_launchers',
))
def check_reply(run) -> None:
    """now: is the launcher's reply, never the verb's: where the launcher
    named the act it dispatched and the file to hand the effect through, the printer's report
    says no now:, hands up no steps of its own, and writes the effect there; where no launcher
    asked, or the effect is an inner verb's, the effect line is the last line and still no
    now: is said. The reply itself is the bare status before the effect line."""
    sys.path.insert(0, str(SRC / 'main'))
    import contextlib
    import importlib
    import io
    import tempfile
    facts = importlib.import_module('facts')
    with tempfile.TemporaryDirectory() as scratch:
        handed = Path(scratch) / 'act.effect'
        env = {'CORPUS_YOGA_ACT': 'stage clean', 'CORPUS_YOGA_EFFECT': str(handed)}
        kept = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            outer, inner = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(outer):
                    facts.report(None, 'stage clean: DONE - did remove 1 duplicate')
                with contextlib.redirect_stdout(inner):
                    facts.report(None, 'indexing sync: DONE - written')
                said = 'the printer says now: itself' if 'now:' in outer.getvalue() + inner.getvalue() else None
            except TypeError as error:
                said = f'the printer takes the room\'s to-do from the verb: {error}'
            read = facts.load(handed.read_text()) if handed.is_file() else None
        finally:
            for k, v in kept.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    handed_ok = (said is None and read == {'effect': 'stage clean: DONE - did remove 1 duplicate'} and outer.getvalue().strip() == '')
    run('reply: an act the launcher dispatched hands its effect up, nothing else, and says no now:', handed_ok,
        said or (None if handed_ok else f'handed {read!r}; printed {outer.getvalue()!r}'), check='reply.now_is_the_launchers')
    inner_ok = said is None and inner.getvalue().strip() == 'indexing sync: DONE - written'
    run('reply: an inner verb ends on its effect line and says no now:', inner_ok,
        said or (None if inner_ok else f'printed {inner.getvalue()!r}'), check='reply.now_is_the_launchers')
    # the reply is the bare status before the effect line (issues/1016): what corpus-yoga status
    # says, as it says it - what stands in the way, then now: - so that a refused unit stands
    # in every tail where it stands in the status, and the reply composes nothing of its own.
    # The live bug: reading-room's rehearsal of 2026-11-06T200505Z refused three units and
    # replied with a now: of a promote, a clean and a server start, then NOT DONE.
    reply = importlib.import_module('reply')
    kept_environ = dict(os.environ)
    os.environ.update({'CORPUS_YOGA_NO_SEND': '1'})     # the nouns the reply runs make no send under the gate
    try:
        with tempfile.TemporaryDirectory() as scratch:
            handed = Path(scratch) / 'act.effect'
            handed.write_text('effect: logs clean: DONE - did remove nothing\n')
            replied = io.StringIO()
            with contextlib.redirect_stdout(replied):
                reply.main(['logs clean', str(handed), '0'])
        status_said = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), 'status'], capture_output=True, text=True, cwd=REPO_ROOT).stdout.splitlines()
    finally:
        os.environ.clear()
        os.environ.update(kept_environ)
    lines_said = replied.getvalue().splitlines()
    body = lines_said[:-1]
    same = body == status_said and lines_said[-1:] == ['logs clean: DONE - did remove nothing']
    differs = next((i for i, (a, b) in enumerate(zip(body, status_said), 1) if a != b), min(len(body), len(status_said)) + 1)
    run("reply: an act's reply is the bare status before its effect line", same,
        None if same else f'the reply has {len(body)} line(s) before its effect where the status has {len(status_said)}; they differ from line {differs}',
        check='reply.is_the_bare_status')


@check(tier='code', on=['src/main', 'src/run_python_script.sh', 'corpus-yoga'], says=(
    'completions.follows_its_own_change',
    'completions.offers_the_commands_as_they_are',
    'completions.says_why_it_offers_nothing',
    'completions.status_says_one_thing',
    'completions.sync_runs_the_install',
))
def check_completions(run) -> None:
    """What tab offers is read from the declarations when tab is pressed: in a
    copy of the declared surface, a zsh that has pressed tab once is offered, at its next
    tab, a verb declared in between; where a declaration no longer parses, tab says
    why it offers nothing; and what tab does is itself read at each tab, since zsh keeps
    the file it loads until the terminal closes. And the status says whether zsh is set up for this
    copy, over a planted home: no lines, this copy's lines, another copy's,
    a copy that is gone, lines `install` would not write, and lines zsh does not load."""
    import shutil
    import subprocess
    import tempfile
    sys.path.insert(0, str(SRC / 'main'))
    import importlib
    facts = importlib.import_module('facts')
    zsh = shutil.which('zsh')
    standin = CLI / 'completions' / '_corpus-yoga'
    offers = 'completions: tab offers a verb declared since the last tab'
    if zsh is None:
        run(offers, True, check='completions.offers_the_commands_as_they_are')
        run('completions: tab says why it offers nothing where a declaration does not parse', True, check='completions.says_why_it_offers_nothing')
        run('completions: a terminal that has pressed tab follows a change to what tab does', True, check='completions.follows_its_own_change')
    elif not standin.is_file():
        run(offers, False, 'src/main/cli/completions/_corpus-yoga is no file: what zsh loads is a copy of the commands, '
            'written by a verb and out of date wherever a declaration has changed since', check='completions.offers_the_commands_as_they_are')
        run('completions: tab says why it offers nothing where a declaration does not parse', False,
            'src/main/cli/completions/_corpus-yoga is no file', check='completions.says_why_it_offers_nothing')
        run('completions: a terminal that has pressed tab follows a change to what tab does', False, 'src/main/cli/completions/_corpus-yoga is no file', check='completions.follows_its_own_change')
    else:
        with tempfile.TemporaryDirectory() as scratch:
            copy = Path(scratch).resolve() / 'copy'
            shutil.copytree(CLI, copy / 'src' / 'main' / 'cli', ignore=shutil.ignore_patterns('__pycache__'))
            for module in sorted((SRC / 'main').glob('*.py')):
                shutil.copy(module, copy / 'src' / 'main' / module.name)
            shutil.copy(SRC / 'run_python_script.sh', copy / 'src' / 'run_python_script.sh')
            shutil.copy(REPO_ROOT / 'corpus-yoga', copy / 'corpus-yoga')
            verbs = copy / 'src' / 'main' / 'cli' / 'completions'
            presses = f'''
fpath=({verbs} $fpath)
autoload -Uz _corpus-yoga
_describe() {{ local offered=$@[-1]; print -l -- "${{(@P)offered}}" }}
compadd() {{ print -l -- "$@" }}
_files() {{ : }}
_message() {{ print -r -- "message: $@[-1]" }}
cd {copy}
words=(./corpus-yoga completions ''); CURRENT=3
_corpus-yoga
print -- ---
cp {verbs}/uninstall.json {verbs}/declared-since.json
_corpus-yoga
print -- ---
print -r -- '{{ "help": "cut short' > {verbs}/declared-since.json
_corpus-yoga
print -- ---
print -r -- 'print -r -- changed-since' >> {verbs}/offer.zsh
_corpus-yoga
'''
            pressed = subprocess.run([zsh, '-f', '-c', presses], capture_output=True, text=True, timeout=60,
                                     env={**os.environ, 'CORPUS_YOGA_VENV': sys.prefix})
        first, second, third, fourth = (pressed.stdout.split('---') + ['', '', ''])[:4]
        before = [line.split(':')[0] for line in first.splitlines() if line.strip()]
        after = [line.split(':')[0] for line in second.splitlines() if line.strip()]
        why = (f'the first tab offers {before}, not the declared verbs' if 'uninstall' not in before or 'declared-since' in before
               else f'the second tab offers {after}: the verb declared since the first is not among them' if 'declared-since' not in after
               else None)
        run(offers, why is None, why and f'{why} {pressed.stderr.strip()[:200]}'.strip(), check='completions.offers_the_commands_as_they_are')
        told = [line for line in third.splitlines() if line.startswith('message: ')]
        run('completions: tab says why it offers nothing where a declaration does not parse', bool(told),
            None if told else f'the third tab says {third.strip()[:120] or "nothing"}: a reader cannot tell a broken declaration from a position that takes no argument',
            check='completions.says_why_it_offers_nothing')
        followed = 'changed-since' in fourth.split()
        run('completions: a terminal that has pressed tab follows a change to what tab does', followed,
            None if followed else 'the fourth tab does not run what src/main/cli/completions/offer.zsh became: zsh keeps the file it loaded, '
            'so a change to it is followed only by a new terminal, and nothing says so', check='completions.follows_its_own_change')

    declared = json.loads((CLI / 'status' / 'sync.json').read_text()).get('x', [])
    install = getattr(cli_completions, 'INSTALL', '')
    ran = bool(install) and install.removeprefix('./') in declared
    run('completions: the machine\'s sync runs the remedy the status names', ran,
        None if ran else f'{install or "the status names no one remedy"}: not among what corpus-yoga status sync runs ({", ".join(declared)}) - a reader types it by hand',
        check='completions.sync_runs_the_install')

    if zsh is None:
        return
    here = [f'fpath=({CLI / "completions"} $fpath)', f"alias corpus-yoga='{REPO_ROOT / 'corpus-yoga'}'"]
    def planted(home: Path, lines: list[str] | None, below: bool) -> None:
        if lines is not None:
            ours, zsh_own = ['# corpus-yoga tab-completion', *lines, '# end corpus-yoga tab-completion'], ['autoload -Uz compinit', 'compinit -u']
            (home / '.zshrc').write_text('\n'.join([*zsh_own, *ours, ''] if below else [*ours, *zsh_own, '']))
    cases = {
        'no lines in ~/.zshrc': (None, 'not set up in zsh', True),
        'the lines of this copy': (here, 'set up', False),
        'the lines of another copy': ([here[0], "alias corpus-yoga='~/other/corpus-yoga'"], 'set up for a different copy of corpus-yoga, at ~/other', True),
        'the lines of a copy that is gone': ([here[0], "alias corpus-yoga='~/gone/corpus-yoga'"], 'set up for a copy of corpus-yoga that is gone, at ~/gone', True),
        'lines install would not write': (['fpath=(~/elsewhere $fpath)', here[1]], 'set up, but not as corpus-yoga completions install sets it up', True),
        'the lines of this copy below compinit': (here, 'written in ~/.zshrc, but zsh does not load it', True),
    }
    for case, (lines, expected, owed) in cases.items():
        with tempfile.TemporaryDirectory() as scratch:
            home = Path(scratch).resolve()
            (home / 'other').mkdir()
            (home / 'other' / 'corpus-yoga').write_text('')
            planted(home, lines, below=case.endswith('below compinit'))
            # the planted home replaces the reader's own in everything that is found from
            # it: the venv the launcher runs in is named, and the directory zsh reads its
            # rc from is left to follow HOME
            away = {key: value for key, value in os.environ.items() if key not in ('ZDOTDIR', 'USER_ZDOTDIR')}
            asked = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), 'completions'], capture_output=True, text=True, cwd=REPO_ROOT,
                                   env={**away, 'HOME': str(home), 'CORPUS_YOGA_VENV': sys.prefix, 'CORPUS_YOGA_NO_SEND': '1'}, timeout=120)
        try:
            said = facts.load(asked.stdout).get('completions', {})
        except (ValueError, AttributeError):
            said = {}
        said = said if isinstance(said, dict) else {}
        same = said.get('tab-completion') == expected and ('remedy' in said) == owed and len(said) == 1 + owed
        run(f'completions: the status over {case} says one thing, and a remedy where one is owed', same,
            None if same else f'expected tab-completion: {expected} {"with" if owed else "without"} a remedy; corpus-yoga completions says '
            f'{str(said)[:200] if said else "nothing readable - " + (asked.stderr.strip() or asked.stdout.strip())[:200]}',
            check='completions.status_says_one_thing')


@check(tier='code', on=['src/main/cli', 'src/main/facts.py', 'corpus-yoga'], says=(
    'walkthrough.walks_and_runs',
))
def check_walkthrough(run) -> None:
    """The walkthrough walks the room's state and its help, and runs a command it reaches: driven by lines on stdin as a reader's keys drive it, it starts on the
    top, which holds the commands, the machine report first, whose help stands beside its
    status and says what its declaration says; n reaches the pipeline noun, m descends, a
    status is read where the walk lands on it, v shows a value, b returns, and x on a key
    that is a command runs it and re-reads. Each step is a document the printer's reader
    loads, and says the size and shape of what it stands on, each under the key
    that would bring it - members for m, value for v, next for n - and a status that
    cannot be read as a FAIL, never as content; the mark before a step is the key that
    made it."""
    import subprocess
    sys.path.insert(0, str(SRC / 'main'))
    import importlib
    facts = importlib.import_module('facts')
    target = CLI / 'walkthrough' / 'walkthrough.py'
    if not target.is_file() or getattr(facts, 'load', None) is None:
        run('walkthrough: a reader walks the room and runs a command it reaches', False,
            'corpus-yoga walkthrough is no command: a status is read whole, in the printer\'s order', check='walkthrough.walks_and_runs')
        return
    env = {**os.environ, 'CORPUS_YOGA_NO_SEND': '1'}
    commands = sorted(c['command'] for c in cli.commands())
    order = [n for n in ('status', 'stage', 'store') if n in commands] + [n for n in commands if n not in ('status', 'stage', 'store')]
    said = facts.load(subprocess.run([str(REPO_ROOT / 'corpus-yoga'), 'pipeline'], capture_output=True, text=True, env=env, cwd=REPO_ROOT).stdout)
    beneath = list(said['pipelines'])
    command = 'pipeline'                                      # the key at the top that x runs: the command's own name
    declared = json.loads((CLI / 'status' / 'status.json').read_text())
    # from the top into the report, onto its status, along to its help, into that, the summary shown, and back to the top;
    # in again and along to the pipeline noun; into its status, onto the command; back, on, run
    probe = ['m', 'm', 'n', 'm', 'v', 'b', 'b', 'b', 'b', 'b']
    keys = probe + ['m'] + ['n'] * order.index('pipeline') + ['m', 'm', 'm', 'b', 'b', 'b', 'n', 'b', 'x', 'q']
    proc = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), 'walkthrough'], input='\n'.join(keys) + '\n', capture_output=True, text=True,
                          env=env, cwd=REPO_ROOT, timeout=300)
    steps = []
    for document in re.split(r'\n-.-\n', proc.stdout):       # a mark is the key that made the step after it
        try:
            steps.append(facts.load(document))
        except ValueError:
            steps.append(None)            # what a command printed in the foreground: its own, not a step
    def step(index):
        return steps[index] if -len(steps) <= index < len(steps) and isinstance(steps[index], dict) else {}
    at_noun = len(probe) + 1 + order.index('pipeline')        # the step that first stands on the pipeline noun
    arrive = at_noun + 6                                      # back on the pipeline noun, after three b
    wants = [
        ('it starts on the top, which says how many commands it holds', step(0).get('at') == '' and step(0).get('key') == 'corpus-yoga'
         and step(0).get('members') == f'{len(commands)} keys' and 'next' not in step(0)),
        ('m lands on the machine report, its status and its help beneath, the next command named', step(1).get('at') == '/status'
         and step(1).get('members') == '2 keys' and step(1).get('next') == order[1]),
        ('a status is read where the walk lands on it', step(2).get('key') == 'status' and re.fullmatch(r'\d+ keys?', str(step(2).get('members', ''))) is not None),
        ('no status the walk stands on is unread', all('members' in s or 'value' in s or 'FAIL' in s
                                                       for s in steps if isinstance(s, dict) and s.get('key') == 'status')),
        ('help stands beside the status', step(3).get('key') == 'help'),
        ('a value says its size, and v shows it', step(4).get('key') == 'summary'
         and step(4).get('value') == f"{len(declared['summary'].split())} words" and step(5).get('value') == declared['summary']),
        ('b takes the walk back to where it began', step(len(probe)).get('at') == ''),
        ('n reaches the pipeline noun', step(at_noun).get('key') == 'pipeline'),
        ('m reads a status and descends into it', step(at_noun + 3).get('at') == f'/pipeline/status/pipelines/{beneath[0]}'),
        ('it stands on the command', step(arrive).get('key') == command and str(step(arrive).get('runs', '')).startswith('x - ')),
        ('b goes back over the last move', step(arrive + 1).get('key') == order[order.index('pipeline') + 1]
         and step(arrive + 2).get('key') == command),
        ('x runs the command and says so', any(isinstance(s, dict) and s.get('ran') == command and s.get('exit') == 0 for s in steps)),
        ('it says where it left', step(-1).get('walkthrough') == 'left at /pipeline'),
        ('the marks between its steps are the keys pressed, in order',
         [mark for mark in re.findall(r'^-(.)-$', proc.stdout, re.M) if mark != '-'] == keys),
        ('a step says what a key would bring under that key\'s name, and no bare count', all(
            'place' not in s and 'holds' not in s and len({'members', 'value', 'FAIL'} & set(s)) <= 1
            for s in steps if isinstance(s, dict) and 'key' in s)),
        ('next names the spot n lands on', all(step(i + 1).get('key') == str(step(i).get('next'))
                                               for i, key in enumerate(keys[:-1]) if key == 'n' and 'next' in step(i))
         and any(key == 'n' and 'next' in step(i) for i, key in enumerate(keys[:-1]))),
    ]
    # A status that cannot be read is a failure, said as one (issues/787): asked before the venv
    # exists, where no noun but the machine report can be, the step carries FAIL and neither
    # members nor value, and the walk's exit is 1.
    unminted = subprocess.run([sys.executable, str(target), '/stage/status'], input='q\n', capture_output=True, text=True,
                              env={**env, 'CORPUS_YOGA_VENV': str(REPO_ROOT / 'tmp' / 'no-venv-stands-here')}, cwd=REPO_ROOT, timeout=300)
    try:
        failing = facts.load(re.split(r'\n-.-\n', unminted.stdout)[0])
    except ValueError:
        failing = {}
    failing = failing if isinstance(failing, dict) else {}
    wants += [
        ('a status that cannot be read is a FAIL, not content, and the exit is 1', failing.get('key') == 'status' and 'FAIL' in failing
         and 'members' not in failing and 'value' not in failing and unminted.returncode == 1),
    ]
    # Every spot is addressed by its JSON pointer (issues/775): the walk starts where one names,
    # a slash within a key is ~1, the nearest spot stands in for one that is not there, and
    # the walk leaves with the command that continues it.
    exits: dict[str, int] = {}

    def walked(pointer: str, pressed: str, bare: bool = False) -> list:
        typed = pointer.split(' ') if bare else [pointer]     # typed bare, the shell splits it at each space
        asked = subprocess.run([str(REPO_ROOT / 'corpus-yoga'), 'walkthrough', *typed], input=pressed, capture_output=True, text=True,
                               env=env, cwd=REPO_ROOT, timeout=300)
        exits[pointer] = asked.returncode
        said = asked.stdout
        out = []
        for document in re.split(r'\n-.-\n', said):
            try:
                out.append(facts.load(document))
            except ValueError:
                out.append({})
        return out
    summary = walked('/status/help/summary', 'v\nq\n')
    top = walked('', 'q\n')
    slashed = walked('/stage/status/tmp~1stage', 'q\n')
    astray = walked('/status/help/nonesuch/deeper', 'q\n')
    spaced = '/status/help/explanation/pipeline inputs'
    wants += [
        ('a pointer starts the walk on its spot', summary[0].get('at') == '/status/help/summary' and summary[0].get('key') == 'summary'
         and summary[1].get('value') == declared['summary']),
        ('a slash within a key is ~1 in its pointer', slashed[0].get('key') == 'tmp/stage' and slashed[0].get('at') == '/stage/status/tmp~1stage'),
        ('where no spot stands the longest truncation that does, and the walk says so', astray[0].get('at') == '/status/help'
         and 'the longest part of it that stands is /status/help' in str(astray[0].get('note'))),
        ('its exit is 0 where it went as asked', proc.returncode == 0 and exits.get('/status/help/summary') == 0),
        ('its exit is 3 where the pointer names no spot', exits.get('/status/help/nonesuch/deeper') == 3),
        ('an argument that is no pointer is refused, exit 2, with no walk', walked('nonesuch', 'q\n') == [{}] and exits.get('nonesuch') == 2),
        ('a space within a key is read, quoted or typed bare', walked(spaced, 'q\n')[0].get('at') == spaced
         and walked(spaced, 'q\n', bare=True)[0].get('at') == spaced),
        ('it leaves with the command that continues it', summary[-1].get('walkthrough') == 'left at /status/help/summary'
         and summary[-1].get('corpus-yoga walkthrough /status/help/summary') == 'continues from there'),
        ('the empty pointer is the top, and the walk left there continues bare', top[0].get('at') == '' and exits.get('') == 0
         and top[-1].get('walkthrough') == 'left at the top' and top[-1].get('corpus-yoga walkthrough') == 'continues from there'),
    ]
    failed = [what for what, held in wants if not held]
    run('walkthrough: a reader walks the room and runs a command it reaches', not failed,
        None if not failed else 'not so: ' + '; '.join(failed) + f' (exit {proc.returncode}; {proc.stderr.strip()[-120:]})',
        check='walkthrough.walks_and_runs')


@check(tier='code', on='TREE', after_all=True, says=(
    'calculus.gated_is_cited',
    'calculus.laws_parse',
    'calculus.state_declared',
    'calculus.unenforced_names_issue',
    'grammar.citation_is_stated',
    'grammar.enforcement_map',
    'grammar.gated_is_cited',
    'grammar.laws_parse',
    'grammar.parent_law_defined',
    'grammar.state_declared',
    'grammar.unenforced_names_issue',
    'grammar.unenforced_not_cited',
))
def check_grammar_laws(run, cited: dict) -> None:
    """The CLI's grammar (the law list in src/main/cli/README.md) and the checks that enforce
    it are held to each other, in both directions — so neither can drift into fiction.

    Forward: a citation must name a law the document states. A check citing G99 is
    enforcing something nobody wrote down.

    Backward: a law declaring itself `gated` must really be cited by a check that ran.
    This is the direction that rots silently: a law no check holds is a failing check
    here, not a discovery made when it is broken.

    A law must declare a state at all: `gated`, `by construction` (the shape admits no
    violation — there is no second source to check), `unenforced (#N)` naming the issue that
    will hold it, or `doctrine` (stated deliberately, with no check). Silence is not a state,
    because silence is how an unheld law passes for a held one. `unenforced` must name an
    issue, so the gap is tracked rather than merely noted; `doctrine` need not, because it
    promises nothing — it is the state that keeps a law from obliging a check that would
    need a curated vocabulary invented just to make it codable.

    A law may declare a parent corpus law (`from L5`) — it is that law applied to the
    surface. The parent must exist in rsc/CALCULUS.md (calculus_terms is the authority),
    so the grammar cites the principle instead of paraphrasing it.

    Committed files only (the document, and the citations of this same run): code tier."""
    try:
        laws = cli.grammar_laws()
    except Exception as e:
        run('grammar: laws parse: src/main/cli/README.md', False, str(e), check='grammar.laws_parse')
        return
    run('grammar: laws parse: src/main/cli/README.md', bool(laws),
        None if laws else 'no `- **G<n> — …**` law bullets found', check='grammar.laws_parse')
    if not laws:
        return

    # TWO vocabularies, one citation field (issues/50): a check enforces either a surface law
    # from the grammar or a corpus law from rsc/CALCULUS.md, and a citation is stated if
    # either document states it.
    corpus = cli.calculus_laws()
    orphans = sorted(set(cited) - set(laws) - set(corpus))
    run('grammar: every citation names a stated law', not orphans,
        f'cited by a check but stated in neither the grammar nor the calculus: '
        f'{", ".join(orphans)}' if orphans else None, check='grammar.citation_is_stated')

    # The same three questions the G-laws answer, asked of the laws that govern the DATA
    # — which is where the stakes are higher and the gap was identical: the Laws section
    # promised "each law names its current enforcement" in prose, and nothing read it.
    run('calculus: laws parse: rsc/CALCULUS.md', bool(corpus),
        None if corpus else 'no `- **L<n> — …**` law bullets found', check='calculus.laws_parse')
    stateless_l = sorted(l for l, law in corpus.items() if law['state'] not in cli.LAW_STATES)
    run('calculus: every law declares a state', not stateless_l,
        f'no `gated` / `by construction` / `unenforced (issues/N)` / `doctrine`: '
        f'{", ".join(stateless_l)}' if stateless_l else None, check='calculus.state_declared')
    uncited_l = sorted(l for l, law in corpus.items()
                       if law['state'] == 'gated' and l not in cited)
    run('calculus: every gated law is cited by a check that ran', not uncited_l,
        f'declares `gated` but no check cites it: {", ".join(uncited_l)}'
        if uncited_l else None, check='calculus.gated_is_cited')
    issueless_l = sorted(l for l, law in corpus.items()
                         if law['state'] == 'unenforced' and not law['issues'])
    run('calculus: every unenforced law names the issue that will hold it', not issueless_l,
        f'declares `unenforced` with no issues/N: {", ".join(issueless_l)}'
        if issueless_l else None, check='calculus.unenforced_names_issue')

    stateless = sorted(g for g, law in laws.items() if law['state'] not in cli.LAW_STATES)
    run('grammar: every law declares a state', not stateless,
        f'no `gated`/`by construction`/`unenforced`/`doctrine` marker: {", ".join(stateless)}'
        if stateless else None, check='grammar.state_declared')

    # AGGREGATE, not one check per law: a line per law saying "G7 is cited" carries the same
    # fact as one saying "7/7 gated laws are cited", and the failing ids belong in a detail
    # line rather than in nineteen labels. A report is read by someone deciding whether to
    # look closer; per-law rows make that decision harder, not easier.
    ids = lambda gs: ', '.join(sorted(gs, key=lambda g: int(g[1:])))

    gated = {g for g, law in laws.items() if law['state'] == 'gated'}
    uncited = gated - set(cited)
    run(f'grammar: every gated law is cited by a check ({len(gated) - len(uncited)}/{len(gated)})',
        not uncited,
        f'declares `gated` but no check cites it: {ids(uncited)}' if uncited else None, check='grammar.gated_is_cited')

    unenforced = {g for g, law in laws.items() if law['state'] == 'unenforced'}
    issueless = {g for g in unenforced if not laws[g]['issues']}
    run(f'grammar: every unenforced law names its issue ({len(unenforced) - len(issueless)}/{len(unenforced)})',
        not issueless,
        f'declares `unenforced` with no issues/N: {ids(issueless)}' if issueless else None, check='grammar.unenforced_names_issue')

    # a cited law is held, whatever it claims: the claim is what is wrong
    miscited = {g for g, law in laws.items()
                if law['state'] in ('unenforced', 'doctrine') and g in cited}
    run('grammar: no unenforced or doctrine law is cited', not miscited,
        '; '.join(f'{g} declares `{laws[g]["state"]}` but is cited by: '
                  f'{", ".join(cited[g])}' for g in sorted(miscited)) if miscited else None, check='grammar.unenforced_not_cited')

    # A law citing a parent corpus law must cite one that exists. The bridge is the point:
    # G3 IS L5 applied to the surface, so rsc/CALCULUS.md stays the authority for the
    # principle and the grammar paraphrases nothing. A dangling `from L99` would put the
    # paraphrase back, silently.
    vocab = cli.calculus_terms()
    bridged = {g: laws[g]['from'] for g in laws if laws[g]['from']}
    dangling = {g: parent for g, parent in bridged.items() if parent not in vocab}
    run(f'grammar: every cited corpus law is defined ({len(bridged) - len(dangling)}/{len(bridged)})',
        not dangling,
        '; '.join(f'{g}: `from {parent}` names no law in rsc/CALCULUS.md'
                  for g, parent in sorted(dangling.items())) if dangling else None, check='grammar.parent_law_defined')

    # The enforcement map, printed rather than maintained as prose: this IS the
    # "held honest by the gates" list, which prose can only carry by hand.
    by_state: dict[str, list[str]] = {}
    for gid, law in laws.items():
        by_state.setdefault(str(law['state']), []).append(gid)
    summary = '; '.join(f'{st}: {len(g)}' for st, g in sorted(by_state.items()))
    run(f'grammar: {len(laws)} laws — {summary}', True, check='grammar.enforcement_map')
