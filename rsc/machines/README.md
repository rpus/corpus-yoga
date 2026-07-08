# Machine manifests

Docker-style declarations of what a machine (a *room*) should have — the desired
state as committed data, with observation strictly machine-local (L2 of
`rsc/CALCULUS.md`: these files are byte-identical on every clone because they
declare in role terms — requirement names and repo-relative paths, never
usernames, absolute paths, or observed values).

## The split, and the binding

- **Manifests (committed, here):** `_base.csv` applies to every room (the docker
  `FROM` layer); `<room>.csv` layers the room's own requirements on top.
- **Binding (machine-local, gitignored):** each machine names which room it is in
  a one-line `self.txt` beside these manifests — the one git-ignored file in
  the committed tree, because the room is the machine's own name for itself
  and must never be shared or transported. An unbound machine is told so, and how to bind
  (L8: absence is a signal).
- **Report (never committed):** `./yoga machine` verifies THIS machine against
  its room's manifest — ✓ present, – optional and absent, ✗ required and absent
  (exit 1). The pre-commit data tier repeats the required rows where a binding
  exists, advisory like all machine-local facts.

## Format

CSV columns `level,kind,arg,note`:

| column | values |
| --- | --- |
| `level` | `required` (✗ and exit 1 when absent) or `optional` (– when absent) |
| `kind` | `cmd` (on PATH) · `env` (variable set) · `path` (repo-relative, exists — dir, file, or symlink) · `grep` (arg is `<file> <pattern>`: file contains pattern; `~` expands) |
| `arg` | the probe's subject |
| `note` | how to satisfy it — printed beside a miss, never executed |

Rooms own their declarations: a room's data holdings are choices (the reading
room's chat-exports are disjoint BY CHOICE, so no manifest demands them), and a
new machine is a new `<room>.csv` plus a one-line binding.

## Commands

    ./yoga machine                  # verify this machine against its bound room
    ./yoga machine --room <name>    # verify against a named room (binding ignored)
