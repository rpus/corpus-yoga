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
MD_SCHEMA = REPO / 'rsc' / 'schema' / 'browser-captures' / 'markdownConversation' / 'v2.json'


def turn_text(msg):
    """Rendered text of one turn: text-type blocks, each trimmed (the API prepends a
    leading space to most assistant blocks; the old scrape trimmed it too), joined."""
    blocks = (b['text'].strip() for b in msg['content'] if b.get('type') == 'text')
    return '\n\n'.join(b for b in blocks if b)


# A root message's parent_message_uuid is the zero-uuid sentinel (see the zero v4 UUID
# convention in the conversations schema); None covers formats omitting the field.
NO_PARENT = {None, '00000000-0000-4000-8000-000000000000'}

# Turn-heading anchors are inline HTML, which markdownlint flags (MD033); this file-scoped
# pragma, rendered into every generated .md, tells any lint-aware editor they are intended.
MD033_PRAGMA = '<!-- markdownlint-disable MD033 -->'


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
    """Lean markdownConversation dict (metadata stripped) from a message list. Each turn
    keeps its message uuid — the turn's durable identity (identical across the browser-capture
    and bulk-export shapes), rendered as the heading anchor."""
    return {
        'title': name,
        'url': f"https://claude.ai/chat/{uuid}",
        'messages': [{'role': m['sender'], 'content': turn_text(m), 'uuid': m['uuid']}
                     for m in messages],
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
    """lean markdownConversation dict -> markdown string. Each turn heading carries an HTML
    anchor named by the message uuid, so <file>.md#<uuid> addresses the turn durably
    (ordinals renumber; uuids don't). Anchors ride the heading line, where turn_seq's
    `## <Role> [^\\n]*` split ignores them — comparisons are anchor-blind by construction."""
    label = {'human': 'Human', 'assistant': 'Claude'}
    count = {'human': 0, 'assistant': 0}
    # the pragma placates markdownlint (MD033 no-inline-html) about the heading anchors;
    # it sits in the preamble, before the first turn heading, so turn_seq never sees it
    out = [f"# {conv['title']}", '', MD033_PRAGMA, '', f"<{conv['url']}>", '']
    for m in conv['messages']:
        count[m['role']] += 1
        out += [f"## {label[m['role']]} ({count[m['role']]}) <a id=\"{m['uuid']}\"></a>",
                '', m['content'], '', '---', '']
    return '\n'.join(out).rstrip() + '\n'


def turn_seq(md):
    """Ordered [(role, normalized_body)] — role 'H' (Human) or 'A' (Claude/Gemini) — parsed
    from a rendered markdown string. The dual of render(): this file owns the markdown
    format in both directions, so format changes (e.g. the heading anchors, which the
    `[^\\n]*` split deliberately ignores) stay in lockstep. The trailing --- turn divider
    is not part of the turn's content: an empty turn must normalize to '' (the empty-turn
    exemption in compare_markdown.classify depends on it)."""
    parts = re.split(r'^## (Human|Claude|Gemini) [^\n]*\n', md, flags=re.M)
    seq = []
    for i in range(1, len(parts) - 1, 2):
        role = 'H' if parts[i] == 'Human' else 'A'
        body = re.sub(r'\s+', ' ', parts[i + 1]).strip()
        body = re.sub(r'\s*---$', '', body)
        seq.append((role, body))
    return seq


def conv_id(md):
    """The conversation id, from the <url> line render() (and the gemini scraper) emits
    (last path segment). Robust pairing key -- different sides slugify different titles,
    so filenames can diverge."""
    m = re.search(r'<(https?://[^>]+)>', md)
    if not m:
        return None
    return m.group(1).split('?')[0].split('#')[0].rstrip('/').rsplit('/', 1)[-1]


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


def load_convs(path) -> list:
    """The conversation objects for a batch, from EITHER the bulk conversations.json
    (a JSON array) or the atomised json/ dir (one object per file — the same elements,
    since atomisation just splits the array). ordered() consumes the result
    identically, so a consumer can read the normalized per-conversation CACHE
    (gen/<batch>/json/) instead of reaching back into the raw INPUT
    (ext/<batch>/conversations.json) — the source-agnostic per-conversation shape a
    non-claude source (gemini) can also produce."""
    p = Path(path)
    if p.is_dir():
        return [json.loads(f.read_text()) for f in sorted(p.glob('*.json'))]
    return json.loads(p.read_text())


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


def reconcile_dir(out_dir, files: dict) -> tuple:
    """Make out_dir hold EXACTLY {relative-name: text content}, touching only
    what changed. A file whose content already matches is left untouched — its
    mtime preserved — so re-running is silence on disk (L1) and a synced
    filesystem (iCloud) re-uploads only genuine changes; a differing or absent
    file is written; an existing file absent from `files` is removed (the orphan
    a rename would otherwise strand — the one thing the old wholesale rmtree got
    right). Reconciling rather than wiping also keeps the previous output intact
    to diff against: you cannot check parity against a directory you deleted
    first. Returns (written, unchanged, removed)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = unchanged = removed = 0
    for name, content in files.items():
        target = out_dir / name
        if target.exists() and target.read_text() == content:
            unchanged += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        written += 1
    keep = set(files)
    for f in out_dir.rglob('*'):
        if f.is_file() and f.name != '.DS_Store' and str(f.relative_to(out_dir)) not in keep:
            f.unlink()
            removed += 1
    return written, unchanged, removed
