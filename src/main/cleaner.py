"""
cleaner.py - the one loop every clean verb runs (#837): corpus-yoga stage clean and
corpus-yoga store clean hand it the entries they alone know, and it says and takes them
one way.

An entry is what a noun's clean acts on: its kind (a word the noun's plural table knows),
its key (the address or path it is said under), its facts (said beneath the key), and the
act that removes it, returning None when it is gone and otherwise why it is not; `under`
is the selection the entry is counted under by a next: block, where one applies. A
cleaner takes no flag (#844): what it would remove is what the noun's status names, so
there is no dry run, and the act is one act.

`will remove:` over the entries, each keyed with its facts beneath, `{}` where there is
none; `could not remove: <why>` beneath an entry whose act left it. The noun's status is
relayed beneath the acts, the certified state after them, and the verdict is the last
line - DONE with the counts when every entry went, NOT DONE naming each the act could
not remove. One verb, remove, in one form throughout.
"""
from dataclasses import dataclass
from typing import Callable

import facts


@dataclass(frozen=True)
class Entry:
    kind: str
    key: str
    facts: dict
    act: Callable[[], str | None]
    under: str = ''


def count(n: int, kind: str, plural: dict[str, str]) -> str:
    return f'{n} {kind if n == 1 else plural[kind]}'


def clean(noun: str, entries: list[Entry], plural: dict[str, str], status: Callable[[], object]) -> int:
    """One loop over the one list: each entry said, then its act. Returns 1 while the act
    could not remove anything named."""
    did = {kind: 0 for kind in plural}
    left: list[str] = []
    print('will remove:' + ('' if entries else ' {}'))
    for entry in entries:
        for line in facts.lines(facts.plain({entry.key: entry.facts}), 1, width=facts.terminal_width()):
            print(line)
        why = entry.act()
        if why is None:
            did[entry.kind] += 1
        else:
            print(f'    could not remove: {why}')
            left.append(f'{entry.kind}: {entry.key} - {why}')
    counts = ', '.join(count(did[kind], kind, plural) for kind in plural if did[kind]) or 'nothing'
    print()
    status()
    print()
    if left:
        print(f'{noun} clean: NOT DONE - {counts}; could not remove ' + '; '.join(left))
    else:
        print(f'{noun} clean: DONE - {counts}')
    return 1 if left else 0
