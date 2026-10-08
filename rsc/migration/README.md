# rsc/migration - the moves a rename owes the machine-local roots

A commit renames a committed file and git carries the rename. A commit that renames
what lives under data/output, tmp/cache or ext/mnt renames nothing there: those roots
are laid out per room and no commit touches them. The script here named for the
causing issue carries that move, as the move: `mv <from> <to>`, `rm <link>`, `rmdir
<directory>` and, for rebuildable derivations only, `rm -r <directory>` lines over the
steps of step.sh.

- bare, a script prints each step it would take and takes none; `--apply` takes them.
- a step whose from is absent prints nothing: a second run does nothing.
- a from and a to both present halt the script with the pair named; nothing here chooses.
- `corpus-yoga migration` runs every script bare and says each one's steps, none, or
  that it halted; `corpus-yoga migration sync --apply` takes the steps, and
  `corpus-yoga status` carries that status.

rsc/naming holds the grammars of names that arrive from outside the repository, which
code parses; a rename the repository caused is a script here, never a row there.
