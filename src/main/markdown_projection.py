#!/usr/bin/env python
"""
markdown_projection.py — Shared primitives for projecting a Conversation to the lean
markdownConversation shape and rendering it to markdown. Common code at the root of src/main/
(like schema_*.py, validate*.py); the per-pipeline CLIs import it via the sys.path idiom:

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # puts src/main/ on the path
    from markdown_projection import project, render, ...

Consumers: model/project_markdown.py (renders markdown), model/compare_sources.py and
browser-captures/compare_markdown.py (project+render to compare), chat-exports/atomise_bulk.py
(slug/assign_name to name the per-conversation pieces).

The per-message projection, in jq:
  {role: .sender,
   content: ([.content[] | select(.type == "text") | (.text | gsub("^\\s+|\\s+$"; ""))]
             | map(select(. != "")) | join("\n\n"))}
"""
import json
import re
from pathlib import Path

REPO      = Path(__file__).resolve().parents[2]
MD_SCHEMA = REPO / 'rsc' / 'schema' / 'browser-captures' / 'markdownConversation' / 'v1.json'


def turn_text(msg):
    """Rendered text of one turn: text-type blocks, each trimmed (the API prepends a
    leading space to most assistant blocks; the old scrape trimmed it too), joined."""
    blocks = (b['text'].strip() for b in msg['content'] if b.get('type') == 'text')
    return '\n\n'.join(b for b in blocks if b)


def _path_to_root(messages, leaf_uuid):
    """Linear path from a leaf back to root via parent_message_uuid (excludes other branches)."""
    by_uuid = {m['uuid']: m for m in messages}
    chain, cur, seen = [], leaf_uuid, set()
    while cur in by_uuid and cur not in seen:
        seen.add(cur)
        chain.append(by_uuid[cur])
        cur = by_uuid[cur].get('parent_message_uuid')
    return list(reversed(chain))


def _lean(name, uuid, messages):
    """Lean markdownConversation dict (metadata stripped) from a message list."""
    return {
        'title': name,
        'url': f"https://claude.ai/chat/{uuid}",
        'messages': [{'role': m['sender'], 'content': turn_text(m)} for m in messages],
    }


def project(conv):
    """Project one Conversation (browser apiConversation or bulk-export element) to the lean dict.
    Both shapes share name/uuid/chat_messages and differ only in the active leaf: a browser capture
    states it (current_leaf_message_uuid); the bulk export omits it, so the leaf is inferred as the
    latest-created message (editing and regenerating append recent-timestamped ones). compare_sources.py
    checks that inference reproduces the API's explicit active path."""
    msgs = conv['chat_messages']
    leaf = conv.get('current_leaf_message_uuid')
    if leaf is None:
        leaf = max(msgs, key=lambda m: m['created_at'])['uuid'] if msgs else None
    return _lean(conv['name'], conv['uuid'], _path_to_root(msgs, leaf))


def render(conv):
    """lean markdownConversation dict -> markdown string."""
    label = {'human': 'Human', 'assistant': 'Claude'}
    count = {'human': 0, 'assistant': 0}
    out = [f"# {conv['title']}", '', f"<{conv['url']}>", '']
    for m in conv['messages']:
        count[m['role']] += 1
        out += [f"## {label[m['role']]} ({count[m['role']]})", '', m['content'], '', '---', '']
    return '\n'.join(out).rstrip() + '\n'


def slug(title):
    return re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:100] or 'conversation'


def assign_name(title, uuid, seen):
    """Unique filename stem from the title, disambiguated by uuid on collision."""
    name = slug(title)
    if name in seen:
        name = f"{name}-{uuid[:8]}"
    seen.add(name)
    return name


def find_api_json(d):
    """The capture's apiConversation JSON (the one with chat_messages)."""
    for f in sorted(d.glob('*.json')):
        try:
            o = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict) and 'chat_messages' in o:
            return o
    return None


def md_validator():
    """A Draft4 validator for the markdownConversation schema."""
    import jsonschema
    return jsonschema.Draft4Validator(json.loads(MD_SCHEMA.read_text()))
