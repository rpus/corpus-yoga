# machine

Two facts about machines, and deliberately no more.

| where | what |
| --- | --- |
| `machines.csv` (here) | the **registry**: every declared machine. Committed — every clone carries the same one. |
| `machine-name.txt` (repo root) | the **binding**: which one this is. One line, gitignored — a machine names itself, and that name is never shared, never transported. |

They live apart because they are opposites: the registry is the list every clone
shares, the binding is the one thing no clone may share. So the binding sits at the
root among the other machine-local entries (`cache/`, `input/`, `logs/`, `output/`),
which is what it is — and this directory is left wholly committed.

`src/main/machine.py` reads both and is a library, not a command: `machines()` and
`bound_machine()`. Nothing here reports — `./yoga prerequisites` is the one machine
voice, and it says everything a report here would, in more detail.

## Why the registry exists

`bound_machine()` refuses a binding the registry does not declare. That refusal
guards exactly one write: `yoga agent capture` keys the shared transport store by
this name (`input/claude/code/machine-transport/<machine>/`), so a typo'd binding
would mint a phantom machine in a store BOTH machines see. The gate lives in the one
reader, so every consumer inherits it.

Declare first, then bind — never the other way round:

    # 1. add a row to machines.csv (committed, reviewed)
    # 2. then, on that machine, from the repo root:
    echo <its-declared-name> > machine-name.txt

`./yoga prerequisites` prints that command ready to run, and names the declared
machines to pick from.

## Why the binding is not in here

Until 2026-07-17 it was — `self.txt`, beside the registry, the one gitignored file
in the committed tree. That single exception cost more than it was worth. Its path
had to be assembled from pieces and never written whole, in this README and in every
script that read it, because a committed literal naming it was a reference to a file
that exists only on bound machines: cross-reference resolution asked the filesystem,
so the committed counts came out one way here and another way on a fresh clone. The
rule was easy to state and easy to forget, and it was forgotten — by the very commit
that rewrote this file. Rooted, the binding is named outright everywhere, because
its own `.gitignore` rule is what makes naming it safe. The exception is gone, and
with it the discipline that existed only to survive it.

## Why there is no manifest

There was one — `_base.csv` layered under `<machine>.csv`, docker-style — and it is
gone. Machines do not diverge: every `<machine>.csv` was empty from the day it was
made, because "this machine might not have X" is already expressed by
`PREREQUISITES` as *optional*, not by giving each machine its own list. A machine is
an **identity**, not a configuration variant. The requirements it declared were also
checked, better, by `./yoga prerequisites` — with versions and counts a manifest row
cannot carry — so the manifest was a second, poorer telling of facts already told.
The names stay as they are (`home-room`, `reading-room`): they are what each machine
calls itself, and they key real directories in the shared store.
