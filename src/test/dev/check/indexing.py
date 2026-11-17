"""indexing.py - the dev gate's checks of the paid indexing capture, over a stand-in for its send."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from gate import (
    REPO_ROOT,
    SRC,
    check,
)


@check(tier='code', says=('indexing.reply_without_text_is_named',), on=['src/main/indexing', 'src/main/tier.sh', 'src/main/report.sh'])
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
