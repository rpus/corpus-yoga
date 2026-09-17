#!/usr/bin/env python
"""
project_conversation.py - project one converted Antigravity session (session.json) to its
conversation form, conversation.json, the sessionConversation datum
(rsc/schema/pipeline/code-transport/sessionConversation).

The conversation is the session read as TALK. A USER_INPUT step is the person speaking;
the harness wraps what they typed in <USER_REQUEST> beside its own additions, and the
turn is what they typed. A PLANNER_RESPONSE step that carries content is the model
speaking; its thinking and its tool calls are working, not talk, and a planner response
with no content contributes no turn. Every other step - the tools' GENERIC results, the
system's messages and checkpoints - is the harness, and remains in session.json.

A step carries no identity of its own: step indices repeat where the harness resumed a
session, so a turn has no uuid and the corpus anchors it by role and count, as it does a
gemini chat's. The title is the summary row's; created / last_activity are the first and
last step's created_at, the whole session's span.

Usage:
    src/run_python_script.sh src/main/pipeline/code-transport/gemini/project_conversation.py \
        <session-dir>    # reads <session-dir>/session.json, writes conversation.json beside it
"""
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/pipeline/code-transport/gemini/project_conversation.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main' / 'pipeline' / 'code-transport'))
from write_if_changed import write_if_changed  # noqa: E402

USER_REQUEST = re.compile(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', re.S)


def turn_text(step) -> str:
    content = step.get('content')
    if not isinstance(content, str):
        return ''
    if step.get('type') == 'USER_INPUT':
        typed = USER_REQUEST.search(content)
        return (typed.group(1) if typed else content).strip()
    return content.strip()


def project_session(steps, summary, session_id, project):
    """One session's steps -> the sessionConversation dict."""
    messages = []
    for step in steps:
        role = {'USER_INPUT': 'human', 'PLANNER_RESPONSE': 'assistant'}.get(step.get('type'))
        text = turn_text(step) if role else ''
        if not text:
            continue
        messages.append({'role': role, 'timestamp': step['created_at'], 'content': text})
    times = [s['created_at'] for s in steps if s.get('created_at')]
    return {'provider': 'gemini',
            'harness': 'Antigravity',
            'title': summary.get('title') or '',
            'project': project,
            'session_id': session_id,
            'created': min(times) if times else '',
            'last_activity': max(times) if times else '',
            'messages': messages}


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: project_conversation.py <session-dir>', file=sys.stderr)
        return 1
    session_dir = Path(sys.argv[1]).resolve()
    steps = json.loads((session_dir / 'session.json').read_text())
    summary_file = session_dir / 'session.json.summary'
    summary = json.loads(summary_file.read_text()) if summary_file.is_file() else {}
    conv = project_session(steps, summary, session_dir.name, session_dir.parent.name)
    out = session_dir / 'conversation.json'
    write_if_changed(str(out), lambda dst: json.dump(conv, dst, indent=1, ensure_ascii=False))
    print(f'  conversation.json: {len(conv["messages"])} turn(s)'
          + (f", titled '{conv['title']}'" if conv['title'] else ', untitled'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
