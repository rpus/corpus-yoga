#!/usr/bin/env python
"""
fetch.py (corpus-yoga browser fetch) - what a provider's account holds, read through Safari and
recorded whole at tmp/browser/fetch/<provider>.json, so that bare `corpus-yoga browser` says which
chats are new or have grown since their capture, read against the account as last fetched,
without sending.

claude - one read of the account's chat list, each chat with the time it was last updated.
gemini - its list holds no such time, so each captured chat is opened and the end of its last
exchange recorded as it renders; a chat holds what it held, so a changed end is a grown chat.
"""
import json
import sys
import time
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import facts
import send  # every Apple Event is the browser noun's declared safari send (issues/1022)
import account
from declared_parser import verb_parser
from safari import PAGE_LOAD_WAIT, safari_close_work_tab, safari_eval_js, safari_navigate, safari_open_work_tab

SELF = 'src/main/cli/browser/fetch.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]


# NB: no // comments in eval'd JS - safari_eval_js flattens newlines to spaces, so a line
# comment would swallow the rest of the function.
CLAUDE_LIST_JS = """(async function(){
  const orgId = document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1];
  if (!orgId) { window.__fetched = 'ERROR: no lastActiveOrg cookie - not logged in?'; return; }
  const r = await fetch('/api/organizations/' + orgId + '/chat_conversations?limit=10000',
                        {credentials: 'include'});
  if (!r.ok) { window.__fetched = 'ERROR: HTTP ' + r.status; return; }
  const d = await r.json();
  const arr = Array.isArray(d) ? d : (d.data || d.chat_conversations || []);
  window.__fetched = JSON.stringify(arr.map(c => [c.uuid, c.updated_at]));
})();"""

# Each part is sliced SEPARATELY: a long final response must not evict the human end from the
# returned text.
GEMINI_END_JS = """(function(){
  var uq = document.querySelectorAll('user-query');
  var mr = document.querySelectorAll('model-response');
  var u = uq.length ? (uq[uq.length - 1].innerText || '') : '';
  var m = mr.length ? (mr[mr.length - 1].innerText || '') : '';
  return (u.replace(/\\s+/g, ' ').slice(-600) + ' | ' + m.replace(/\\s+/g, ' ').slice(-600));
})()"""


def claude() -> dict:
    """The account's chats, each with the time it was last updated."""
    safari_navigate('https://claude.ai/recents')
    time.sleep(PAGE_LOAD_WAIT + 2)
    safari_eval_js(CLAUDE_LIST_JS)
    raw = ''
    for _ in range(30):
        raw = safari_eval_js('window.__fetched || ""')
        if raw:
            break
        time.sleep(0.5)
    if not raw or raw.startswith('ERROR'):
        raise RuntimeError(facts.phrase('listing fetch failed ({why})', why=raw or 'timeout'))
    return {'updated': dict(json.loads(raw))}


def gemini() -> dict:
    """The account's chats, and the rendered end of each captured one."""
    from capture import PROVIDERS, ids_from_safari, wait_for_ready
    cfg = PROVIDERS['gemini']
    ids = ids_from_safari('gemini', cfg)
    captured = account.captured('gemini')
    ends = {}
    for cid in (i for i in ids if i in captured):
        safari_navigate(cfg['chat_url'].format(id=cid))
        time.sleep(PAGE_LOAD_WAIT)
        wait_for_ready(cfg['ready_sel'])
        ends[cid] = account.alnum(safari_eval_js(GEMINI_END_JS))
    return {'listed': ids, 'ends': ends}


def main() -> int:
    provider = verb_parser('browser', 'fetch').parse_args().provider
    try:
        previous = safari_open_work_tab()
        try:
            read = claude() if provider == 'claude' else gemini()
        finally:
            safari_close_work_tab(previous)
    except send.SendRefused as refused:
        facts.report(None, f'browser fetch: NOT DONE - {refused}')
        return 1
    except RuntimeError as failed:
        facts.report(None, f'browser fetch: NOT DONE - {failed}')
        return 1
    account.RECORD.mkdir(parents=True, exist_ok=True)
    record = account.RECORD / f'{provider}.json'
    record.write_text(json.dumps({'fetched': tier.stamp_of('browser fetch'), **read}, indent=1) + '\n')
    listed = len(read['updated']) if provider == 'claude' else len(read['listed'])
    facts.report(None, 'browser fetch: DONE - ' + facts.phrase('{n} chat(s) of the {provider} account recorded at {record}',
                                                                n=listed, provider=provider, record=record.relative_to(REPO)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
