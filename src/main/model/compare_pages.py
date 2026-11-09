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
import facts  # the one face a sentence is said through (issues/909)

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
# the columns that measure a row's content, per table (issues/1028): a change in them is the one
# to hold against expectation, so each such row is listed with them; a change elsewhere alone -
# a format's, uniform - is counted
MEASURES = {
    'data-chats': ('turns', ('human', 'assistant')),   # what the measures are called together, then the columns
}
# the columns a table's rows are grouped by, per table (issues/1028): what is added, removed or
# changed is said by group, of that group's whole - a format's change is one projection's, all of
# one channel or some of it, and a conversation is one of its channel's - and a group with
# nothing in it is not said
GROUPS = {
    'data-chats': ('provider', 'channel'),
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


def changed_columns(old: dict, new: dict, name: str, shared: set[str]) -> list[str]:
    """The columns both pages carry whose values differ between the two rows. A column one
    page lacks is the table's change, said once (issues/1028), never every row's."""
    skip = {'chat'}   # the ordinal is a position, never a change
    return [c for c in dict.fromkeys([*old, *new]) if c in shared and c not in skip and old.get(c) != new.get(c)]


def value(record: dict, column: str) -> str:
    """A row's value in a column, or the word for its absence."""
    return str(record[column]) if column in record else facts.phrase('absent')


def named(name: str, keys: list, rows: dict) -> str:
    """The rows by their labels, the first SHOWN of them, then how many more."""
    return ', '.join(label(name, k, rows[k]) for k in keys[:SHOWN]) + (', ...' if len(keys) > SHOWN else '')


def change(old: dict, new: dict, column: str) -> str:
    """What one column of a row became: its new value, with the signed difference where both
    are numbers and with what it was otherwise - one fact, never a phrase joining the two."""
    was, now = old.get(column), new.get(column)
    if isinstance(was, int) and isinstance(now, int) and not isinstance(was, bool) and not isinstance(now, bool):
        return facts.phrase('{value} ({difference})', value=now, difference=f'{now - was:+d}')
    return facts.phrase('{value} (was {old})', value=value(new, column), old=value(old, column))


def compare_table(name: str, old: dict, new: dict, uuid_old: dict, uuid_new: dict) -> list[Fact]:
    """What changes in one table, by row identity, each count of its whole (issues/1028): the rows
    added and removed; the rows whose content measures changed, each listed with them; and
    the rows changed elsewhere alone, counted under the columns they changed in - each by
    the table's groups where it declares them. Nothing where nothing changes."""
    a, b = keyed(name, old, uuid_old), keyed(name, new, uuid_new)
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    shared = set(old['columns']) & set(new['columns'])
    changed = {k: changed_columns(a[k], b[k], name, shared) for k in b if k in a}
    changed = {k: cols for k, cols in changed.items() if cols}
    called, measures = MEASURES.get(name, ('', ()))
    by = GROUPS.get(name, ())

    def group(record: dict) -> str:
        return '/'.join(value(record, c) for c in by)

    def grouped(keys: list, rows: dict) -> dict[str, list]:
        out: dict[str, list] = {}
        for k in keys:
            out.setdefault(group(rows[k]), []).append(k)
        return out

    def whole(rows: dict, key: str) -> int:
        return sum(1 for record in rows.values() if group(record) == key)

    out: list[Fact] = []
    for part, columns in ((facts.phrase('columns added'), [c for c in new['columns'] if c not in shared]),
                          (facts.phrase('columns removed'), [c for c in old['columns'] if c not in shared])):
        if columns:
            out.append((name, part, ', '.join(columns)))
    for part, keys, rows in ((facts.phrase('added'), added, b), (facts.phrase('removed'), removed, a)):
        if not keys:
            continue
        if not by:
            out.append((name, facts.phrase('{part} ({n} of {total})', part=part, n=len(keys), total=len(rows)), named(name, keys, rows)))
            continue
        for key, of_group in grouped(keys, rows).items():
            out.append((name, part, facts.phrase('{group} ({n} of {total})', group=key, n=len(of_group), total=whole(rows, key)), named(name, of_group, rows)))
    measured = [k for k, cols in changed.items() if any(c in measures for c in cols)]
    if measured:
        part = facts.phrase('{measures} changed', measures=called)
        for key, of_group in (grouped(measured, b) if by else {'': measured}).items():
            under = (facts.phrase('{group} ({n} of {total})', group=key, n=len(of_group), total=whole(b, key)),) if by else ()
            for k in of_group:
                for c in measures:
                    if c in changed[k]:
                        out.append((name, part, *under, label(name, k, b[k]), c, change(a[k], b[k], c)))
    rest = [k for k in changed if k not in measured]
    if rest and measures:
        part = facts.phrase('changed in {columns} alone', columns=', '.join(dict.fromkeys(c for k in rest for c in changed[k])))
        if not by:
            out.append((name, part, facts.phrase('{n} of {total}', n=len(rest), total=len(b))))
        for key, of_group in (grouped(rest, b) if by else {}).items():
            out.append((name, part, key, facts.phrase('{n} of {total}', n=len(of_group), total=whole(b, key))))
    elif rest:
        part = facts.phrase('{part} ({n} of {total})', part=facts.phrase('changed'), n=len(rest), total=len(b))
        for k in rest[:SHOWN]:
            for c in changed[k]:
                out.append((name, part, label(name, k, b[k]), c, change(a[k], b[k], c)))
        if len(rest) > SHOWN:
            out.append((name, part, facts.phrase('{n} more', n=len(rest) - SHOWN)))
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
