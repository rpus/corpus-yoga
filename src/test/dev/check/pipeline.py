"""pipeline.py - the dev gate's checks of the pipelines: declarations, judges, caches, captures and the corpus format."""
import io
import subprocess
from pathlib import Path

from gate import (
    PIPELINES,
    REPO_ROOT,
    SRC,
    _cache_io_resolves,
    check,
)
from markdown_projection import turn_seq
import accumulate as _accumulate
import cache_io
import cli


@check(tier='code', on=['src/main/corpus.py', 'src/main/browser', 'src/main/export', 'src/main/agent'], says=(
    'pipeline.every_provider_is_judged',
))
def check_providers_judged(run) -> None:
    """Every provider a pipeline captures for is judged by a family of that pipeline: a unit of the provider has at least one judge, so the rehearsal stands
    before its promotion."""
    import corpus
    unjudged = []
    for store in corpus.stores():
        if store.provider is not None and not store.globs[0].families:     # the provider's own unit, as the declaration selects it
            unjudged.append(f'{store.pipeline}/{store.provider}')
    run('pipeline: every provider a pipeline captures for is judged by a family of the pipeline', not unjudged,
        None if not unjudged else f'no family judges {", ".join(unjudged)} - their units promote on their relation alone',
        check='pipeline.every_provider_is_judged')


@check(tier='code', says=(
    'pipeline.families_are_total',
    'pipeline.validate_step_judges_the_declared_families',
    'stage.declared_families_judge',
))
def check_declared_families_judge(run) -> None:
    """A unit is judged by the families its pipeline's declaration names for its kind, whatever
    its measure: claude's session, a prefix unit, by its two families; gemini's ordering
    file, a mirror unit, by none."""
    import tempfile
    import corpus
    judged: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        code = next(s for s in corpus.stores() if s.pipeline == 'agent' and s.provider == 'claude')
        (root / code.input / 'room' / 'project').mkdir(parents=True)
        (root / code.input / 'room' / 'project' / 'session.jsonl').write_text('{}\n')
        for unit in corpus.select(root, code):
            judged[unit.kind] = corpus.judges_of(unit)
        chat = next(s for s in corpus.stores() if s.pipeline == 'browser' and s.provider == 'gemini')
        (root / chat.input).mkdir(parents=True)
        (root / chat.input / 'ordering.txt').write_text('a\n')
        for unit in corpus.select(root, chat):
            judged[unit.kind] = corpus.judges_of(unit)
    want = {'session': ['claude/session', 'sessionConversation'], 'ordering': []}
    run("stage: a unit is judged by the families its declaration names for its kind, whatever its measure", judged == want,
        None if judged == want else f'the judges read {judged}, where they are {want}', check='stage.declared_families_judge')
    # the declaration is total over the pipeline's families, and the validate step validates
    # against exactly the declared families of each kind - read from its enumerate face, the
    # one that lists what it would validate (issues/1018): the declaration is one home only
    # while every reader of the pairing agrees with it.
    import subprocess
    partial = {}
    for name, declared in sorted(corpus.pipelines().items()):
        named = {f for store in corpus.stores() if store.pipeline == name for g in store.globs for f in g.families}
        if named != set(declared['schemas']):
            partial[name] = sorted(set(declared['schemas']) ^ named)
    run('pipeline: every family a pipeline declares judges some kind of its unit, and no other family does', not partial,
        None if not partial else f'declared and judging differ by {partial}', check='pipeline.families_are_total')
    validate = SRC / 'main' / 'agent' / 'validate.sh'
    schema_root = 'rsc/schema/agent/'
    enumerated: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / 'session').mkdir()
        for kind, provider, flag, target in (('session', 'claude', '--session', root / 'session'), ('session', 'gemini', '--session', root / 'session')):
            said = subprocess.run([str(validate), '--enumerate', '--provider', provider, flag, str(target)], capture_output=True, text=True, cwd=REPO_ROOT).stdout
            families = []
            for line in said.splitlines():
                schema = line.split('\t')[1]
                families.append(schema.split(schema_root, 1)[1].rsplit('/', 1)[0])
            enumerated[f'{provider}/{kind}'] = families
    declared_families = {f'{store.provider}/{g.kind}': list(g.families) for store in corpus.stores() if store.pipeline == 'agent' for g in store.globs}
    same = enumerated == declared_families
    run('pipeline: the agent validate step validates each kind of unit against exactly its declared families', same,
        None if same else f'the step enumerates {enumerated}, where the declaration names {declared_families}', check='pipeline.validate_step_judges_the_declared_families')


@check(tier='code', on=['src', 'rsc/cache_io.csv'], says=(
    'cache_io.paths_resolve',
    'cache_io.pipeline_tags_match',
    'cache_io.read_implies_writer',
    'cache_io.registry_parses',
    'cache_io.subtree_named_for_its_writer',
    'cache_io.pipeline_cache_is_the_registrys',
))
def check_cache_io(run) -> None:
    """The declared cache/ IO registry (rsc/cache_io.csv) must not lie: it parses, it
    covers every pipeline's gen root (so clean and rebuild know the pipelines),
    and — the catastrophe guard — no subtree is READ with no WRITER. A cache/ path
    the machinery consumes but nothing produces breaks the 'cache/ is reproducible
    from data/input/' contract: a fresh clone, or `corpus-yoga cache clean`, would strand the
    reader. Written-but-not-read is fine (a terminal output — a page a browser
    reads); only the read side lacking a writer is fatal. Committed registry
    only, so deterministic on any clone: code tier."""
    try:
        rows = cache_io.rows()
    except Exception as e:
        run('cache_io: registry parses: rsc/cache_io.csv', False, str(e), check='cache_io.registry_parses')
        return
    run('cache_io: registry parses: rsc/cache_io.csv', True, check='cache_io.registry_parses')

    # each pipeline's stores have their caches registered (the check below), so a pipeline
    # missing its row fails loudly at first use; this catches the reverse — a
    # pipeline TAG in cache_io naming no real pipeline (or a mismatch either way).
    tagged = cache_io.pipelines()
    run('cache_io: pipeline tags match PIPELINES', tagged == set(PIPELINES),
        f'cache_io tags {sorted(tagged)} != PIPELINES {sorted(PIPELINES)}'
        if tagged != set(PIPELINES) else None, check='cache_io.pipeline_tags_match')

    commands = {c['command'] for c in cli.commands()}
    for r in rows:
        # read-but-not-written: the catastrophe (see docstring).
        read_no_writer = bool(r['read_by']) and not r['written_by']
        run(f'cache_io: {r["cache_path"]}: read implies a writer', not read_no_writer,
            'READ but not WRITTEN — a cache/ dependency nothing produces; name its '
            'producer in written_by, or the cache/ contract breaks' if read_no_writer else None, check='cache_io.read_implies_writer')
        # Every producer/reader RESOLVES — a rename that strands one (how
        # cache/browser/markdown happened) fails here, not silently.
        unresolved = [e for e in r['written_by'] + r['read_by']
                      if not _cache_io_resolves(e, commands)]
        run(f'cache_io: {r["cache_path"]}: producers/readers resolve', not unresolved,
            f'unresolved: {", ".join(unresolved)}' if unresolved else None, check='cache_io.paths_resolve')
        # A subtree is the command that writes it (issues/1181), as logs/<command>/ is: every writer's
        # command is the subtree's name, and a subtree no command writes is named for no command.
        subtree = r['cache_path'].split('/')[1]
        writers = {e.split()[1] for e in r['written_by'] if e.startswith('corpus-yoga ')}
        named = writers == {subtree} if r['written_by'] else subtree not in commands
        run(f'cache_io: {r["cache_path"]}: the subtree is named for the command that writes it', named,
            None if named else (f'written by corpus-yoga {", ".join(sorted(writers))}, named {subtree}' if r['written_by']
                                else f'no command writes it, and corpus-yoga {subtree} is a command'),
            check='cache_io.subtree_named_for_its_writer')

    # Every store's cache is a row of the registry, tagged with its pipeline, and every tagged row a
    # store's cache (issues/1181, issues/1192): the cache each unit's output stands under, at its
    # store's own input address, is the cache clean keeps and the rebuild knows.
    import corpus
    import tier
    stored = sorted((store.pipeline, corpus.store_cache(store.pipeline, store.provider).relative_to(tier.DATA_ROOT).as_posix())
                    for store in corpus.stores())
    registered = sorted((r['pipeline'], r['cache_path']) for r in rows if r['pipeline'])
    run("cache_io: each store's cache is a registry row tagged with its pipeline, and each tagged row a store's cache", stored == registered,
        None if stored == registered else f'the stores cache at {stored}, where the registry says {registered}', check='cache_io.pipeline_cache_is_the_registrys')


@check(tier='code', says=('accumulate.trajectory_contract',), on=['src'])
def check_accumulate_contract(run) -> None:
    """The shared accumulate operation (src/main/export/accumulate.py) obeys
    the contract rsc/CALCULUS.md states: deposit iff
    the content differs from the NEAREST EARLIER deposit, so the store records a
    trajectory, not a set. The design turns on cases a byte-set would get wrong —
    above all that a genuine A→B→A return deposits while a re-stamp of an unchanged
    reading does not. CALCULUS.md holds the sentence; this holds
    it to account. Deterministic, tempdir-only, committed code — code tier: the
    guarantee is guarded in the repo, not only in prose."""
    import tempfile
    import shutil
    d = Path(tempfile.mkdtemp())
    try:
        def acc(stamp, content):
            return _accumulate.accumulate(d, stamp, content,
                                          suffix='.md', exclude={'index.md'})
        # A→B→A: every leg is a trajectory event, so all three deposit — the
        # return is exactly what a folder-wide content set would erase.
        cases = [
            ('A deposits',              acc('2026-01-01T000000Z', 'A') == 'deposited'),
            ('B deposits',              acc('2026-01-02T000000Z', 'B') == 'deposited'),
            ('A→B→A return deposits',   acc('2026-01-03T000000Z', 'A') == 'deposited'),
            # a re-stamp of an unchanged reading (A again, nothing between) is not
            # an event — suppressed; this is the re-stamp bug's fix.
            ('re-stamp suppressed',     acc('2026-01-04T000000Z', 'A') == 'unchanged'),
            # re-run of an existing stamp with identical content is idempotent.
            ('idempotent re-run',       acc('2026-01-03T000000Z', 'A') == 'unchanged'),
            # same stamp, different content: conflict, and nothing is written.
            ('same-stamp mismatch → conflict',
                                        acc('2026-01-03T000000Z', 'Z') == 'conflict'),
            ('conflict leaves deposit immutable',
                (d / '2026-01-03T000000Z.md').read_text() == 'A'),
        ]
        # a non-deposit sibling never enters the comparison.
        (d / 'index.md').write_text('B')
        cases.append(('non-deposit sibling excluded',
                      acc('2026-01-06T000000Z', 'A') == 'unchanged'))
        failed = [name for name, ok in cases if not ok]
        run('accumulate: the CALCULUS trajectory contract (issues/22)',
            not failed, 'cases failed: ' + '; '.join(failed) if failed else None, law='L1 L6', check='accumulate.trajectory_contract')
    finally:
        shutil.rmtree(d, ignore_errors=True)


@check(tier='code', on=['src/main'], says=('pipeline.run_reads_one_unit',))
def check_run_reads_one_unit(run) -> None:
    """A unit's outputs from corpus-yoga pipeline run are the same whatever corpus it is run in:
    in a scratch copy of the checkout, the browser pipeline runs over one planted claude capture,
    then again with an earlier one beside it, and every file the first run wrote the second writes
    at the same path, with the same bytes - each validation record excepted, which carries its
    run's time."""
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile

    def conversation(uuid: str, at: str, name: str) -> dict:
        turn = {'content': [], 'created_at': at, 'updated_at': at, 'attachments': [], 'files': []}
        return {'uuid': uuid, 'name': name, 'summary': '', 'created_at': at, 'updated_at': at, 'model': 'claude-x',
                'current_leaf_message_uuid': uuid[:8] + '-m2', 'chat_messages': [
                    {**turn, 'uuid': uuid[:8] + '-m1', 'parent_message_uuid': '00000000-0000-4000-8000-000000000000',
                     'sender': 'human', 'text': 'hi'},
                    {**turn, 'uuid': uuid[:8] + '-m2', 'parent_message_uuid': uuid[:8] + '-m1',
                     'sender': 'assistant', 'text': 'hello'}]}

    def written(room: Path) -> dict[str, bytes]:
        found = {}
        for root in ('data', 'cache'):
            for path in sorted((room / root).rglob('*')):
                relative = path.relative_to(room).as_posix()
                if path.is_file() and not relative.startswith(('data/input/', 'cache/python/')):
                    found[relative] = b'' if '/validation/' in relative else path.read_bytes()
        return found

    later = ('aaaaaaaa-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000000Z', 'later chat')
    earlier = ('bbbbbbbb-0000-4000-8000-000000000000', '2026-01-01T00:00:00.000000Z', 'earlier chat')
    runs: list[tuple[dict[str, bytes], list[str]]] = []
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        environment = _room_environment(room)
        for units in ([later], [later, earlier]):
            for root in ('data', 'cache'):
                shutil.rmtree(room / root, ignore_errors=True)
            for uuid, at, name in units:
                unit = room / 'data' / 'input' / 'claude' / 'chat' / 'API-capture' / uuid
                unit.mkdir(parents=True)
                (unit / 'apiConversation.json').write_text(json.dumps(conversation(uuid, at, name)))
            ran = subprocess.run([str(room / 'src' / 'main' / 'browser' / 'run.sh')], cwd=room, env=environment,
                                 capture_output=True, text=True, timeout=300)
            runs.append((written(room), (ran.stdout + ran.stderr).strip().splitlines()))
    (alone, words), (beside, _) = runs
    moved = sorted(path for path in alone if path not in beside)
    changed = sorted(path for path in alone if path in beside and alone[path] != beside[path])
    holds = bool(alone) and not moved and not changed
    run('pipeline: a unit\'s outputs from the run are the same whatever corpus it is run in', holds,
        None if holds else
        f'the run over one capture wrote nothing - its last words are {words[-1] if words else "(none)"}' if not alone else
        '; '.join([f'{path} is not written where an earlier capture stands beside it' for path in moved]
                  + [f'{path} holds other bytes where an earlier capture stands beside it' for path in changed]),
        check='pipeline.run_reads_one_unit')


@check(tier='code', on=['src/main/cli/pipeline', 'src/declared_parser.py', 'src/main/cli/cli.py'], says=('pipeline.rehearsal_is_the_run_aimed_at_the_stage',))
def check_rehearsal_is_the_run(run) -> None:
    """The rehearsal is the pipeline run aimed at the stage (issues/1165): `corpus-yoga pipeline run
    --stage-rehearsal`, the flag exclusive of a pipeline and so of an item, which only a pipeline
    precedes - its form says so, the declared parser takes the flag alone and a pipeline with its item,
    and refuses the flag beside a pipeline - and `pipeline rehearse` is no verb. Held over the
    declarations and the parser built from them; no pipeline runs."""
    import contextlib
    import io as _io
    import spell
    from declared_parser import command_parser
    form = next((line.split('form: ', 1)[1] for line in subprocess.run(
        [str(REPO_ROOT / 'corpus-yoga'), 'pipeline', '-h'], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60).stdout.splitlines()
        if line.strip().startswith('form: corpus-yoga pipeline run')), None)
    def parses(*argv: str) -> bool:
        with contextlib.redirect_stderr(_io.StringIO()):
            try:
                command_parser('pipeline').parse_args(list(argv))
            except SystemExit:
                return False
        return True
    said = {'form': form, 'flag alone': parses('run', '--stage-rehearsal'), 'a pipeline and its item': parses('run', 'browser', 'x'),
            'the flag beside a pipeline': parses('run', '--stage-rehearsal', 'browser'), 'rehearse a verb': 'rehearse' in spell.verbs('pipeline')}
    want = {'form': 'corpus-yoga pipeline run [<pipeline> | --stage-rehearsal] [<item>] [--plan]', 'flag alone': True,
            'a pipeline and its item': True, 'the flag beside a pipeline': False, 'rehearse a verb': False}
    run('pipeline: the rehearsal is corpus-yoga pipeline run --stage-rehearsal, exclusive of a pipeline and its item, and rehearse is no verb',
        said == want, None if said == want else f'it holds {said}, where {want}', check='pipeline.rehearsal_is_the_run_aimed_at_the_stage')


@check(tier='code', on=['src/main/cli/pipeline', 'src/main/steps.sh', 'src/main/browser', 'src/main/export', 'src/main/agent'], says=('pipeline.plan_says_map_or_reduce',))
def check_plan_says_map_or_reduce(run) -> None:
    """Each plan says of every step whether it maps one unit or reduces over all of them (issues/1191):
    every step of `corpus-yoga pipeline run --plan` maps, every step of `collate --plan` reduces, and the
    run's one other line is the dev gate it opens on, over src/ and rsc/. Read from the plans as
    printed, which are the step lists that execute."""
    import re
    def steps(verb: str) -> list[str]:
        plan = subprocess.run([str(SRC / 'main' / 'cli' / 'pipeline' / 'pipeline.sh'), verb, '--plan'],
                              capture_output=True, text=True, cwd=REPO_ROOT, timeout=120).stdout
        return [line.strip() for line in plan.splitlines() if re.search(r'\S {2,}\S', line) and not line.strip().startswith(('tooling:', 'tail:'))]
    unmarked = ([f'run: {line[:60]}' for line in steps('run') if '(map - one unit' not in line and not line.startswith('corpus-yoga test run ')]
                + [f'collate: {line[:60]}' for line in steps('collate') if '(reduce - all units' not in line])
    run('pipeline: every step of the run maps one unit and every step of the collate reduces over all, as each plan says', not unmarked,
        '; '.join(unmarked[:6]) + (f'; ... {len(unmarked)} in all' if len(unmarked) > 6 else '') if unmarked else None,
        check='pipeline.plan_says_map_or_reduce')


@check(tier='code', on=['src/main/tier.py', 'src/main/tier.sh', 'src/main/corpus.py'], says=('pipeline.unit_cache_at_its_input_address',))
def check_unit_cache_address(run) -> None:
    """Each unit's run output stands at the unit's own input address under cache/pipeline (issues/1192):
    for a unit of every store, in python and the shell alike, its cache is its path under the input tree,
    a session's .jsonl dropped, re-rooted at cache/pipeline - so that a unit's input and what the run
    derived from it are one relative path under two roots."""
    import corpus
    import tier
    said, want = {}, {}
    for store in corpus.stores():
        unit = store.input / ('m/p/s.jsonl' if store.pipeline == 'agent' and store.provider == 'claude' else 'u')
        path = tier.DATA / 'input' / unit
        cache_of = getattr(tier, 'cache_of', None)
        python_side = cache_of(path).relative_to(tier.DATA_ROOT).as_posix() if cache_of else '?'
        shell_side = subprocess.run(['bash', '-c', 'source "$1"; cache_of "$2"', '_', str(SRC / 'main' / 'tier.sh'), str(path)],
                                    capture_output=True, text=True).stdout.strip()
        shell_side = Path(shell_side).relative_to(tier.DATA_ROOT).as_posix() if shell_side.startswith('/') else '?'
        key = f'{store.pipeline}/{store.provider}'
        said[key] = sorted({python_side, shell_side})
        want[key] = [('cache/pipeline' / unit.with_suffix('') if unit.suffix == '.jsonl' else Path('cache/pipeline') / unit).as_posix()]
    run("pipeline: each unit's run output stands at its own input address under cache/pipeline, in python and the shell alike",
        said == want, None if said == want else f'it resolves as {said}, where {want}', check='pipeline.unit_cache_at_its_input_address')


def _room_environment(room: Path) -> dict:
    """The environment a pipeline runs in as the room's own, outside the gate: the room its root."""
    import os
    import sys
    environment = {name: value for name, value in os.environ.items()
                   if name not in ('CORPUS_YOGA_DEV_GATE', 'CORPUS_YOGA_REHEARSAL', 'CORPUS_YOGA_GATE_CHECK')}
    environment['CORPUS_YOGA_VENV'] = sys.prefix
    environment['CORPUS_YOGA_ROOT'] = str(room)
    return environment


def _scratch_room(scratch: Path) -> Path:
    """A scratch copy of the checkout's code, holding no corpus, for a pipeline to run in."""
    import shutil
    room = scratch.resolve() / 'room'
    shutil.copytree(SRC, room / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    (room / 'rsc').symlink_to(REPO_ROOT / 'rsc')
    shutil.copy(REPO_ROOT / 'pyrightconfig.json', room / 'pyrightconfig.json')
    return room


@check(tier='code', on=['src/main/browser', 'src/main/markdown_projection.py', 'src/main/project_markdown.py'], says=('pipeline.browser_run_renders_each_capture',))
def check_browser_run_renders(run) -> None:
    """The browser pipeline's run renders each capture's markdown, a map (issues/1195): in a scratch copy
    of the checkout, the run over one planted claude capture writes its rendered conversation at the
    capture's own cache address; and a composed file - the run's rendering, the collate's frontmatter
    and summaries link - is byte for byte the file a whole rendering writes, so the collate's output is
    unchanged by the split; and the collate, run after it, deposits that file."""
    import json
    import tempfile
    import markdown_projection as projection
    uuid, at = 'aaaaaaaa-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000000Z'
    turn = {'content': [], 'created_at': at, 'updated_at': at, 'attachments': [], 'files': []}
    capture = {'uuid': uuid, 'name': 'a chat', 'summary': '', 'created_at': at, 'updated_at': at, 'model': 'claude-x',
               'current_leaf_message_uuid': 'aaaaaaaa-m2', 'chat_messages': [
                   {**turn, 'uuid': 'aaaaaaaa-m1', 'parent_message_uuid': '00000000-0000-4000-8000-000000000000', 'sender': 'human', 'text': 'hi'},
                   {**turn, 'uuid': 'aaaaaaaa-m2', 'parent_message_uuid': 'aaaaaaaa-m1', 'sender': 'assistant', 'text': 'hello'}]}
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        environment = _room_environment(room)
        unit = room / 'data' / 'input' / 'claude' / 'chat' / 'API-capture' / uuid
        unit.mkdir(parents=True)
        (unit / 'apiConversation.json').write_text(json.dumps(capture))
        run_script = str(room / 'src' / 'main' / 'browser' / 'run.sh')
        subprocess.run([run_script], cwd=room, env=environment, capture_output=True, text=True, timeout=300)
        rendered = room / 'cache' / 'pipeline' / 'claude' / 'chat' / 'API-capture' / uuid / 'conversation.md'
        held = rendered.read_text() if rendered.is_file() else None
        subprocess.run([run_script, '--collate'], cwd=room, env=environment, capture_output=True, text=True, timeout=300)
        name = '1-a_chat'
        deposited = room / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations' / f'{name}.md'
        collated = deposited.read_text() if deposited.is_file() else None
    lean = projection.project(capture)
    render_body, compose = getattr(projection, 'render_body', None), getattr(projection, 'compose', None)
    frontmatter = {'source': 'browser-capture', 'uuid': uuid, 'human': 1, 'assistant': 1, 'last_activity': '2026-02-01T00:00:00Z',
                   'cross_checked_against': 'none', 'currency': 'unchecked'}
    link = f'../summaries/{name}/index.md'
    same = (render_body is not None and compose is not None
            and compose(render_body(lean), frontmatter, link) == projection.render(lean, frontmatter=frontmatter, summaries_link=link))
    why = ('the run wrote no conversation.md at the capture\'s cache address' if held is None else
           'the run\'s rendering is not the conversation\'s body' if render_body is not None and held != render_body(lean) else
           'a composed file differs from a whole rendering' if not same else
           'the collate deposited no file, or not the whole rendering' if collated != projection.render(lean, frontmatter=frontmatter, summaries_link=link) else None)
    run("pipeline: the browser run renders each capture's markdown at its own cache address, and the collate composes it unchanged",
        why is None, why, check='pipeline.browser_run_renders_each_capture')


@check(tier='code', on=['src/main/cli/pipeline', 'src/main/validation_audit.py'], says=('pipeline.status_offers_collate_where_one_is_owed',))
def check_status_offers_collate(run) -> None:
    """The pipeline's status offers `corpus-yoga pipeline collate` (issues/1188) where one is owed - no unit
    owed a run, and some unit's run output not what the last collate read - so that the offer moves over a
    chain: in a scratch copy of the checkout, a planted capture's run brings the offer; its collate clears it;
    the capture renamed, the run alone is offered; its run brings the collate back."""
    import json
    import tempfile
    uuid, at = 'ffffffff-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000000Z'
    turn = {'content': [], 'created_at': at, 'updated_at': at, 'attachments': [], 'files': []}
    capture = {'uuid': uuid, 'name': 'an offered chat', 'summary': '', 'created_at': at, 'updated_at': at, 'model': 'claude-x',
               'current_leaf_message_uuid': 'ffffffff-0000-4000-8000-000000000002', 'chat_messages': [
                   {**turn, 'uuid': 'ffffffff-0000-4000-8000-000000000001', 'parent_message_uuid': '00000000-0000-4000-8000-000000000000', 'sender': 'human', 'text': 'hi'},
                   {**turn, 'uuid': 'ffffffff-0000-4000-8000-000000000002', 'parent_message_uuid': 'ffffffff-0000-4000-8000-000000000001', 'sender': 'assistant', 'text': 'hello'}]}
    rows = ''.join(f'pipeline\t{name}\n' for name in ('agent', 'browser', 'export'))
    collate, run_browser = 'corpus-yoga pipeline collate', 'corpus-yoga pipeline run browser'
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        unit = room / 'data' / 'input' / 'claude' / 'chat' / 'API-capture' / uuid
        unit.mkdir(parents=True)
        (unit / 'apiConversation.json').write_text(json.dumps(capture))
        subprocess.run([str(room / 'src' / 'main' / 'browser' / 'run.sh')], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        status = [str(room / 'src' / 'run_python_script.sh'), str(room / 'src' / 'main' / 'cli' / 'pipeline' / 'status.py')]
        browser = str(room / 'src' / 'main' / 'browser' / 'run.sh')

        def offers() -> str:
            return subprocess.run(status, input=rows, cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300).stdout

        current = offers()
        subprocess.run([browser, '--collate'], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        collated = offers()
        (unit / 'apiConversation.json').write_text(json.dumps({**capture, 'name': 'an offered chat, renamed'}))
        owed = offers()
        subprocess.run([browser], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        rerun = offers()
    why = ('after the run, the status offers no collate' if collate not in current else
           'after the collate, the status offers the collate again' if collate in collated else
           'with a run owed, the status offers no run' if run_browser not in owed else
           'with a run owed, the status offers the collate, which would refuse' if collate in owed else
           'after the run that moved the rendering, the status offers no collate' if collate not in rerun else None)
    run('pipeline: the status offers the collate where one is owed - after a run moves a rendering, not after a collate - and the run alone where one is',
        why is None, why, check='pipeline.status_offers_collate_where_one_is_owed')


@check(tier='code', on=['src/main/browser', 'src/main/validation_audit.py', 'src/main/project_markdown.py'], says=('pipeline.collate_refuses_a_rendering_older_than_its_input',))
def check_collate_refuses_stale(run) -> None:
    """The collate places only what the run made of the inputs as they stand (issues/1183): in a scratch copy
    of the checkout, a capture run and collated, then recaptured with a new reply and collated again
    without a run, is refused by the collate, which names it and the run it is owed, rather than placing
    the rendering of the capture it replaced."""
    import json
    import tempfile
    uuid, at = 'eeeeeeee-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000000Z'
    turn = {'content': [], 'created_at': at, 'updated_at': at, 'attachments': [], 'files': []}
    capture = {'uuid': uuid, 'name': 'a grown chat', 'summary': '', 'created_at': at, 'updated_at': at, 'model': 'claude-x',
               'current_leaf_message_uuid': 'eeeeeeee-0000-4000-8000-000000000002', 'chat_messages': [
                   {**turn, 'uuid': 'eeeeeeee-0000-4000-8000-000000000001', 'parent_message_uuid': '00000000-0000-4000-8000-000000000000', 'sender': 'human', 'text': 'hi'},
                   {**turn, 'uuid': 'eeeeeeee-0000-4000-8000-000000000002', 'parent_message_uuid': 'eeeeeeee-0000-4000-8000-000000000001', 'sender': 'assistant', 'text': 'hello'}]}
    grown = {**capture, 'current_leaf_message_uuid': 'eeeeeeee-0000-4000-8000-000000000003', 'chat_messages': capture['chat_messages'] + [
        {**turn, 'uuid': 'eeeeeeee-0000-4000-8000-000000000003', 'parent_message_uuid': 'eeeeeeee-0000-4000-8000-000000000002', 'sender': 'human', 'text': 'and again'}]}
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        unit = room / 'data' / 'input' / 'claude' / 'chat' / 'API-capture' / uuid
        unit.mkdir(parents=True)
        (unit / 'apiConversation.json').write_text(json.dumps(capture))
        run_script = str(room / 'src' / 'main' / 'browser' / 'run.sh')
        for mode in ([], ['--collate']):
            subprocess.run([run_script, *mode], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        (unit / 'apiConversation.json').write_text(json.dumps(grown))
        again = subprocess.run([run_script, '--collate'], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
    said = again.stdout + again.stderr
    why = ('the collate placed the rendering of the capture it replaced, and exited 0' if again.returncode == 0 else
           'the collate refused without naming the capture' if uuid not in said else
           'the collate refused without naming the run it is owed' if 'corpus-yoga pipeline run' not in said else None)
    run('pipeline: the collate refuses a capture changed since the run rendered it, naming it and the run it is owed',
        why is None, why, check='pipeline.collate_refuses_a_rendering_older_than_its_input')


@check(tier='code', on=['src/main/export', 'src/main/markdown_projection.py', 'src/main/project_markdown.py'], says=('pipeline.export_run_renders_each_batch',))
def check_export_run_renders(run) -> None:
    """The export pipeline's run renders each batch's conversations, a map (issues/1196): in a scratch
    copy of the checkout, the run over one planted batch writes each conversation's rendering at the
    batch's own cache address, under its atomised name; and the collate, run after it, deposits the whole
    rendering - the run's body dressed with the frontmatter - in the batch's markdown. The batch is
    one no collate has read, as a new export is, so the run needs nothing the collate writes."""
    import json
    import tempfile
    import markdown_projection as projection
    uuid, at, batch = 'cccccccc-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000000Z', 'data-2026-02-03-00-00-00-batch-0000'
    turn = {'content': [], 'created_at': at, 'updated_at': at, 'attachments': [], 'files': []}
    conversation = {'uuid': uuid, 'name': 'an export chat', 'summary': '', 'created_at': at, 'updated_at': at, 'account': {'uuid': uuid},
                    'chat_messages': [
                        {**turn, 'uuid': 'cccccccc-0000-4000-8000-000000000001', 'parent_message_uuid': '00000000-0000-4000-8000-000000000000', 'sender': 'human', 'text': 'hi'},
                        {**turn, 'uuid': 'cccccccc-0000-4000-8000-000000000002', 'parent_message_uuid': 'cccccccc-0000-4000-8000-000000000001', 'sender': 'assistant', 'text': 'hello'}]}
    name = '1-an_export_chat'
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        exports = room / 'data' / 'input' / 'claude' / 'chat' / 'bulk-export'
        (exports / batch).mkdir(parents=True)
        (exports / batch / 'conversations.json').write_text(json.dumps([conversation]))
        run_script = str(room / 'src' / 'main' / 'export' / 'run.sh')
        ran = subprocess.run([run_script, '--input', str(exports)], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        cache = room / 'cache' / 'pipeline' / 'claude' / 'chat' / 'bulk-export' / batch
        rendered = cache / 'rendered' / f'{name}.md'
        held = rendered.read_text() if rendered.is_file() else None
        subprocess.run([run_script, '--input', str(exports), '--collate'], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        said = (ran.stdout + ran.stderr).replace(str(room), '<room>').strip().splitlines()
        deposited = cache / 'markdown' / f'{name}.md'
        collated = deposited.read_text() if deposited.is_file() else None
    lean = projection.project(conversation)
    roles = [message['role'] for message in lean['messages']]
    frontmatter = {'source': 'bulk-export', 'uuid': uuid, 'human': roles.count('human'), 'assistant': roles.count('assistant'),
                   'last_activity': '2026-02-01T00:00:00Z',
                   'cross_checked_against': 'none', 'currency': 'unchecked'}

    why = (f'the run over a batch never collated exited {ran.returncode}: {said[-1] if said else "silently"}' if ran.returncode else
           'the run wrote no rendering at the batch\'s cache address' if held is None else
           'the run\'s rendering is not the conversation\'s body' if held != projection.render_body(lean) else
           'the collate deposited no file, or not the whole rendering' if collated != projection.render(lean, frontmatter=frontmatter) else None)
    run("pipeline: the export run renders each batch's conversations at the batch's own cache address, and the collate composes them unchanged",
        why is None, why, check='pipeline.export_run_renders_each_batch')


@check(tier='code', on=['src/main/agent', 'src/main/markdown_projection.py'], says=('pipeline.agent_run_renders_each_session',))
def check_agent_run_renders(run) -> None:
    """The agent pipeline's run renders each session's markdown, a map (issues/1197): in a scratch copy of
    the checkout, the run over one planted claude session writes its rendering at the session's own cache
    address; and the collate, run after it, deposits that rendering under the session's ordinal name."""
    import json
    import tempfile
    session, at = 'dddddddd-0000-4000-8000-000000000000', '2026-02-01T00:00:00.000Z'
    records = [{'type': 'user', 'uuid': 'dddddddd-0000-4000-8000-000000000001', 'timestamp': at, 'message': {'role': 'user', 'content': 'hi'}},
               {'type': 'assistant', 'uuid': 'dddddddd-0000-4000-8000-000000000002', 'timestamp': at, 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'hello'}]}},
               {'type': 'ai-title', 'aiTitle': 'a code chat', 'sessionId': session}]
    with tempfile.TemporaryDirectory() as scratch:
        room = _scratch_room(Path(scratch))
        project = room / 'data' / 'input' / 'claude' / 'code' / 'machine-transport' / 'a-machine' / 'a-project'
        project.mkdir(parents=True)
        (project / f'{session}.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
        run_script = str(room / 'src' / 'main' / 'agent' / 'run.sh')
        stores = str(room / 'data' / 'input' / '<provider>' / 'code' / 'machine-transport')
        ran = subprocess.run([run_script, '--input', stores], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        said = (ran.stdout + ran.stderr).replace(str(room), '<room>').strip().splitlines()
        rendered = room / 'cache' / 'pipeline' / 'claude' / 'code' / 'machine-transport' / 'a-machine' / 'a-project' / session / 'conversation.md'
        held = rendered.read_text() if rendered.is_file() else None
        subprocess.run([run_script, '--input', stores, '--collate'], cwd=room, env=_room_environment(room), capture_output=True, text=True, timeout=300)
        deposited = room / 'data' / 'output' / 'markdown' / 'claude' / 'code' / 'conversations' / '1-a_code_chat.md'
        collated = deposited.read_text() if deposited.is_file() else None
    why = (f'the run exited {ran.returncode}: {said[-1] if said else "silently"}' if ran.returncode else
           'the run wrote no conversation.md at the session\'s cache address' if held is None else
           'the collate deposited no file, or not the run\'s rendering' if collated != held else None)
    run("pipeline: the agent run renders each session's markdown at its own cache address, and the collate deposits it unchanged",
        why is None, why, check='pipeline.agent_run_renders_each_session')


@check(tier='code', says=('capture.prefix_resolves_to_one',), on=['src/main/cli/browser/capture.py'])
def check_capture_prefix(run) -> None:
    """A browser capture by id files its unit under the conversation's full uuid: a
    typed prefix of eight characters or more resolves to exactly one id of the listing, or
    to none, before any navigation - never typed into a URL the site cannot resolve, never
    used as a directory's name. Held over the resolver alone, in process: Safari is the
    reader's, not the gate's."""
    import importlib
    capture = importlib.import_module('capture')
    resolve = getattr(capture, 'resolve_id', None)
    if resolve is None:
        run('capture: a typed prefix resolves to the one full id it names', False,
            'src/main/cli/browser/capture.py resolves no prefix: the id typed is the id used', check='capture.prefix_resolves_to_one')
        return
    listing = ['d11565d6-640e-465a-9aca-b77a96404d49', 'd1156000-0000-4000-8000-000000000000', '0e537a54-5db8-4164-9a49-06155980b978']
    got = [resolve('d11565d6', listing), resolve('d1156', listing), resolve('ffffffff', listing),
           resolve('d11565d6-640e-465a-9aca-b77a96404d49', listing)]
    expected = ['d11565d6-640e-465a-9aca-b77a96404d49', None, None, 'd11565d6-640e-465a-9aca-b77a96404d49']
    run('capture: a typed prefix resolves to the one full id it names', got == expected,
        None if got == expected else f'the resolver read {got}, where one match, several, none and the full id itself read {expected}',
        check='capture.prefix_resolves_to_one')


@check(tier='code', says=('capture.monotone_record',), on=['src', 'data/output/indexing'])
def check_capture_monotone(run) -> None:
    """L4 where a browser capture BECOMES the record. Gemini has no API, so its DOM
    capture is the only copy, and the page renders just its last few human turns until
    a walk reaches the top — so a walk that ends up shorter than what is already on disk
    failed partway. Held over a temporary tree, never the machine's own captures: the
    property is about the write, and the write must be exercised to test it.

    The growth case is checked beside the refusal, because a guard that also blocks the
    normal path would pass a refusal-only test while breaking every real capture."""
    import contextlib
    import shutil
    import tempfile
    import time
    import safari
    real_downloads = safari.DOWNLOADS

    def turns(n):
        return ''.join(f'## Human ({i})\nq{i}\n\n## Gemini ({i})\na{i}\n\n' for i in range(1, n))

    try:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dl = base / 'downloads'
            dest = base / 'input' / 'gemini' / 'chat' / 'DOM-capture' / 'abc123'
            logs = base / 'logs'
            for d in (dl, dest, logs):
                d.mkdir(parents=True)
            safari.DOWNLOADS = dl

            long_md = turns(10)
            (dest / 'standing.md').write_text(long_md)
            (dl / 'standing.md').write_text(turns(3))
            after = time.time() - 1
            # the guard reports loudly, as it must in a real capture; here the verdicts
            # below are the report, so its output does not belong in the check log
            with contextlib.redirect_stdout(io.StringIO()):
                moved = safari.collect_md_and_log(after, dest, logs)
            kept = (dest / 'standing.md').read_text()
            run('capture: a shorter walk never replaces a longer record', kept == long_md,
                None if kept == long_md else
                f'the record was replaced by a walk holding {len(turn_seq(kept))} turns',
                law='L4', check='capture.monotone_record')
            run('capture: a refused walk reports no markdown', moved == [],
                None if moved == [] else f'returned {moved} — the caller would file it as a '
                f'successful capture', law='L4', check='capture.monotone_record')
            evidence = next(logs.glob('*.gemini.abc123.short.md'), None)   # <stamp>.<provider>.<id>.short.md beside the record (issues/708)
            run('capture: the refused walk is kept as evidence', evidence is not None,
                None if evidence is not None else 'the short capture was discarded, so the '
                'reason for the refusal cannot be inspected', law='L4', check='capture.monotone_record')

            shutil.rmtree(dl)
            dl.mkdir()
            (dl / 'grown.md').write_text(turns(20))
            after = time.time() - 1
            with contextlib.redirect_stdout(io.StringIO()):
                moved = safari.collect_md_and_log(after, dest, logs)
            grew = moved == ['grown.md'] and not (dest / 'standing.md').exists()
            run('capture: a longer walk still supersedes', grew,
                None if grew else f'moved={moved}, dir={sorted(f.name for f in dest.glob("*.md"))} '
                f'— the guard is blocking the normal path', law='L4', check='capture.monotone_record')
    finally:
        safari.DOWNLOADS = real_downloads


@check(tier='code', on=['src/main/markdown_projection.py', 'src/main/page_declaration.py', 'src/main/browser', 'src/main/export', 'src/main/agent', 'src/main/project_markdown.py', 'src/main/compare_sources.py', 'src/main/frontier.py', 'src/main/present_corpus.py', 'src/main/rekey_chats.py', 'src/main/corpus_shape.sh', 'src/main/compare_pages.py'], says=(
    'markdown.turn_count_in_frontmatter',
    'markdown.turns_parse_in_sequence',
))
def check_turn_count_one_home(run) -> None:
    """A conversation's turn count has one home, the frontmatter the projection writes: the projection counts the turns it renders by role, writes them as
    `human` and `assistant`, and refuses a render whose headings disagree; the page reads the
    counts from there; and a turn heading is one the projection wrote - its number the next
    for its role - so a message quoting a rendered conversation's headings adds no turn."""
    import importlib
    projection = importlib.import_module('markdown_projection')
    declaration = importlib.import_module('page_declaration')
    import importlib.util
    # several pipelines hold a render.py, so the agent's is loaded by its path
    spec = importlib.util.spec_from_file_location('agent_render', SRC / 'main' / 'agent' / 'render.py')
    assert spec is not None and spec.loader is not None
    agent_render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_render)
    quoted = 'the file reads:\n\n```\n## Human (1)\n\n## Claude (1) <a id="x"></a>\n```\n'
    conv = {'provider': 'claude', 'project': 'p', 'session_id': '0a1b2c3d-0000-4000-8000-000000000000', 'title': 't',
            'last_activity': '2026-11-09T00:00:00Z', 'harness': 'Claude Code',
            'messages': [{'role': 'human', 'content': 'show me a rendered file', 'uuid': 'h1'},
                         {'role': 'assistant', 'content': quoted, 'uuid': 'a1'},
                         {'role': 'human', 'content': 'thanks', 'uuid': 'h2'}]}
    try:
        md = agent_render.render_session(conv)
        parsed = [role for role, _body in projection.turn_seq(md)]
        said = declaration.declared_of(md)
        head = md.split('\n---\n', 1)[0]
    except Exception as error:   # noqa: BLE001 - the failure IS the finding
        parsed, said, head = f'raised {type(error).__name__}: {error}', {}, ''
    ok = parsed == ['H', 'A', 'H']
    run('markdown: a turn heading is one the projection wrote - a quoted heading adds no turn', ok,
        None if ok else f'the turns parsed as {parsed!r}, where the projection rendered H, A, H', check='markdown.turns_parse_in_sequence')
    home = ('human: 2' in head.splitlines() and 'assistant: 1' in head.splitlines() and not any(l.startswith('turns:') for l in head.splitlines())
            and said.get('human') == 2 and said.get('assistant') == 1)
    run('markdown: the projection writes its turn counts by role, and the page reads them from there', home,
        None if home else f'the frontmatter reads {head.splitlines()[1:]!r} and the page declares {said!r}', check='markdown.turn_count_in_frontmatter')
