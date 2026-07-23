#!/usr/bin/env python
"""
memory_to_json.py — JSONify one project's memory/ directory into memory.json,
the projectMemory datum (rsc/schema/code-agents/projectMemory).

A project's memory/ (under data/input/claude/code/machine-transport/<machine>/<project>/, the repo-owned
store transport populates) is an index (MEMORY.md, one '- [Title](file.md) — hook'
line per fact) plus one markdown file per fact: YAML frontmatter (name,
description, metadata) and a body that may [[link]] other facts by name. This
tool parses that structure verbatim — frontmatter values as the strings they
are, the body whole, links extracted — so the schema can hold the memory
contract to account: every fact carries its identity and classification.

Index lines that are not entries (headings, the merge marker comments
agent.py's receive writes) are carried verbatim under 'unparsed' — data,
not discarded.

The frontmatter parser is deliberately minimal (top-level 'key: value' pairs,
one 2-space-indented nested mapping level, optional quote wrapping) — exactly
the shape the memory format prescribes, not general YAML; anything beyond it
should fail validation loudly rather than parse silently.

Usage:
    src/run_python_script.sh src/main/code-agents/memory_to_json.py \
        <memory-dir> <output.json>
"""
import json
import re
import sys
from pathlib import Path

from jsonl_to_json import _write_if_changed

ENTRY = re.compile(r'^- \[(?P<title>.*?)\]\((?P<file>[^)]+)\)(?:\s+—\s+(?P<hook>.*))?$')
LINK = re.compile(r'\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]')


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """(mapping, body) from a frontmattered markdown file. Nested mappings one
    level deep (the 'metadata:' block); scalar values kept as strings."""
    m = re.match(r'---\n(.*?)\n---\n?(.*)\Z', text, re.S)
    if not m:
        return {}, text
    mapping, current = {}, None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith('  ') and current is not None:
            key, _, value = line.strip().partition(':')
            mapping[current][key.strip()] = _unquote(value)
        else:
            key, _, value = line.partition(':')
            if value.strip() == '':
                current = key.strip()
                mapping[current] = {}
            else:
                current = None
                mapping[key.strip()] = _unquote(value)
    return mapping, m.group(2)


def parse_fact(path):
    front, body = parse_frontmatter(path.read_text())
    body = body.strip()
    return {'file': path.name,
            'name': front.get('name', ''),
            'description': front.get('description', ''),
            'metadata': front.get('metadata') if isinstance(front.get('metadata'), dict) else {},
            'body': body,
            'links': sorted(set(LINK.findall(body)))}


def parse_index(path):
    entries, unparsed = [], []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        m = ENTRY.match(line.strip())
        if m:
            entries.append({'title': m['title'], 'file': m['file'],
                            'hook': m['hook'] or ''})
        else:
            unparsed.append(line)
    return {'file': path.name, 'entries': entries, 'unparsed': unparsed}


def memory_to_json(memory_dir, project):
    facts = [parse_fact(f) for f in sorted(memory_dir.glob('*.md'))
             if f.name != 'MEMORY.md']
    return {'project': project,
            'facts': facts,
            'index': parse_index(memory_dir / 'MEMORY.md')}


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: memory_to_json.py <memory-dir> <output.json>', file=sys.stderr)
        return 1
    memory_dir = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2])
    doc = memory_to_json(memory_dir, memory_dir.parent.name)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_if_changed(str(out), lambda dst: json.dump(doc, dst, indent=1, ensure_ascii=False))
    print(f'  memory.json: {len(doc["facts"])} fact(s), '
          f'{len(doc["index"]["entries"])} index entr(y/ies)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
