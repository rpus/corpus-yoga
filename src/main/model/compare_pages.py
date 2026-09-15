#!/usr/bin/env python
"""
compare_pages.py - what changes between two renders of the corpus page, in the
page's own terms (#652): the title, and for each inlined data table the rows
added, removed and changed, compared by the table's identity column rather
than its position. The page keys its rows by ordinal (the `chat` column is a
position, and one inserted conversation renumbers every row after it), so a
line diff of two renders misstates the size of a change; the identity the
page also carries reads it true.

    compare_pages.py <old index.html> <new index.html>

One line per table on stdout; exit 0 whether or not anything differs. The
site publish dry run prints this for index.html where the clone's copy and
the publish tree's differ.
"""
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/model/compare_pages.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'

BLOCK = re.compile(r'<script id="(data-[a-z-]+)" type="application/json">\s*(.*?)\s*</script>', re.S)
TITLE = re.compile(r'<title>(.*?)</title>', re.S)
# the identity of a row, per table: a column name, or 'chat' for tables keyed by the
# conversation's ordinal, which resolves to the uuid through data-chats
IDENTITY = {
    'data-chats': ('uuid',),
    'data-spans': ('chat', 'from'),
    'data-chat-categories': ('chat',),
    'data-files': ('chat', 'file'),
    'data-categories': ('category',),
    'data-semantic-concepts': ('word',),
}
SHOWN = 4   # rows named per kind of change before ", ..."


def tables(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding='utf-8')
    title = TITLE.search(text)
    return (title.group(1) if title else ''), {m.group(1): json.loads(m.group(2)) for m in BLOCK.finditer(text)}


def keyed(name: str, table: dict, uuid_of: dict) -> dict:
    """{identity: {column: value}} for one table; a row keyed by chat carries the
    conversation's uuid in its identity, so renumbering changes nothing."""
    columns = table['columns']
    out = {}
    for row in table['rows']:
        record = dict(zip(columns, row))
        key = tuple(uuid_of.get(record[c], f'chat {record[c]}') if c == 'chat' else record[c]
                    for c in IDENTITY[name])
        out[key] = record
    return out


def label(name: str, key: tuple, record: dict) -> str:
    if name == 'data-chats':
        return f'{record["uuid"][:8]} "{record["name"]}"'
    if name == 'data-chat-categories':
        return f'{key[0][:8]} {record["category"]}'
    if name in ('data-files', 'data-spans'):
        return f'{key[0][:8]} {key[1]}'
    return ' '.join(str(k) for k in key)


def changed_columns(old: dict, new: dict, name: str) -> list[str]:
    skip = {'chat'}   # the ordinal is a position, never a change
    return [c for c in new if c not in skip and old.get(c) != new.get(c)]


def compare_table(name: str, old: dict, new: dict, uuid_old: dict, uuid_new: dict) -> str:
    a, b = keyed(name, old, uuid_old), keyed(name, new, uuid_new)
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    changed = [k for k in b if k in a and changed_columns(a[k], b[k], name)]
    if not (added or removed or changed):
        return f'{name}: identical ({len(b)} rows)'
    parts = []
    if added:
        parts.append(f'{len(added)} added: ' + ', '.join(label(name, k, b[k]) for k in added[:SHOWN])
                     + (', ...' if len(added) > SHOWN else ''))
    if removed:
        parts.append(f'{len(removed)} removed: ' + ', '.join(label(name, k, a[k]) for k in removed[:SHOWN])
                     + (', ...' if len(removed) > SHOWN else ''))
    if changed:
        shown = []
        for k in changed[:SHOWN]:
            cols = changed_columns(a[k], b[k], name)
            shown.append(label(name, k, b[k]) + ' (' + ', '.join(f'{c} {a[k][c]} to {b[k][c]}' for c in cols) + ')')
        parts.append(f'{len(changed)} changed: ' + ', '.join(shown) + (', ...' if len(changed) > SHOWN else ''))
    return f'{name}: ' + '; '.join(parts)


def size(table: dict) -> str:
    """A table's extent in its own terms: rows, or for the words table words per side."""
    if 'rows' in table:
        return f'{len(table["rows"])} rows'
    return ', '.join(f'{side} {len(t.get("rows", []))} words' for side, t in table.items())


def compare_words(old: dict, new: dict) -> str:
    """data-literal-words: one table per side (human, assistant, both), keyed by word."""
    parts = []
    for side in new:
        a = dict(old.get(side, {}).get('rows', [])) if side in old else {}
        b = dict(new[side]['rows'])
        added = [w for w in b if w not in a]
        removed = [w for w in a if w not in b]
        moved = [w for w in b if w in a and a[w] != b[w]]
        if added or removed or moved:
            parts.append(f'{side} {len(added)} entered, {len(removed)} left, {len(moved)} counts moved'
                         + (' (entered: ' + ', '.join(added[:SHOWN]) + (', ...' if len(added) > SHOWN else '') + ')' if added else ''))
    return 'data-literal-words: ' + ('; '.join(parts) if parts else 'identical')


def uuid_by_chat(page: dict) -> dict:
    """{chat ordinal: uuid} from data-chats, by the columns the table declares."""
    chats = page.get('data-chats')
    if not chats:
        return {}
    chat, uuid = chats['columns'].index('chat'), chats['columns'].index('uuid')
    return {row[chat]: row[uuid] for row in chats['rows']}


def compare(old_path: Path, new_path: Path) -> list[str]:
    old_title, old = tables(old_path)
    new_title, new = tables(new_path)
    lines = []
    if old_title != new_title:
        lines.append(f'title: "{old_title}" to "{new_title}"')
    else:
        lines.append(f'title: unchanged - "{new_title}"')
    uuid_old, uuid_new = uuid_by_chat(old), uuid_by_chat(new)
    for name in sorted(set(old) | set(new)):
        if name not in new:
            lines.append(f'{name}: removed from the page'); continue
        if name not in old:
            lines.append(f'{name}: new on the page ({size(new[name])})'); continue
        if name == 'data-literal-words':
            lines.append(compare_words(old[name], new[name]))
        elif name in IDENTITY:
            lines.append(compare_table(name, old[name], new[name], uuid_old, uuid_new))
        else:
            lines.append(f'{name}: {"identical" if old[name] == new[name] else "differs"} (no identity column declared)')
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print(f'usage: {SELF} <old index.html> <new index.html> - what changes between two renders '
              'of the corpus page, in the page\'s own terms', file=sys.stderr)
        return 2
    for line in compare(Path(sys.argv[1]), Path(sys.argv[2])):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
