# provider

One fact about providers: which ones the repository knows, as data.

| where | what |
| --- | --- |
| `providers.csv` (here) | the **registry**: every declared AI provider, one row each - the environment variable its sessions carry, its live session store, the `ext/mnt/` mount name, and the bot co-author pattern its harness writes. Committed - every clone carries the same one. |

A row states only what was observed, with the room and the date in its note; a
column stays empty where nothing was observed, and an empty column means "not
attested" to every reader, never a guess.

The first five columns hold no comma and no quote: the commit hook and the mount
script split a row on commas in bash, the python readers parse it as csv, and
the dev gate holds that every row reads the same under both
(`provider.readers_agree`). The note, the last column, may hold either.

Every reader of a provider fact reads this file and nothing else: the commit
hook (`rsc/test/prepare-commit-msg-hook.sh`) attests a session only for a
declared provider whose declared variable the environment carries; the machine
report (`corpus-yoga prerequisites`) and the mount script
(`src/main/pipeline/code-agents/link_projects.sh`) iterate the rows; the browser
capture keys its mechanisms by declared names; `src/main/provider.py` is the
library the python readers share. The dev gate holds that every provider named
by a directory or a data path under `src/` is a row here.

The sibling registry is `rsc/machine/machines.csv`: a machine is an identity, and
so is a provider; the Signature a commit carries is `<machine>/<provider>/<session>`.
