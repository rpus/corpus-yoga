# machine

Two facts about machines, and deliberately no more.

| file | what |
| --- | --- |
| `machines.csv` | the **registry**: every declared machine. Committed. |
| `self.txt` | the **binding**: which one this is. One line, gitignored — a machine names itself, and that name is never shared, never transported. |

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
    # 2. then, on that machine, from this directory:
    echo <its-declared-name> > self.txt

`./yoga prerequisites` prints that command with the path filled in — it builds the
path by arithmetic, because the joined literal must not appear in committed text:
the file rightly does not exist on a fresh clone, so naming it whole would strand
xref and make the committed counts depend on which machine wrote them.

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
