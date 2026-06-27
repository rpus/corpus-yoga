#!/usr/bin/env python
"""
project_markdown.py — Project browser-captured apiConversation JSON down to the lean
markdownConversation shape, validate it, and render flat markdown files.

This replaces the brittle DOM/clipboard scrape: the markdown becomes a pure function of
the reliable API JSON we already fetch.

  apiConversation.json  --project-->  {title, url, messages:[{role, content}]}  --render-->  <title>.md
                                      (validated against rsc/schema/browser-captures/markdownConversation/v1.json)

Messages are the linear ACTIVE PATH (current_leaf_message_uuid back to root), not all of
chat_messages -- the capture fetches the full tree, including edited/regenerated branches
the markdown must omit. That walk is done in Python; the per-message projection in jq is:
  {role: .sender,
   content: ([.content[] | select(.type == "text") | (.text | gsub("^\\s+|\\s+$"; ""))]
             | map(select(. != "")) | join("\n\n"))}

Usage:
  src/run_python_script.sh src/main/browser-captures/project_markdown.py \
    --browser-captures ext/browser-captures/claude --out gen/browser-captures/markdown
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


def project(api):
    """apiConversation dict -> lean markdownConversation dict (metadata stripped)."""
    return {
        'title': api['name'],
        'url': f"https://claude.ai/chat/{api['uuid']}",
        'messages': [
            {'role': m['sender'], 'content': turn_text(m)}
            for m in active_path(api)
        ],
    }


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True, help='dir of <uuid>/ capture folders')
    ap.add_argument('--out', required=True, help='flat output dir for <title>.md files')
    args = ap.parse_args()

    import jsonschema
    validator = jsonschema.Draft4Validator(json.loads(SCHEMA.read_text()))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    n_ok = n_bad = 0
    seen = set()
    for d in sorted(p for p in Path(args.browser_captures).iterdir() if p.is_dir()):
        api = find_api_json(d)
        if api is None:
            continue
        conv = project(api)
        errors = sorted(validator.iter_errors(conv), key=lambda e: list(e.path))
        if errors:
            n_bad += 1
            print(f"  INVALID {d.name}: {errors[0].message}", file=sys.stderr)
            continue
        name = slug(conv['title'])
        if name in seen:  # same-named conversations -> disambiguate by uuid
            name = f"{name}-{api['uuid'][:8]}"
        seen.add(name)
        (out / f"{name}.md").write_text(render(conv))
        n_ok += 1
    print(f"projected {n_ok} conversations to {args.out} ({n_bad} invalid)")


if __name__ == '__main__':
    main()
