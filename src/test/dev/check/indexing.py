"""indexing.py - the dev gate's checks of the paid indexing capture, over a stand-in for its send."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from gate import (
    REPO_ROOT,
    SRC,
    check,
)


@check(tier='code', says=('indexing.reply_without_text_is_named', 'indexing.reply_text_read_wherever_it_stands'), on=['src/main/indexing', 'src/main/tier.sh', 'src/main/report.sh'])
def check_reply_without_text(run) -> None:
    """A reply whose blocks hold no text ends the capture by name - the table and the block
    types it got - and is kept beside the run's record, never handed on as `null` to the
    rekey (issues/1121). capture.sh is loaded, its paid send replaced by a canned reply;
    every send is refused besides, so nothing outward can run."""
    reply = {'content': [{'type': 'thinking', 'thinking': 'weighing the categories'}], 'stop_reason': 'end_turn'}
    with tempfile.TemporaryDirectory() as tmp:
        canned = Path(tmp) / 'reply.json'
        canned.write_text(json.dumps(reply))
        logs = Path(tmp) / 'logs'
        script = ('canned="$2"; source "$1"; send() { cat "$canned"; }; LOGS_DIR="$3"; '
                  "set +e; capture_table '[\"chat\"]' 'chat: x' 'task' 'data' chat-categories; echo \"rc=$?\"")   # capture.sh sets -e
        env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'CORPUS_YOGA_ACT', 'CORPUS_YOGA_STAMP')}
        env.update(CORPUS_YOGA_NO_SEND='1', ANTHROPIC_API_KEY='stand-in')
        done = subprocess.run(['bash', '-c', script, '_', str(SRC / 'main' / 'indexing' / 'capture.sh'), str(canned), str(logs)],
                              capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120)
        kept = sorted(p for p in logs.rglob('*.reply.json') if '.chat-categories.' in p.name)
        held = bool(kept) and json.loads(kept[0].read_text()) == reply
    named = 'the chat-categories reply holds no text block - its blocks are thinking' in done.stderr
    refused = 'rc=1' in done.stdout and 'null' not in done.stdout
    ok = named and refused and held
    run('indexing: a reply that holds no text ends the capture by name, and the reply is kept', ok,
        None if ok else f'stdout {done.stdout.strip()[-160:]!r}; stderr {done.stderr.strip()[-240:]!r}; reply kept: {held}',
        check='indexing.reply_without_text_is_named')

    # A reply whose text stands after another block is read from its text block (issues/1121).
    reply = {'content': [{'type': 'thinking', 'thinking': 'weighing the categories'},
                         {'type': 'text', 'text': '{"columns": ["chat"], "rows": [[1]]}'}], 'stop_reason': 'end_turn'}
    with tempfile.TemporaryDirectory() as tmp:
        canned = Path(tmp) / 'reply.json'
        canned.write_text(json.dumps(reply))
        done = subprocess.run(['bash', '-c', script, '_', str(SRC / 'main' / 'indexing' / 'capture.sh'), str(canned), str(Path(tmp) / 'logs')],
                              capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120)
    read = done.stdout.strip() == '{"columns": ["chat"], "rows": [[1]]}\nrc=0'
    run('indexing: a reply\'s text is read from its text block, wherever it stands', read,
        None if read else f'stdout {done.stdout.strip()[-160:]!r}; stderr {done.stderr.strip()[-160:]!r}',
        check='indexing.reply_text_read_wherever_it_stands')


@check(tier='code', says=('indexing.listed_queue_offers_disposal',), on=['src/main/indexing', 'src/main/facts.py', 'src/main/cli/indexing'])
def check_listed_queue_offers_disposal(run) -> None:
    """Once the queue is listed as it stands, the indexing status offers accept --all and
    reject --all, never list-candidates again; a queue listed before it moved, or never
    listed, is offered list-candidates (issues/1123); and a queue disposed whole, its listing
    rewritten empty as --all leaves it, is offered no disposal, only the build of the judged
    index (issues/1125). The status reads a planted capture, disposal records and turn bodies,
    never the room's."""
    import importlib.util
    facts = importlib.import_module('facts')
    # loaded by path: this check's own module holds the name indexing
    spec = importlib.util.spec_from_file_location('indexing_status', SRC / 'main' / 'indexing' / 'indexing.py')
    assert spec is not None and spec.loader is not None
    indexing = importlib.util.module_from_spec(spec)
    sys.modules['indexing_status'] = indexing
    spec.loader.exec_module(indexing)
    kept = {name: getattr(indexing, name) for name in ('INFERRED_FILE', 'CANDIDATES_TXT', 'INDEXED_FILE', 'turn_bodies') if hasattr(indexing, name)}
    offered = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'markdown').mkdir()
        inferred, listed = root / 'inferred-semantic-concepts.json', root / 'candidate-semantic-concepts.txt'
        inferred.write_text(json.dumps({'columns': ['concept'], 'rows': [['quasiparticles'], ['adjunctions']]}))
        setattr(indexing, 'INFERRED_FILE', inferred)
        setattr(indexing, 'CANDIDATES_TXT', listed)
        setattr(indexing, 'INDEXED_FILE', root / 'indexed-semantic-concepts.json')
        setattr(indexing, 'turn_bodies', lambda _root: ['on quasiparticles and adjunctions'])
        accepted, rejected = root / 'accepted-semantic-concepts.txt', root / 'rejected-semantic-concepts.txt'
        try:
            def offer() -> list[str] | str:
                try:
                    now = facts.now_of(indexing.status(accepted, rejected, root / 'markdown'))
                except Exception as error:   # noqa: BLE001 - the failure IS the finding
                    return f'raised {type(error).__name__}: {error}'
                return sorted(command for acts in now.values() for command in acts)
            offered['unlisted'] = offer()
            listed.write_text(indexing.candidates_report(accepted, rejected, root / 'markdown'))
            offered['listed'] = offer()
            rejected.write_text('adjunctions\n')
            offered['moved'] = offer()
            rejected.write_text('adjunctions\nquasiparticles\n')
            listed.write_text(indexing.candidates_report(accepted, rejected, root / 'markdown'))
            offered['disposed'] = offer()
        finally:
            for name, value in kept.items():
                setattr(indexing, name, value)
    expected = {'unlisted': ['corpus-yoga indexing list-candidates'],
                'listed': ['corpus-yoga indexing accept --all', 'corpus-yoga indexing reject --all'],
                'moved': ['corpus-yoga indexing list-candidates'],
                'disposed': ['corpus-yoga indexing build']}
    ok = offered == expected
    run('indexing: a queue listed as it stands is offered its disposal, not its listing; a disposed one, the build', ok,
        None if ok else f'offered {offered!r}', check='indexing.listed_queue_offers_disposal')


@check(tier='code', says=('indexing.judged_index_waits_in_order', 'indexing.no_run_builds_the_index_or_the_page',
                          'server.book_index_is_written_from_the_judged_index', 'site.concepts_are_the_judged_index'),
       on=['src/main/indexing', 'src/main/cli/server/book_index.py', 'src/main/present_corpus.py', 'src/main/cli/pipeline', 'src/main/cli/site'])
def check_judged_index(run) -> None:
    """The server's book index and the site's corpus page are built only from a current capture
    the reader has judged (issues/1125): the judged index waits on the paid capture, then on the
    reader's judgement, then on its build, in that order; the server's index.md and the page's
    concept table are both written from it; and no pipeline run builds any of them. Held over a
    planted capture, disposal record and corpus, never the room's."""
    import importlib
    indexing = importlib.import_module('indexing')
    waits_on = getattr(indexing, 'waits_on', None)
    if waits_on is None:
        run('indexing: the judged index waits on the capture, then the judgement, then its build', False,
            'src/main/indexing/indexing.py has no waits_on: nothing says what the index and the page wait on',
            check='indexing.judged_index_waits_in_order')
    else:
        kept = {name: getattr(indexing, name) for name in ('INFERRED_FILE', 'INDEXED_FILE', 'capture_lag')}
        said = []
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                conversations = root / 'markdown' / 'claude' / 'chat' / 'conversations'
                conversations.mkdir(parents=True)
                page = conversations / '01-physics.md'
                page.write_text('## Human (1) <a id="h1"></a>\n\non quasiparticles\n\n---\n\n## Claude (1) <a id="a1"></a>\n\nquasiparticles indeed\n\n---\n')
                inferred = root / 'inferred-semantic-concepts.json'
                inferred.write_text(json.dumps({'columns': ['word', 'count', 'provider'], 'rows': [['quasiparticles', 9, 'claude']]}))
                accepted, rejected = root / 'accepted-semantic-concepts.txt', root / 'rejected-semantic-concepts.txt'
                setattr(indexing, 'INFERRED_FILE', inferred)
                setattr(indexing, 'INDEXED_FILE', root / 'indexed-semantic-concepts.json')
                lag = [3]
                setattr(indexing, 'capture_lag', lambda: lag[0])
                markdown = root / 'markdown'
                said.append(waits_on(accepted, rejected, markdown))
                lag[0] = 0
                said.append(waits_on(accepted, rejected, markdown))
                accepted.write_text('quasiparticles\n')
                said.append(waits_on(accepted, rejected, markdown))
                built = indexing.indexed(markdown, accepted)
                indexing.INDEXED_FILE.write_text(json.dumps(built))
                said.append(waits_on(accepted, rejected, markdown))
                page.write_text(page.read_text() + '\n## Human (2) <a id="h2"></a>\n\nmore quasiparticles\n\n---\n')
                said.append(waits_on(accepted, rejected, markdown))
        finally:
            for name, value in kept.items():
                setattr(indexing, name, value)
        want = ['waits on the paid capture - corpus-yoga indexing capture',
                "waits on the reader's judgement of 1 concept(s) - corpus-yoga indexing",
                'waits on corpus-yoga indexing build', None, 'waits on corpus-yoga indexing build']
        run('indexing: the judged index waits on the capture, then the judgement, then its build - and again once the corpus moves',
            said == want, None if said == want else f'waited on {said!r}', check='indexing.judged_index_waits_in_order')

        physics, matter = (f'{provider}/chat/conversations/01-{name}.md' for provider, name in (('claude', 'physics'), ('gemini', 'matter')))
        index = {'columns': ['headword', 'aliases', 'locators'], 'conversations': 2, 'built_from': 'sha256:x',
                 'rows': [['quasiparticles', [], [[physics, 'H', 1, 'h1'], [matter, 'G', 2, 'g2']]],
                          ['zymurgy', ['brewing'], []]]}
        book_index = importlib.import_module('book_index')
        text = book_index.index_markdown(index)
        expected = ('## Q\n\n### quasiparticles\n'
                    f'- [01-physics]({physics}#h1) — [H1]({physics}#h1)\n'
                    f'- [01-matter]({matter}#g2) — [G2]({matter}#g2)\n\n'
                    '---\n\n1/2 headwords located; 2 turn locators across 2 conversations.\n')
        ok = text.endswith(expected) and 'zymurgy' not in text
        run('server: the book index is written from the judged index, a headword with no locator left out', ok,
            None if ok else f'wrote {text[-400:]!r}', check='server.book_index_is_written_from_the_judged_index')
        present = importlib.import_module('present_corpus')
        table = present.concept_table(index)
        want_table = {'columns': ['word', 'count', 'provider'], 'rows': [['quasiparticles', 2, 'both']]}
        run('site: the page\'s concepts are the judged index - each located headword by its turns and their providers',
            table == want_table, None if table == want_table else f'the table was {table!r}', check='site.concepts_are_the_judged_index')

    plan = subprocess.run([str(SRC / 'main' / 'cli' / 'pipeline' / 'pipeline.sh'), '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT, timeout=120).stdout
    built = [line.strip() for line in plan.splitlines()
             if re.search(r'\b(indexing|server|site)\b\S*\s+.*\b(build|render|assemble)\b', line)]
    run('pipeline: no run builds the index, the book index or the corpus page', not built,
        None if not built else f'the plan builds them: {built!r}', check='indexing.no_run_builds_the_index_or_the_page')
