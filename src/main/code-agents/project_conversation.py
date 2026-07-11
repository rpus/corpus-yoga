#!/usr/bin/env python
"""
project_conversation.py — project one converted session (session.json) to its
conversation form, conversation.json, the sessionConversation datum
(rsc/schema/code-agents/sessionConversation).

The conversation is the session read as TALK: user and assistant records only —
no sidechain records (a subagent's transcript is its own session), no meta
records, no tool-result carrier records (a user record with toolUseResult is
the harness returning a tool's output, not the user speaking) — each reduced
to its visible text: text blocks joined; thinking, tool_use and tool_result
blocks are working, not talk, and remain in session.json. A record whose
projection is empty (a pure tool step) contributes no turn. Roles use the
corpus vocabulary: a user record projects as 'human', matching the
markdownConversation projection the corpus already renders.

The title is the LAST ai-title record's aiTitle (the same dressing authority
agent.py's census uses); '' where the session never received one. created /
last_activity are the min/max record timestamps — the whole session's span,
not the projected turns' (a session that ends in tool work still ends then).

Usage:
    src/run_python_script.sh src/main/code-agents/project_conversation.py \
        <session-dir>    # reads <session-dir>/session.json, writes conversation.json beside it
"""
import json
import sys
from pathlib import Path

from jsonl_to_json import _write_if_changed


def turn_text(message):
    """The record's visible text: a bare string content verbatim, else its text
    blocks joined by blank lines. Thinking/tool blocks contribute nothing."""
    content = message.get('content')
    if isinstance(content, str):
        return content.strip()
    parts = (block.get('text', '') for block in content or []
             if isinstance(block, dict) and block.get('type') == 'text')
    return '\n\n'.join(p for p in (s.strip() for s in parts) if p)


def project_session(records, session_id, project):
    """One session's records -> the sessionConversation dict."""
    title = ''
    messages = []
    times = sorted(r['timestamp'] for r in records if r.get('timestamp'))
    for r in records:
        kind = r.get('type')
        if kind == 'ai-title':
            title = r.get('aiTitle', '') or title
            continue
        if kind not in ('user', 'assistant'):
            continue
        if r.get('isSidechain') or r.get('isMeta'):
            continue
        if kind == 'user' and ('toolUseResult' in r or 'sourceToolAssistantUUID' in r):
            continue
        text = turn_text(r.get('message') or {})
        if not text:
            continue
        messages.append({'uuid': r['uuid'],
                         'role': 'human' if kind == 'user' else 'assistant',
                         'timestamp': r['timestamp'],
                         'content': text})
    return {'title': title,
            'project': project,
            'session_id': session_id,
            'created': times[0] if times else '',
            'last_activity': times[-1] if times else '',
            'messages': messages}


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: project_conversation.py <session-dir>', file=sys.stderr)
        return 1
    session_dir = Path(sys.argv[1]).resolve()
    records = json.loads((session_dir / 'session.json').read_text())
    conv = project_session(records, session_dir.name, session_dir.parent.name)
    out = session_dir / 'conversation.json'
    _write_if_changed(str(out), lambda dst: json.dump(conv, dst, indent=1, ensure_ascii=False))
    print(f'  conversation.json: {len(conv["messages"])} turn(s)'
          + (f", titled '{conv['title']}'" if conv['title'] else ', no ai-title'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
