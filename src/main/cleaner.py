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

The lines keep their tenses - `will remove:` over the entries, each keyed with its facts
beneath, `{}` where there is none; `did remove: it` or `did NOT remove: <why>` beneath each after
its act, so a log read after a crash shows the intention and, entry by entry, whether it
was carried out. Then next:, the acts the room can take after this one, corpus-yoga status
last (#801), and the verdict is the last line - DONE only when every entry went, NOT DONE
naming each that was NOT removed.
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


def clean(noun: str, entries: list[Entry], plural: dict[str, str], following: Callable[[], object]) -> int:
    """One loop over the one list: each entry said, then its act; following gives the next:
    block after the acts. Returns 1 while anything named was NOT removed."""
    did = {kind: 0 for kind in plural}
    left: list[str] = []
    width = facts.terminal_width()
    print(facts.opening('will remove') if entries else facts.lines({'will remove': {}})[0])
    for entry in entries:
        for line in facts.lines(facts.plain({entry.key: entry.facts}), 1, width=width):
            print(line)
        why = entry.act()
        if why is None:
            did[entry.kind] += 1
        else:
            left.append(f'{entry.kind}: {entry.key} - {why}')
        for line in facts.lines({'did remove': 'it'} if why is None else {'did NOT remove': why}, 2, width=width):
            print(line)
    counts = ', '.join(count(did[kind], kind, plural) for kind in plural if did[kind]) or 'nothing'
    if left:
        facts.report(None, following(), f'{noun} clean: NOT DONE - did remove {counts}; did NOT remove ' + '; '.join(left))
    else:
        facts.report(None, following(), f'{noun} clean: DONE - did remove {counts}')
    return 1 if left else 0
