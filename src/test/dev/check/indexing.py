"""indexing.py - the dev gate's checks of the paid indexing capture, over a stand-in for its send."""
import json
import os
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
    listed, is offered list-candidates (issues/1123). The status reads a planted capture,
    disposal records and turn bodies, never the room's."""
    import importlib.util
    facts = importlib.import_module('facts')
    # loaded by path: this check's own module holds the name indexing
    spec = importlib.util.spec_from_file_location('indexing_status', SRC / 'main' / 'indexing' / 'indexing.py')
    assert spec is not None and spec.loader is not None
    indexing = importlib.util.module_from_spec(spec)
    sys.modules['indexing_status'] = indexing
    spec.loader.exec_module(indexing)
    kept = {name: getattr(indexing, name) for name in ('INFERRED_FILE', 'CANDIDATES_TXT', 'turn_bodies')}
    offered = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'markdown').mkdir()
        inferred, listed = root / 'inferred-semantic-concepts.json', root / 'candidate-semantic-concepts.txt'
        inferred.write_text(json.dumps({'columns': ['concept'], 'rows': [['quasiparticles'], ['adjunctions']]}))
        setattr(indexing, 'INFERRED_FILE', inferred)
        setattr(indexing, 'CANDIDATES_TXT', listed)
        setattr(indexing, 'turn_bodies', lambda _root: ['on quasiparticles and adjunctions'])
        accepted, rejected = root / 'accepted-semantic-concepts.txt', root / 'rejected-semantic-concepts.txt'
        try:
            def offer() -> list[str]:
                now = facts.now_of(indexing.status(accepted, rejected, root / 'markdown'))
                return sorted(command for acts in now.values() for command in acts)
            offered['unlisted'] = offer()
            listed.write_text(indexing.candidates_report(accepted, rejected, root / 'markdown'))
            offered['listed'] = offer()
            rejected.write_text('adjunctions\n')
            offered['moved'] = offer()
        finally:
            for name, value in kept.items():
                setattr(indexing, name, value)
    expected = {'unlisted': ['corpus-yoga indexing list-candidates'],
                'listed': ['corpus-yoga indexing accept --all', 'corpus-yoga indexing reject --all'],
                'moved': ['corpus-yoga indexing list-candidates']}
    ok = offered == expected
    run('indexing: a queue listed as it stands is offered its disposal, not its listing', ok,
        None if ok else f'offered {offered!r}', check='indexing.listed_queue_offers_disposal')
