"""
render.py - render one projected session (conversation.json, the sessionConversation datum) to its
corpus markdown, a map (issues/1197): conversation.md, and facts.json with what the collate names,
orders and dedupes it by, beside it at the session's cache address. A session's rendering reads the
session alone; which copy across machines is placed, and under which ordinal, is the collate's
(src/main/agent/render_corpus.py).

A session with no projected talk renders honestly: title, provenance bullets, no turns.

Usage:
    src/run_python_script.sh src/main/agent/render.py <session-dir>
"""
import json
import sys
from pathlib import Path
from markdown_projection import FACTS, MD033_PRAGMA, RENDERED, write_if_changed

SELF = 'src/main/agent/render.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'


def render_session(conv):
    """sessionConversation dict -> corpus markdown. Mirrors render() in
    markdown_projection.py: frontmatter provenance dressing, h1 title, a
    plain-bullet preamble (sessions have no URL to link), role-labelled turn
    headings each carrying its durable anchor: the message uuid where the provider's
    record has one, else the role and count, as a gemini chat's turns are anchored - and the
    turn's instant beside it where the record has one (issues/1007), since a session's uuids
    are v4 and carry none, and the corpus page draws a conversation's bars from its turns'
    instants."""
    label = {'human': 'Human', 'assistant': conv['provider'].capitalize()}
    count = {'human': 0, 'assistant': 0}
    roles = [m['role'] for m in conv['messages']]
    out = ['---',
           'source: code-session',
           f"project: {conv['project']}",
           f"uuid: {conv['session_id']}",
           f"human: {roles.count('human')}",               # the turn count's one home, by role (issues/1001)
           f"assistant: {roles.count('assistant')}",
           f"last_activity: {conv['last_activity']}",
           '---', '',
           f"# {conv['title'] or 'Session ' + conv['session_id'][:8]}", '',
           MD033_PRAGMA, '',
           f"- {conv['harness']} session `{conv['session_id']}`",
           f"- Project `{conv['project']}`",
           '']
    for m in conv['messages']:
        count[m['role']] += 1
        anchor = m.get('uuid') or f"{label[m['role']].lower()}-{count[m['role']]}"
        at = f' data-at="{m["timestamp"][:19]}Z"' if m.get('timestamp') else ''   # second precision, as dormant_from
        out += [f"## {label[m['role']]} ({count[m['role']]}) <a id=\"{anchor}\"{at}></a>",
                '', m['content'], '', '---', '']
    return '\n'.join(out).rstrip() + '\n'


def facts(conv):
    """What the collate places a session by: its identity, its title, its span, and its turns,
    by which the maximal copy across machines is chosen."""
    return {'provider': conv['provider'], 'session_id': conv['session_id'], 'title': conv['title'],
            'created': conv['created'], 'last_activity': conv['last_activity'], 'turns': len(conv['messages'])}


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: render.py <session-dir>', file=sys.stderr)
        return 1
    session_dir = Path(sys.argv[1]).resolve()
    conv = json.loads((session_dir / 'conversation.json').read_text())
    written = write_if_changed(session_dir / RENDERED, render_session(conv))
    write_if_changed(session_dir / FACTS, json.dumps(facts(conv), ensure_ascii=False, indent=1) + '\n')
    print(f"  {RENDERED}: {'rendered anew' if written else 'current'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
