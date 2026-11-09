"""tree.py - the dev gate's checks of the repository's own files, names and cross-references."""
import json
import re
import subprocess
import sys
from pathlib import Path

from gate import (
    GATE_FILES,
    PIPELINES,
    PIPELINE_ROOT,
    REPO_ROOT,
    RSC,
    SRC,
    _PIPELINE_UNDECLARED,
    check,
)
from member import members  # noqa: E402 - on the paths gate.py sets
import provider  # noqa: E402 - on the paths gate.py sets
import xref  # noqa: E402 - the gate's sibling, src/test/dev/xref.py


@check(tier='code', says=('files.required_exists',), on='TREE')
def check_required_files(run):
    # Only files named independently of the live tree -- walking rsc/schema/ for v*.json and then
    # asserting those same paths exist is tautological (it requires whatever is present); a missing
    # schema dir simply has no versions and is invisible to the family walks instead.
    required = [
        *[PIPELINE_ROOT / name / 'validate.sh' for name in PIPELINES if name != 'chat-capture'],
        PIPELINE_ROOT / 'chat-capture' / 'claude' / 'validate.sh',
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'model' / 'gen_model_candidate.py',
        SRC  / 'main' / 'model' / 'model.py',
        RSC  / 'test' / 'xref_expected_score',
        SRC  / 'test' / 'dev' / 'schema_recommendations.py',
        SRC  / 'run_python_script.sh',
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists(), check='files.required_exists')


@check(tier='code', says=(
    'structure.pipeline_declaration_validates',
    'structure.pipeline_implements_run',
    'structure.pipeline_mechanism_whole',
    'structure.pipeline_name_states_input',
    'structure.pipeline_provider_served',
    'structure.pipeline_skip_names_family',
))
def check_pipeline_declarations(run) -> None:
    """Membership is placement and facts are declared: every subdirectory of
    src/main/pipeline/ carries a pipeline.json valid against pipeline.schema.json and
    implements run.sh — so a member missing either is a named failure here, and a stray
    run.sh elsewhere confers nothing."""
    import jsonschema
    schema = json.loads((PIPELINE_ROOT / 'pipeline.schema.json').read_text())
    validator = jsonschema.Draft4Validator(schema)
    for name in _PIPELINE_UNDECLARED:
        run(f'pipeline: {name}: declares itself in pipeline.json', False,
            f'src/main/pipeline/{name}/ has no pipeline.json — a member without a '
            f'declaration is invisible to every consumer of the listing',
            check='structure.pipeline_declaration_validates')
    for name in PIPELINES:
        decl = PIPELINE_ROOT / name / 'pipeline.json'
        errors = sorted(validator.iter_errors(json.loads(decl.read_text())),
                        key=lambda e: list(e.path))
        run(f'pipeline: {name}: declaration validates against pipeline.schema.json',
            not errors,
            None if not errors else
            f'{errors[0].message} at {"/".join(str(x) for x in errors[0].path) or "(root)"}',
            check='structure.pipeline_declaration_validates')
        undeclared = sorted(set(PIPELINES[name].diagnostic_skip) - set(PIPELINES[name].schemas))
        run(f'pipeline: {name}: every diagnostic skip names a declared family', not undeclared,
            None if not undeclared else
            f'diagnostic_skip names {", ".join(undeclared)}, no entry of schemas - a skip licenses one declared family',
            check='structure.pipeline_skip_names_family')
        # The name states the input (issues/667): the pipeline <channel>-<act> reads
        # data/input/<provider>/<channel>/<qualifier>-<act>, of a declared provider.
        declared = json.loads(decl.read_text()).get('input', '')
        channel, _, act = name.partition('-')
        parts = declared.split('/')
        served = PIPELINES[name].providers
        stated = (len(parts) == 5 and parts[:2] == ['data', 'input']
                  and (parts[2] in provider.provider_names() if not served else parts[2] == '<provider>')
                  and parts[3] == channel and '-' in parts[4]
                  and parts[4].rsplit('-', 1)[1] == act)
        run(f'pipeline: {name}: name states its input', stated,
            None if stated else
            f'{declared} is not data/input/<provider>/{channel}/<qualifier>-{act} of a declared provider - '
            f'a pipeline is named <channel>-<act>, singular, for the directories it reads',
            check='structure.pipeline_name_states_input')
        # A provider the declaration names is a row of the registry with a mechanism
        # directory of its name beside the declaration, and the reverse (issues/635).
        placed = {d.name for d in members(PIPELINE_ROOT / name)} & set(provider.provider_names())
        for p in sorted(set(served) | (placed if served else set())):
            ok = p in served and p in placed
            run(f'pipeline: {name}: provider {p} is declared, registered and has its mechanism', ok,
                None if ok else
                (f'src/main/pipeline/{name}/{p}/ exists and pipeline.json names no provider {p}' if p in placed else
                 f'pipeline.json names provider {p}, which is '
                 + ('no row of rsc/provider/providers.csv' if p not in provider.provider_names()
                    else f'without src/main/pipeline/{name}/{p}/')),
                check='structure.pipeline_provider_served')
            # run.sh reaches a provider's mechanism by the provider's name ($provider/<file>),
            # so no reference names these files: what run.sh reaches that way is held here,
            # less what it first tests for with -f, which a provider may lack.
            runner = (PIPELINE_ROOT / name / 'run.sh').read_text()
            reached = set(re.findall(r'\$provider/([A-Za-z_]+\.(?:sh|py))', runner))
            optional = set(re.findall(r'-f "\$SCRIPT_DIR/\$provider/([A-Za-z_]+\.(?:sh|py))"', runner))
            absent = [f for f in sorted(reached - optional) if ok and not (PIPELINE_ROOT / name / p / f).is_file()]
            run(f'pipeline: {name}: provider {p} holds its mechanism whole', not absent,
                None if not absent else
                f'src/main/pipeline/{name}/{p}/ lacks {", ".join(absent)} - run.sh calls each by the provider\'s name',
                check='structure.pipeline_mechanism_whole')
        run_sh = PIPELINE_ROOT / name / 'run.sh'
        run(f'pipeline: {name}: implements run.sh', run_sh.is_file(),
            None if run_sh.is_file() else
            f'{run_sh.relative_to(REPO_ROOT)} missing — the run phase is the one every '
            f'pipeline must implement',
            check='structure.pipeline_implements_run')


@check(tier='code', says=('imports.step_module_imports',))
def check_step_imports(run) -> None:
    """A step module that cannot import fails here, not at the first pipeline run: the run.sh steps exec these under python, so an unresolvable sys.path
    insert or import inside them is a commit-time defect the tiers' cache reads
    cannot see. Each import runs in a FRESH interpreter, because this process's
    own sys.path (pipeline/chat-export is already on it for the accumulate
    check) resolves the very imports a dangling insert would strand, so an
    in-process import passes where the step's own interpreter fails. Both modules are
    __main__-guarded, so importing executes only their top level."""
    for name in ('project_markdown', 'compare_sources'):
        proc = subprocess.run(
            [sys.executable, '-c',
             f"import sys; sys.path.insert(0, 'src/main/model'); import {name}"],
            capture_output=True, text=True, cwd=REPO_ROOT)
        lines = (proc.stdout + proc.stderr).strip().splitlines()
        run(f'imports: {name}: the step module imports in a fresh interpreter',
            proc.returncode == 0,
            None if proc.returncode == 0 else
            (lines[-1] if lines else f'exit {proc.returncode}'),
            check='imports.step_module_imports')


@check(tier='code', says=('structure.self_path_matches_address',))
def check_self_paths(run) -> None:
    """Every SELF declaration names its own file's address: the root
    derivation searches for the declared path and fails loudly at import when it
    is stale — this check fails it at commit instead, for every declaring file,
    executed or not — python, shell and applescript alike."""
    pat = re.compile(r"^SELF\s*=\s*'([^']+)'", re.M)
    pat_applescript = re.compile(r'^set SELF to "([^"]+)"', re.M)
    for f in sorted(list(SRC.rglob('*.py')) + list(SRC.rglob('*.sh'))
                    + list(SRC.rglob('*.applescript'))):
        if '__pycache__' in f.parts:
            continue
        m = (pat_applescript if f.suffix == '.applescript' else pat).search(f.read_text())
        if not m:
            continue
        actual = f.relative_to(REPO_ROOT).as_posix()
        run(f'self: {actual}: declares its own address', m.group(1) == actual,
            None if m.group(1) == actual else
            f'declares {m.group(1)!r} — a moved file whose declaration did not move with it',
            check='structure.self_path_matches_address')


@check(tier='code', on='TREE', says=(
    'anchor.names_its_sequence',
    'structure.corpus_roots_ignored',
    'structure.no_machine_facts_committed',
))
def check_committed_tree(run) -> None:
    """L2 held over every tracked file, not only the report the gate writes itself. Git carries machinery only, as two facts. The corpus's
    roots (data, tmp, ext) and the machine binding are ignored and track nothing, so a
    corpus datum or a machine fact is unrepresentable in a commit. And no tracked text
    names a macOS home path or its project-slug form, the two shapes that embed a
    username; /home/claude/ is the provider's container, a datum's path and no machine
    fact, so the shape is /Users/ alone. The declared machine names in
    rsc/machine/machines.csv are vocabulary, not machine facts (the one exemption).
    Committed files only: code tier."""
    roots = ['data', 'tmp', 'ext', 'machine-name.txt']
    tracked = subprocess.run(['git', '-C', str(REPO_ROOT), 'ls-files', '--cached', '--'] + roots,
                             capture_output=True, text=True).stdout.split()
    unignored = [r for r in roots
                 if subprocess.run(['git', '-C', str(REPO_ROOT), 'check-ignore', '-q', r]).returncode != 0]
    run('tree: the corpus roots and the machine binding are ignored and track nothing',
        not tracked and not unignored,
        '; '.join(filter(None, [f'tracked: {", ".join(tracked)}' if tracked else None,
                                f'not ignored: {", ".join(unignored)}' if unignored else None])) or None,
        law='L2', check='structure.corpus_roots_ignored')
    home = re.compile(r'/Users/[A-Za-z0-9_.-]+/|-Users-[A-Za-z0-9_.]+-')
    files = subprocess.run(['git', '-C', str(REPO_ROOT), 'ls-files', '--cached', '-z'],
                           capture_output=True, text=True).stdout.split('\0')
    hits = []
    for rel in files:
        if not rel:
            continue
        try:
            text = (REPO_ROOT / rel).read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if home.search(line):
                hits.append(f'{rel}:{number}')
    run(f'tree: no tracked file names a home path or its slug ({len(files) - 1} files)',
        not hits, f'machine facts in committed text: {", ".join(hits[:8])}'
        + (f' (+{len(hits) - 8})' if len(hits) > 8 else '') if hits else None,
        law='L2', check='structure.no_machine_facts_committed')
    # An anchor to the forge names its sequence, issues/N or pull/N (issues/922): a hash is
    # YAML's comment, a URL's fragment and a shell's, and #N says nothing of which sequence
    # holds N. A CSS colour stands after a colon or a border style; a fixture of GitHub's
    # own grammar, which the forge writes for its parser, says so on its line.
    hash_anchor = re.compile(r"(?<![\w&{#$:])(?<!solid )(?<!dashed )(?<!dotted )#\d{1,4}\b")
    hashed = []
    for rel in files:
        if not rel or rel.endswith(('.html', '.css')):
            continue
        try:
            text = (REPO_ROOT / rel).read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if "GitHub's grammar, hashed" not in line and hash_anchor.search(line):
                hashed.append(f'{rel}:{number}')
    run(f'tree: no tracked file anchors the forge by a hash ({len(files) - 1} files)',
        not hashed, f'hashed anchors, each written as issues/N or pull/N: {", ".join(hashed[:8])}'
        + (f' (+{len(hashed) - 8})' if len(hashed) > 8 else '') if hashed else None,
        check='anchor.names_its_sequence')


@check(tier='code', says=('templates.teach_signature',), on=['.github'])
def check_templates(run) -> None:
    """Both templates teach the Signature line, so a body raised through either
    route — the web form or the copy-from-prototype --body-file — opens with the same
    triad the commit hook stamps. A bare-line match, not a substring one: the teaching
    prose itself mentions the phrase mid-sentence, backticked, which must not pass for
    the line the body actually opens with."""
    signature_line = 'Signature: <machine>/<provider>/<session>'
    for path in [REPO_ROOT / '.github' / 'ISSUE_TEMPLATE.md',
                 REPO_ROOT / '.github' / 'PULL_REQUEST_TEMPLATE.md']:
        lines = path.read_text().splitlines() if path.exists() else []
        taught = signature_line in lines
        run(f'{path.relative_to(REPO_ROOT)}: teaches the Signature line', taught,
            f'Add a `{signature_line}` line to {path.relative_to(REPO_ROOT)}'
            if not taught else None, check='templates.teach_signature')


@check(tier='code', on='TREE', says=(
    'xref.no_bad_pointers',
    'xref.score_matches_expectation',
    'xref.version_named_inside_its_family',
))
def check_xref(run):
    """The table is computed here, in-process; only render writes rsc/test/xref.csv
    (a check computes, it never writes). `check`
    stays xref.py's own writing verb for a standalone `corpus-yoga test xref`."""
    rows   = xref.build_table()
    counts = xref.count(rows)
    actual = xref.score_line(counts)

    score_file = RSC / 'test' / 'xref_expected_score'
    expected   = score_file.read_text().strip()

    run('xref: no bad pointers', counts.stale_pointer == 0,
        xref.summary_line(counts, xref.DEFAULT_OUT.relative_to(REPO_ROOT))
        if counts.stale_pointer else None, check='xref.no_bad_pointers')
    run(f'xref: {actual}', actual == expected,
        f'expected: {expected}  →  consider updating {score_file.relative_to(REPO_ROOT)}'
        if actual != expected else None, law='L9', check='xref.score_matches_expectation')
    # L9 is cited from here, a check that cannot be skipped: a citation inside a network
    # fetch never happens when the fetch fails, and a law must not look unenforced
    # because a request timed out.
    # A family's version file is named only from inside the family (issues/986): a version
    # number written elsewhere is a second home for the family's latest, which src/main/latest.py
    # reads from the directory, restated by hand at every mint - and two mints in flight meet
    # on that one line at relocation.
    version_file = re.compile(r'^(rsc/schema/.+)/v\d+\.json$')
    outside = sorted({(str(r[0]), str(r[1])) for r in rows
                      if r[0] and (named := version_file.match(str(r[3])))    # an unreferenced file's row has no referrer
                      and not str(r[0]).startswith(named.group(1) + '/')})
    run("xref: a family's version file is named only from inside the family", not outside,
        None if not outside else 'named outside its family at ' + ', '.join(f'{f}:{line}' for f, line in outside[:8]),
        check='xref.version_named_inside_its_family')
    return rows


@check(tier='code', on=['src/main', 'src/test', 'README.md', 'CONTRIBUTING.md', 'AGENTS.md', 'rsc/CALCULUS.md', 'rsc/schema/WORKFLOW.md', '.github'], says=(
    'command.every_spelling_is_declared',
    'command.undeclared_is_unrepresentable',
    'prescription.names_a_command',
))
def check_spelling(run) -> None:
    """Every spelling of a corpus-yoga command the sources and documents carry is one the
    declarations hold (G17): the noun, the verb and each flag, read by
    src/main/spell.py - the one API that spells a command from its declaration - over every
    string literal of src/main and src/test, every line of the shell, applescript and
    declaration files, and the live documents. A site that types a command the declarations
    do not hold fails here.
    The API itself refuses what is undeclared. A prescription in prose names a command,
    never a repository path."""
    import ast
    import importlib
    sys.path.insert(0, str(SRC / 'main'))
    try:
        spell = importlib.import_module('spell')
    except ImportError:
        run('spelling: src/main/spell.py spells a command from its declaration', False,
            'src/main/spell.py does not exist: every site types its command', law='G17', check='command.every_spelling_is_declared')
        return
    refused = {}
    for name, ask in (('export promote --all', lambda: spell.line('export', 'promote', all=True)),
                      ('forge merge without its pr', lambda: spell.line('forge', 'merge')),
                      ('a noun no declaration holds', lambda: spell.line('nonesuch'))):
        try:
            refused[name] = f'spelt {ask()!r}'
        except spell.Undeclared:
            refused[name] = None
    spelt = {'agent capture --provider claude --id e2d2039d': spell.line('agent', 'capture', provider='claude', id='e2d2039d'),
             'server start --daemon': spell.line('server', 'start', daemon=True), 'export promote': spell.line('export', 'promote'),
             'forge merge 946': spell.line('forge', 'merge', 946)}
    wrong = {k: v for k, v in spelt.items() if v != f'corpus-yoga {k}'}
    ok = not any(refused.values()) and not wrong
    run('spelling: the API refuses an undeclared noun, verb or flag and spells the declared as typed', ok,
        None if ok else '; '.join([f'{k} was not refused: {v}' for k, v in refused.items() if v] + [f'{k} spelt as {v!r}' for k, v in wrong.items()]),
        law='G17', check='command.undeclared_is_unrepresentable')

    def python_texts(path: Path) -> list[tuple[int, str]]:
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and 'corpus-yoga' in node.value:
                out.append((node.lineno, node.value))
            elif isinstance(node, ast.JoinedStr):
                text = ''.join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else '{}' for v in node.values)
                if 'corpus-yoga' in text:
                    out.append((node.lineno, text))
        return out
    files = [p for p in sorted((SRC / 'main').rglob('*')) if p.suffix in ('.py', '.sh', '.applescript', '.json')]
    files += [p for p in sorted((SRC / 'test').rglob('*.py')) if p not in GATE_FILES]     # the gate's files hold fixtures that spell no command
    files += [REPO_ROOT / name for name in ('README.md', 'CONTRIBUTING.md', 'AGENTS.md', 'rsc/CALCULUS.md', 'rsc/schema/WORKFLOW.md')]
    files += sorted((REPO_ROOT / '.github').glob('*.md'))
    faults = []
    for path in files:
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT)
        texts = python_texts(path) if path.suffix == '.py' else [(i, l) for i, l in enumerate(path.read_text(errors='ignore').splitlines(), 1) if 'corpus-yoga' in l]
        for lineno, text in texts:
            for spelling, fault in spell.mentions(text):
                if fault:
                    faults.append(f'{rel}:{lineno} `{spelling[:60]}` - {fault}')
    run('spelling: every spelling of a corpus-yoga command in the sources and documents is one the declarations hold', not faults,
        None if not faults else '; '.join(faults)[:600], law='G17', check='command.every_spelling_is_declared')

    # A prescription in prose names a command, never a path: "run src/main/<p>/run.sh first"
    # tells a reader to type a path. The imperative identifies it - `run` followed by a
    # repository script - and a line that merely mentions a path prescribes nothing.
    imperative = re.compile(r'\b[Rr]un\s+\.?/?((?:src|rsc)/\S+\.(?:sh|py))')
    told = []
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sh', '.md', '.json'):
            continue
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] in ('tmp', '.git', 'data') or str(rel) == 'rsc/test/xref.csv' or path in GATE_FILES:
            continue
        for i, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
            m = imperative.search(line)
            if m:
                told.append(f'{rel}:{i} tells a reader to run {m.group(1)}: `{line.strip()[:80]}`')
    run('prescription: no line tells a reader to run a repository path - a prescription names a command', not told,
        None if not told else '; '.join(told)[:600] + ' - name the corpus-yoga command that does it, or there is none and that is the defect',
        law='G17', check='prescription.names_a_command')


@check(tier='code', says=('tier.paths_from_contract',), on=['src/main'])
def check_tier_contract(run) -> None:
    """Every data or tmp path under src/main derives from the tier contract:
    src/main/tier.py and its shell twin are the one home, and no other script builds a
    path through the literal segment 'data' or 'tmp' from a root of its own - REPO,
    parents[3], $REPO_DIR - by hand - a rehearsal is
    the checkout's own code run over other tiers, which such a path would escape."""
    # a Path built through the literal segment 'data' or 'tmp' from any root-shaped
    # expression - REPO, repo, parents[3], _root[0] - and the shell's $<ROOT>/data, /tmp
    py = re.compile(r"/\s*'(data|tmp)'\s*/")
    sh = re.compile(r'\$\{?[A-Z_]*(DIR|ROOT)\}?/(data|tmp)(/|")')
    found = []
    for f in sorted((SRC / 'main').rglob('*')):
        if f.suffix not in ('.py', '.sh') or f.name in ('tier.py', 'tier.sh') or '__pycache__' in f.parts or 'gen' in f.parts:
            continue
        pat = py if f.suffix == '.py' else sh
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if line.strip().startswith('#'):
                continue
            if pat.search(line):
                found.append(f'{f.relative_to(REPO_ROOT)}:{i}')
    run('tier: every data and tmp path under src/main derives from src/main/tier.py or tier.sh', not found,
        ('; '.join(found[:8]) + (f'; ... {len(found)} total' if len(found) > 8 else '')) if found else None,
        check='tier.paths_from_contract')
