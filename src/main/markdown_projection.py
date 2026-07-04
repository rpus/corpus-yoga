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


# A root message's parent_message_uuid is the zero-uuid sentinel (see the zero v4 UUID
# convention in the conversations schema); None covers formats omitting the field.
NO_PARENT = {None, '00000000-0000-4000-8000-000000000000'}


def tree_problems(messages):
    """Reasons this conversation's tree cannot be walked faithfully; [] if healthy.
    The projection renders the active path, which only exists if there is exactly one
    root and every other parent link resolves. The pre-tree export format (early 2026)
    lacks parent_message_uuid entirely — every message looks like a root — and until
    this check it silently projected to one-turn garbage that still validated."""
    if len(messages) <= 1:
        return []
    by_uuid = {m['uuid'] for m in messages}
    roots = sum(1 for m in messages if m.get('parent_message_uuid') in NO_PARENT)
    dangling = sum(1 for m in messages
                   if m.get('parent_message_uuid') not in NO_PARENT
                   and m.get('parent_message_uuid') not in by_uuid)
    problems = []
    if roots != 1:
        problems.append(f'{roots} root message(s), expected exactly 1')
    if dangling:
        problems.append(f'{dangling} dangling parent link(s)')
    return problems


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


def is_empty(conv):
    """A content-free conversation stub (an abandoned chat): no message carries any
    content blocks, text, or attached files. A predicate FUNCTION, deliberately not a
    schema: emptiness is a cross-source semantic that would need re-stating per source
    format (the schema corpus is flat — versioned standalone files with no cross-file
    subtyping), whereas both source shapes share the chat_messages sub-shape read here.
    A zero-message conversation is vacuously empty."""
    return all(
        not m.get('content')
        and not (m.get('text') or '').strip()
        and not m.get('attachments')
        and not m.get('files')
        for m in conv.get('chat_messages', []))


def ordered(convs):
    """The single source of truth for how a conversation corpus is ordered and named — shared by
    the atomised json/ pieces, the rendered markdown/, the presentation timeline, and the inference
    chat list, so a conversation is "<ordinal>-<slug>" (and conversation N) everywhere.

    Sort ascending by created_at; assign a 1-based ordinal zero-padded to the corpus width (so
    lexicographic filename order == conversation order); name each "<ordinal>-<slug>". The ordinal
    is itself unique, so no uuid disambiguation is needed. Returns [(ordinal:int, name:str, conv)].

    Empty stubs (is_empty) are excluded from the numbering — a stub present in one corpus but not
    another (e.g. deleted live after an export) would dislocate the cross-corpus ordinal
    correlation — but nothing is skipped: they are returned last as (None, "empty-<uuid8>", conv),
    the name announcing what they are wherever they land."""
    live = sorted((c for c in convs if not is_empty(c)),
                  key=lambda c: (c['created_at'], c['uuid']))  # uuid breaks created_at ties -> total, input-order-independent
    empties = sorted((c for c in convs if is_empty(c)),
                     key=lambda c: (c['created_at'], c['uuid']))
    width = len(str(len(live)))
    return ([(i, f"{i:0{width}d}-{slug(c['name'])}", c) for i, c in enumerate(live, 1)]
            + [(None, f"empty-{c['uuid'][:8]}", c) for c in empties])


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
