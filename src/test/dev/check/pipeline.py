"""pipeline.py - the dev gate's checks of the pipelines: declarations, judges, caches, captures and the corpus format."""
import io
import shutil
import subprocess
import sys
import time
from pathlib import Path

from gate import (  # noqa: F401 - the gate's shared vocabulary
    PIPELINES,
    REPO_ROOT,
    SRC,
    _accumulate,
    _cache_io_resolves,
    cache_io,
    check,
    cli,
    provider,
    turn_seq,
)


@check(tier='code', on=['src/main/corpus.py', 'src/main/pipeline'], says=(
    'pipeline.every_provider_is_judged',
))
def check_providers_judged(run) -> None:
    """Every provider a pipeline captures for is judged by a family of that pipeline
    (issues/965): a unit of the provider has at least one judge, so the rehearsal stands
    before its promotion. The live bug at e44b82f3 on reading-room, 2026-10-22: chat-capture
    declared claude/apiConversation alone, and every gemini unit read `judged: no family -
    promoted on its relation alone`."""
    sys.path.insert(0, str(SRC / 'main'))
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
    its measure (issues/1018): claude's memory, a mirror unit, by projectMemory; gemini's
    ordering file, a mirror unit, by none. The live bug at fe5fd36f on reading-room, 2026-11-06:
    the rehearsal of 2026-11-06T221808Z refused both staged memories at projectMemory v3 and
    the stage judged each `no family of code-transport validates claude's`, since every
    mirror unit was exempt from judging."""
    import tempfile
    sys.path.insert(0, str(SRC / 'main'))
    import corpus
    judged: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        code = next(s for s in corpus.stores() if s.pipeline == 'code-transport' and s.provider == 'claude')
        (root / code.input / 'room' / 'project' / 'memory').mkdir(parents=True)
        (root / code.input / 'room' / 'project' / 'memory' / 'MEMORY.md').write_text('# index\n')
        (root / code.input / 'room' / 'project' / 'session.jsonl').write_text('{}\n')
        for unit in corpus.select(root, code):
            judged[unit.kind] = corpus.judges_of(unit)
        chat = next(s for s in corpus.stores() if s.pipeline == 'chat-capture' and s.provider == 'gemini')
        (root / chat.input).mkdir(parents=True)
        (root / chat.input / 'ordering.txt').write_text('a\n')
        for unit in corpus.select(root, chat):
            judged[unit.kind] = corpus.judges_of(unit)
    want = {'session': ['claude/session', 'sessionConversation'], 'memory': ['claude/projectMemory'], 'ordering': []}
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
    validate = SRC / 'main' / 'pipeline' / 'code-transport' / 'validate.sh'
    schema_root = 'rsc/schema/pipeline/code-transport/'
    enumerated: dict[str, list[str]] = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / 'project' / 'memory').mkdir(parents=True)
        (root / 'session').mkdir()
        for kind, provider, flag, target in (('session', 'claude', '--session', root / 'session'), ('memory', 'claude', '--memory', root / 'project' / 'memory'),
                                              ('session', 'gemini', '--session', root / 'session')):
            said = subprocess.run([str(validate), '--enumerate', '--provider', provider, flag, str(target)], capture_output=True, text=True, cwd=REPO_ROOT).stdout
            families = []
            for line in said.splitlines():
                schema = line.split('\t')[1]
                families.append(schema.split(schema_root, 1)[1].rsplit('/', 1)[0])
            enumerated[f'{provider}/{kind}'] = families
    declared_families = {f'{store.provider}/{g.kind}': list(g.families) for store in corpus.stores() if store.pipeline == 'code-transport' for g in store.globs}
    same = enumerated == declared_families
    run('pipeline: the code-transport validate step validates each kind of unit against exactly its declared families', same,
        None if same else f'the step enumerates {enumerated}, where the declaration names {declared_families}', check='pipeline.validate_step_judges_the_declared_families')


@check(tier='code', on=['src', 'rsc/cache_io.csv'], says=(
    'cache_io.paths_resolve',
    'cache_io.pipeline_tags_match',
    'cache_io.read_implies_writer',
    'cache_io.registry_parses',
))
def check_cache_io(run) -> None:
    """The declared tmp/cache/ IO registry (rsc/cache_io.csv) must not lie: it parses, it
    covers every pipeline's gen root (so clean and sync know the pipelines),
    and — the catastrophe guard — no subtree is READ with no WRITER. A tmp/cache/ path
    the machinery consumes but nothing produces breaks the 'tmp/cache/ is reproducible
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

    # Pipeline.cache_output derives from cache_io.path_for(), so a pipeline
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
            'READ but not WRITTEN — a tmp/cache/ dependency nothing produces; name its '
            'producer in written_by, or the tmp/cache/ contract breaks' if read_no_writer else None, check='cache_io.read_implies_writer')
        # Every producer/reader RESOLVES — a rename that strands one (how
        # tmp/cache/chat-capture/markdown happened) fails here, not silently.
        unresolved = [e for e in r['written_by'] + r['read_by']
                      if not _cache_io_resolves(e, commands)]
        run(f'cache_io: {r["cache_path"]}: producers/readers resolve', not unresolved,
            f'unresolved: {", ".join(unresolved)}' if unresolved else None, check='cache_io.paths_resolve')


@check(tier='code', says=('accumulate.trajectory_contract',), on=['src'])
def check_accumulate_contract(run) -> None:
    """The shared accumulate operation (src/main/pipeline/chat-export/accumulate.py) obeys
    the contract issues/22 unified it to and rsc/CALCULUS.md states: deposit iff
    the content differs from the NEAREST EARLIER deposit, so the store records a
    trajectory, not a set. The design turns on cases a byte-set would get wrong —
    above all that a genuine A→B→A return deposits while a re-stamp of an unchanged
    reading does not (the 196-twin bug). CALCULUS.md holds the sentence; this holds
    it to account. Deterministic, tempdir-only, committed code — code tier: the
    guarantee is guarded in the repo, not only in a PR's prose (issues/22)."""
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


@check(tier='code', says=('capture.prefix_resolves_to_one',), on=['src/main/cli/browser/capture.py'])
def check_capture_prefix(run) -> None:
    """A browser capture by id files its unit under the conversation's full uuid (issues/990): a
    typed prefix of eight characters or more resolves to exactly one id of the listing, or
    to none, before any navigation - never typed into a URL the site cannot resolve, never
    used as a directory's name. Held over the resolver alone, in process: Safari is the
    reader's, not the gate's."""
    import importlib
    sys.path.insert(0, str(SRC / 'main' / 'cli' / 'browser'))
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
    sys.path.insert(0, str(REPO_ROOT / 'src' / 'main' / 'cli' / 'browser'))
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


@check(tier='code', on=['src/main/markdown_projection.py', 'src/main/page_declaration.py', 'src/main/pipeline', 'src/main/model'], says=(
    'markdown.turn_count_in_frontmatter',
    'markdown.turns_parse_in_sequence',
))
def check_turn_count_one_home(run) -> None:
    """A conversation's turn count has one home, the frontmatter the projection writes
    (issues/1001): the projection counts the turns it renders by role, writes them as
    `human` and `assistant`, and refuses a render whose headings disagree; the page reads the
    counts from there; and a turn heading is one the projection wrote - its number the next
    for its role - so a message quoting a rendered conversation's headings adds no turn.
    The live bug: reading-room, 2026-10-31, two code sessions quoting rendered markdown
    declared 1008 and 3449 turns while the page counted 1009 and 3452."""
    import importlib
    sys.path.insert(0, str(SRC / 'main'))
    sys.path.insert(0, str(SRC / 'main' / 'pipeline' / 'code-transport'))
    projection = importlib.import_module('markdown_projection')
    declaration = importlib.import_module('page_declaration')
    render_corpus = importlib.import_module('render_corpus')
    quoted = 'the file reads:\n\n```\n## Human (1)\n\n## Claude (1) <a id="x"></a>\n```\n'
    conv = {'provider': 'claude', 'project': 'p', 'session_id': '0a1b2c3d-0000-4000-8000-000000000000', 'title': 't',
            'last_activity': '2026-11-09T00:00:00Z', 'harness': 'Claude Code',
            'messages': [{'role': 'human', 'content': 'show me a rendered file', 'uuid': 'h1'},
                         {'role': 'assistant', 'content': quoted, 'uuid': 'a1'},
                         {'role': 'human', 'content': 'thanks', 'uuid': 'h2'}]}
    try:
        md = render_corpus.render_session(conv)
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
