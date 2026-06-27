#!/usr/bin/env python
"""
project_markdown.py — Project conversations down to the lean markdownConversation shape,
validate, and render flat markdown files. Two sources, same target/renderer:

  browser-capture  apiConversation.json   --project-->  {title, url, messages:[{role,content}]}  --render-->  <title>.md
  bulk-export      conversations.json[*]   --project_bulk-->                "                              (validated against
                                                                            rsc/schema/browser-captures/markdownConversation/v1.json)

For browser captures this replaces the brittle DOM/clipboard scrape (the markdown becomes a
pure function of the reliable API JSON). For the bulk export it also ATOMISES the single
conversations.json array into one markdown file per conversation.

Browser captures fetch the full tree (?tree=true), so project() walks the linear ACTIVE
PATH (current_leaf_message_uuid back to root), excluding edited/regenerated branches. Bulk
exports are already linear, so project_bulk() takes chat_messages as-is. The per-message
projection (shared) in jq is:
  {role: .sender,
   content: ([.content[] | select(.type == "text") | (.text | gsub("^\\s+|\\s+$"; ""))]
             | map(select(. != "")) | join("\n\n"))}

Usage:
  src/run_python_script.sh src/main/browser-captures/project_markdown.py \
    --browser-captures ext/browser-captures/claude --out gen/browser-captures/markdown
  src/run_python_script.sh src/main/browser-captures/project_markdown.py \
    --bulk-export ext/chat-exports/<batch>/conversations.json --out gen/chat-exports/markdown
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO   = Path(__file__).resolve().parents[3]
SCHEMA = REPO / 'rsc' / 'schema' / 'browser-captures' / 'markdownConversation' / 'v1.json'


def turn_text(msg):
    """Rendered text of one turn: text-type blocks, each trimmed (the API prepends a
    leading space to most assistant blocks; the old scrape trimmed it too), joined."""
    blocks = (b['text'].strip() for b in msg['content'] if b.get('type') == 'text')
    return '\n\n'.join(b for b in blocks if b)


def active_path(api):
    """The linear conversation actually shown: walk current_leaf_message_uuid back to root
    via parent_message_uuid. The capture fetches the full tree (?tree=true), so chat_messages
    also contains edited/regenerated branches that the markdown must NOT include."""
    by_uuid = {m['uuid']: m for m in api['chat_messages']}
    chain, cur, seen = [], api.get('current_leaf_message_uuid'), set()
    while cur in by_uuid and cur not in seen:
        seen.add(cur)
        chain.append(by_uuid[cur])
        cur = by_uuid[cur].get('parent_message_uuid')
    return list(reversed(chain))


def _lean(name, uuid, messages):
    """Build the lean markdownConversation dict (metadata stripped) from a message list."""
    return {
        'title': name,
        'url': f"https://claude.ai/chat/{uuid}",
        'messages': [{'role': m['sender'], 'content': turn_text(m)} for m in messages],
    }


def project(api):
    """Browser-capture apiConversation -> lean dict. Uses the active leaf path, since the
    captured tree (?tree=true) also holds edited/regenerated branches."""
    return _lean(api['name'], api['uuid'], active_path(api))


def project_bulk(conv):
    """Bulk-export Conversation -> lean dict. Already linear (no branches, no leaf pointer),
    so chat_messages is the conversation in order -- this also atomises the bulk array."""
    return _lean(conv['name'], conv['uuid'], conv['chat_messages'])


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


def write_markdown(convs, out_dir):
    """Validate each lean conv against markdownConversation and render to <title>.md in
    out_dir, disambiguating same-named conversations by uuid. Returns (n_ok, n_bad)."""
    import jsonschema
    validator = jsonschema.Draft4Validator(json.loads(SCHEMA.read_text()))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_ok = n_bad = 0
    seen = set()
    for conv in convs:
        errors = sorted(validator.iter_errors(conv), key=lambda e: list(e.path))
        if errors:
            n_bad += 1
            print(f"  INVALID {conv.get('title', '?')}: {errors[0].message}", file=sys.stderr)
            continue
        uuid = conv['url'].rsplit('/', 1)[-1]
        name = slug(conv['title'])
        if name in seen:  # same-named conversations -> disambiguate by uuid
            name = f"{name}-{uuid[:8]}"
        seen.add(name)
        (out / f"{name}.md").write_text(render(conv))
        n_ok += 1
    return n_ok, n_bad


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--browser-captures', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--bulk-export', help='a bulk-export conversations.json (array of conversations)')
    ap.add_argument('--out', required=True, help='flat output dir for <title>.md files')
    args = ap.parse_args()

    if args.browser_captures:
        dirs = sorted(p for p in Path(args.browser_captures).iterdir() if p.is_dir())
        convs = [project(api) for d in dirs if (api := find_api_json(d)) is not None]
    else:
        convs = [project_bulk(c) for c in json.loads(Path(args.bulk_export).read_text())]

    n_ok, n_bad = write_markdown(convs, args.out)
    print(f"projected {n_ok} conversations to {args.out} ({n_bad} invalid)")


if __name__ == '__main__':
    main()
