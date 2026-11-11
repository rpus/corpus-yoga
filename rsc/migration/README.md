# rsc/migration - the moves a rename owes the machine-local roots

A commit renames a committed file and git carries the rename. A commit that renames
what lives under data/input, data/output, tmp/cache or ext/mnt renames nothing there:
those roots are laid out per room and no commit touches them - data/input the shared
tier, which iCloud carries, so that one room's move reaches the others and their run of
the same script finds nothing left to move. The script here named for the causing
issue carries that move, as the steps rsc/migration/step.sh declares.

`corpus-yoga migration` says what each script would do, and its `now:` names the
command that does it.

rsc/naming holds the grammars of names that arrive from outside the repository, which
code parses; a rename the repository caused is a script here, never a row there.
