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
                  "set +e; capture_table '[\"chat\"]' 'chat: x' 'task' 'data' chat-categories '{\"type\": \"object\"}'; echo \"rc=$?\"")   # capture.sh sets -e
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
                         {'type': 'text', 'text': '{"rows": [{"chat": 1}]}'}], 'stop_reason': 'end_turn'}
    with tempfile.TemporaryDirectory() as tmp:
        canned = Path(tmp) / 'reply.json'
        canned.write_text(json.dumps(reply))
        done = subprocess.run(['bash', '-c', script, '_', str(SRC / 'main' / 'indexing' / 'capture.sh'), str(canned), str(Path(tmp) / 'logs')],
                              capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120)
    read = done.stdout.strip() == '{"columns": ["chat"], "rows": [[1]]}\nrc=0'
    run('indexing: a reply\'s text is read from its text block, wherever it stands', read,
        None if read else f'stdout {done.stdout.strip()[-160:]!r}; stderr {done.stderr.strip()[-160:]!r}',
        check='indexing.reply_text_read_wherever_it_stands')


@check(tier='code', says=('indexing.request_carries_the_table_shape', 'indexing.refused_reading_says_why'),
       on=['src/main/indexing', 'rsc/schema/indexing', 'src/main/report.sh', 'src/main/cli/indexing'])
def check_reply_shape(run) -> None:
    """The capture sends the API the shape of the table it asks for (issues/1161): taken from the
    table's schema family, with nothing the API's structured outputs refuse, so the rows come
    back typed; the categories table asks for the conversation's number and a palette category.
    A reading that still fails its family ends on one verdict naming the column."""
    shaper = SRC / 'main' / 'indexing' / 'reply_shape.py'
    launcher = SRC / 'run_python_script.sh'
    refused_keywords = {'minimum', 'maximum', 'minLength', 'maxLength', 'minItems', 'maxItems', 'additionalItems', 'pattern', 'multipleOf'}

    def shape(*words: str) -> object:
        done = subprocess.run([str(launcher), str(shaper), 'schema', *words], capture_output=True, text=True, cwd=REPO_ROOT, timeout=60)
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else f'exit {done.returncode}: {done.stderr.strip()[-160:]}'

    def keywords(node) -> set:
        if isinstance(node, dict):
            return set(node) | set().union(*(keywords(v) for v in node.values()))
        if isinstance(node, list):
            return set().union(*(keywords(v) for v in node)) if node else set()
        return set()

    def columns_of(said) -> dict:
        try:
            return said['properties']['rows']['items']['properties']
        except (TypeError, KeyError):
            return {}
    concepts = shape('semanticConcepts', '["word", "count", "provider"]') if shaper.is_file() else 'no reply_shape.py'
    categories = shape('chatCategories', '["chat", "category"]', 'chat={"type": "integer"}',
                       'category={"type": "string", "enum": ["one", "two"]}') if shaper.is_file() else 'no reply_shape.py'
    concept_columns, category_columns = columns_of(concepts), columns_of(categories)
    shaped = (concept_columns.get('count', {}).get('type') == 'integer'
              and concept_columns.get('provider', {}).get('enum') == ['claude', 'gemini', 'both']
              and concept_columns.get('word', {}).get('type') == 'string'
              and not keywords(concepts) & refused_keywords
              and category_columns.get('chat', {}).get('type') == 'integer'
              and category_columns.get('category', {}).get('enum') == ['one', 'two'])
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'CORPUS_YOGA_ACT', 'CORPUS_YOGA_STAMP')}
    env.update(CORPUS_YOGA_NO_SEND='1')
    capture_sh = str(SRC / 'main' / 'indexing' / 'capture.sh')
    body: object = ''
    if isinstance(concepts, dict):
        done = subprocess.run(['bash', '-c', 'source "$1"; table_request \'["word"]\' "word: x" task data "$2"', '_', capture_sh, json.dumps(concepts)],
                              capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=60)
        try:
            body = json.loads(done.stdout)
        except ValueError:
            body = done.stdout.strip()[-200:] + done.stderr.strip()[-200:]
    sent = (isinstance(body, dict) and body.get('output_config', {}).get('format') == {'type': 'json_schema', 'schema': concepts}
            and 'valid JSON' not in json.dumps(body))
    ok = shaped and sent
    run('indexing: the capture sends the shape of the table it asks for, from the table\'s family', ok,
        None if ok else f'the concepts shape {str(concepts)[:300]}; the categories shape {str(categories)[:200]}; the request {str(body)[:300]}',
        check='indexing.request_carries_the_table_shape')

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / 'inferred-semantic-concepts.json'
        staged.write_text(json.dumps({'columns': ['word', 'count', 'provider'], 'rows': [['category theory', '100', 'both']]}))
        done = subprocess.run(['bash', '-c', 'source "$1"; validate_capture "$2" semanticConcepts', '_', capture_sh, str(staged)],
                              capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=60)
    verdict = next((line.strip() for line in done.stdout.splitlines() if 'indexing capture: NOT DONE' in line), '')
    says = verdict.startswith('indexing capture: NOT DONE - the reading fails semanticConcepts v2 at rows/0/count') and 'not deposited' in verdict
    run('indexing: a reading that fails its family ends on a verdict naming the column', says,
        None if says else f'the capture ended {verdict or done.stdout.strip()[-200:]!r}', check='indexing.refused_reading_says_why')


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
    """The server's book index and the site's corpus page are built only from the capture in use as
    the reader has judged it (issues/1125): the judged index waits on the reader's judgement, then
    on its build, in that order - a capture is no step before them, taken at any time and replacing
    nothing until adopted (issues/1185); the server's index.md and the page's
    concept table are both written from it; and no pipeline run builds any of them. Held over a
    planted capture, disposal record and corpus, never the room's."""
    import importlib
    indexing = importlib.import_module('indexing')
    waits_on = getattr(indexing, 'waits_on', None)
    if waits_on is None:
        run('indexing: the judged index waits on the judgement, then its build', False,
            'src/main/indexing/indexing.py has no waits_on: nothing says what the index and the page wait on',
            check='indexing.judged_index_waits_in_order')
    else:
        kept = {name: getattr(indexing, name) for name in ('INFERRED_FILE', 'INDEXED_FILE')}
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
                markdown = root / 'markdown'
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
        want = ["waits on the reader's judgement of 1 concept(s) - corpus-yoga indexing",
                'waits on corpus-yoga indexing build', None, 'waits on corpus-yoga indexing build']
        run('indexing: the judged index waits on the judgement, then its build - and again once the corpus moves',
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

    plan = ''.join(subprocess.run([str(SRC / 'main' / 'cli' / 'pipeline' / 'pipeline.sh'), verb, '--plan'],
                                  capture_output=True, text=True, cwd=REPO_ROOT, timeout=120).stdout
                   for verb in ('run', 'collate'))
    built = [line.strip() for line in plan.splitlines()
             if re.search(r'\b(indexing|server|site)\b\S*\s+.*\b(build|render|assemble)\b', line)]
    run('pipeline: no run or collate builds the index, the book index or the corpus page', not built,
        None if not built else f'the plan builds them: {built!r}', check='indexing.no_run_builds_the_index_or_the_page')


@check(tier='code', on=['src/main/indexing', 'src/main/cli/indexing'], says=('indexing.a_capture_is_adopted_never_replaced',))
def check_capture_adopted(run) -> None:
    """A paid capture replaces nothing (issues/1185): it is deposited under its stamp beside every
    earlier one, the capture in use - the pair accept, reject, build and the site read - left as it
    stands, and said as one from before deposits where no deposit holds it; `corpus-yoga indexing
    adopt <stamp>` makes a deposit the capture in use, which the status then names by its stamp.
    Held over planted files, the module's paths pointed at them, never the room's."""
    import importlib
    import json
    import tempfile
    indexing = importlib.import_module('indexing')
    names = ('INFERRED_FILE', 'CATEGORIES_FILE', 'CAPTURES_DIR')
    kept = {name: getattr(indexing, name, None) for name in names}
    said: dict[str, object] = {}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'indexing'
            root.mkdir()
            concepts, categories = root / 'inferred-semantic-concepts.json', root / 'inferred-chat-categories.json'
            def table(rows: list) -> str:
                return json.dumps({'columns': ['a', 'b'], 'rows': rows}) + '\n'
            concepts.write_text(table([['old concept', 1]]))
            categories.write_text(table([['c1', 'practical']]))
            staged = Path(tmp) / 'staged'
            staged.mkdir()
            (staged / concepts.name).write_text(table([['new concept', 2]]))
            (staged / categories.name).write_text(table([['c1', 'creative'], ['c2', 'practical']]))
            for name, value in zip(names, (concepts, categories, root / 'capture')):
                setattr(indexing, name, value)
            deposit, adopt, in_use = (getattr(indexing, f, None) for f in ('deposit', 'adopt', 'in_use'))
            if not (deposit and adopt and in_use):
                said['verbs'] = 'src/main/indexing/indexing.py has no deposit, adopt and in_use'
            else:
                deposit(staged, '2026-11-26T000000Z')
                said['deposited'] = sorted(p.name for p in (root / 'capture' / '2026-11-26T000000Z').iterdir())
                said['left in use'] = json.loads(concepts.read_text())['rows']
                said['before'] = in_use()
                adopt('2026-11-26T000000Z')
                said['adopted'] = (json.loads(concepts.read_text())['rows'], json.loads(categories.read_text())['rows'])
                said['after'] = in_use()
    finally:
        for name, value in kept.items():
            if value is not None:
                setattr(indexing, name, value)
    want = {'deposited': ['inferred-chat-categories.json', 'inferred-semantic-concepts.json'], 'left in use': [['old concept', 1]],
            'before': None, 'adopted': ([['new concept', 2]], [['c1', 'creative'], ['c2', 'practical']]), 'after': '2026-11-26T000000Z'}
    run('indexing: a capture is deposited beside every earlier one and replaces the capture in use only when adopted',
        said == want, None if said == want else f'it held {said}, where {want}', check='indexing.a_capture_is_adopted_never_replaced')
