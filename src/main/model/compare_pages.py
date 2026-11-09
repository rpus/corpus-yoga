#!/usr/bin/env python
"""
compare_pages.py - what changes between two renders of the corpus page, in the
page's own terms (issues/652): the title, and for each inlined data table the rows
added, removed and changed, compared by the table's identity column rather
than its position. The page keys its rows by ordinal (the `chat` column is a
position, and one inserted conversation renumbers every row after it), so a
line diff of two renders misstates the size of a change; the identity the
page also carries reads it true.

    compare_pages.py <old index.html> <new index.html>

One fact per line on stdout - its keys, then its value, tab-separated - and only what
changes; exit 0 whether or not anything differs. The site's status says these beneath
index.html where the publish tree's copy and rpus.co's differ.
"""
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/model/compare_pages.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main'))
import facts  # noqa: E402 - the one face a sentence is said through (issues/909)

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
# the columns that measure a row's content, per table (issues/1028): a change in them is the one
# to hold against expectation, so each such row is listed with them; a change elsewhere alone -
# a format's, uniform - is counted
MEASURES = {
    'data-chats': ('human', 'assistant'),
}
SHOWN = 4   # rows named per kind of change before ", ..."
Fact = tuple[str, ...]   # the keys a fact stands under, then its value


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
    """The columns whose values differ between the two rows - a column one row lacks among
    them, since a page that declares more than the other did has changed in that column."""
    skip = {'chat'}   # the ordinal is a position, never a change
    return [c for c in dict.fromkeys([*old, *new]) if c not in skip and old.get(c) != new.get(c)]


def value(record: dict, column: str) -> str:
    """A row's value in a column, or the word for its absence."""
    return str(record[column]) if column in record else facts.phrase('absent')


def named(name: str, keys: list, rows: dict) -> str:
    """The rows by their labels, the first SHOWN of them, then how many more."""
    return ', '.join(label(name, k, rows[k]) for k in keys[:SHOWN]) + (', ...' if len(keys) > SHOWN else '')


def compare_table(name: str, old: dict, new: dict, uuid_old: dict, uuid_new: dict) -> list[Fact]:
    """What changes in one table, by row identity, each count of its whole (issues/1028): the rows
    added and removed; the rows whose content measures changed, each listed with them; and
    the rows changed elsewhere alone, counted under the columns they changed in. Nothing
    where nothing changes."""
    a, b = keyed(name, old, uuid_old), keyed(name, new, uuid_new)
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    changed = {k: changed_columns(a[k], b[k], name) for k in b if k in a}
    changed = {k: cols for k, cols in changed.items() if cols}
    measures = MEASURES.get(name, ())
    out: list[Fact] = []
    if added:
        out.append((name, facts.phrase('added ({n} of {total})', n=len(added), total=len(b)), named(name, added, b)))
    if removed:
        out.append((name, facts.phrase('removed ({n} of {total})', n=len(removed), total=len(a)), named(name, removed, a)))
    measured = [k for k, cols in changed.items() if any(c in measures for c in cols)]
    if measured:
        part = facts.phrase('{measures} changed ({n} of {total})', measures=' or '.join(measures), n=len(measured), total=len(b))
        for k in measured:
            out.append((name, part, label(name, k, b[k]), ', '.join(
                facts.phrase('{column} {old} to {new}', column=c, old=value(a[k], c), new=value(b[k], c)) for c in measures if c in changed[k])))
    rest = [k for k in changed if k not in measured]
    if rest and measures:
        columns = ', '.join(dict.fromkeys(c for k in rest for c in changed[k]))
        out.append((name, facts.phrase('changed in {columns} alone', columns=columns), facts.phrase('{n} of {total}', n=len(rest), total=len(b))))
    elif rest:
        out.append((name, facts.phrase('changed ({n} of {total})', n=len(rest), total=len(b)), ', '.join(
            label(name, k, b[k]) + ' (' + ', '.join(facts.phrase('{column} {old} to {new}', column=c, old=value(a[k], c), new=value(b[k], c))
                                                    for c in changed[k]) + ')' for k in rest[:SHOWN]) + (', ...' if len(rest) > SHOWN else '')))
    return out


def size(table: dict) -> str:
    """A table's extent in its own terms: rows, or for the words table words per side."""
    if 'rows' in table:
        return facts.phrase('{n} rows', n=len(table['rows']))
    return ', '.join(facts.phrase('{side} {n} words', side=side, n=len(t.get('rows', []))) for side, t in table.items())


def compare_words(old: dict, new: dict) -> list[Fact]:
    """data-literal-words: one table per side (human, assistant, both), keyed by word; nothing
    where nothing changes."""
    parts = []
    for side in new:
        a = dict(old.get(side, {}).get('rows', [])) if side in old else {}
        b = dict(new[side]['rows'])
        added = [w for w in b if w not in a]
        removed = [w for w in a if w not in b]
        moved = [w for w in b if w in a and a[w] != b[w]]
        if added or removed or moved:
            parts.append(facts.phrase('{side} {added} entered, {removed} left, {moved} counts moved', side=side, added=len(added), removed=len(removed), moved=len(moved))
                         + (' (' + facts.phrase('entered {words}', words=', '.join(added[:SHOWN]) + (', ...' if len(added) > SHOWN else '')) + ')' if added else ''))
    return [('data-literal-words', '; '.join(parts))] if parts else []


def uuid_by_chat(page: dict) -> dict:
    """{chat ordinal: uuid} from data-chats, by the columns the table declares."""
    chats = page.get('data-chats')
    if not chats:
        return {}
    chat, uuid = chats['columns'].index('chat'), chats['columns'].index('uuid')
    return {row[chat]: row[uuid] for row in chats['rows']}


def compare(old_path: Path, new_path: Path) -> list[Fact]:
    """Every fact of what changes between the two renders, and nothing that does not."""
    old_title, old = tables(old_path)
    new_title, new = tables(new_path)
    out: list[Fact] = []
    if old_title != new_title:
        out.append(('title', facts.phrase('"{old}" to "{new}"', old=old_title, new=new_title)))
    uuid_old, uuid_new = uuid_by_chat(old), uuid_by_chat(new)
    for name in sorted(set(old) | set(new)):
        if name not in new:
            out.append((name, facts.phrase('removed from the page')))
        elif name not in old:
            out.append((name, facts.phrase('new on the page ({size})', size=size(new[name]))))
        elif name == 'data-literal-words':
            out += compare_words(old[name], new[name])
        elif name in IDENTITY:
            out += compare_table(name, old[name], new[name], uuid_old, uuid_new)
        elif old[name] != new[name]:
            out.append((name, facts.phrase('differs (no identity column declared)')))
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(f'usage: {SELF} <old index.html> <new index.html> - ' + facts.phrase("what changes between two renders of the corpus page, in the page's own terms"), file=sys.stderr)
        return 2
    for fact in compare(Path(sys.argv[1]), Path(sys.argv[2])):
        print('\t'.join(' '.join(part.split()) for part in fact))   # a part is one line and no tab
    return 0


if __name__ == '__main__':
    sys.exit(main())
