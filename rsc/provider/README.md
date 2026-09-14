# provider

One fact about providers: which ones the repository knows, as data.

| where | what |
| --- | --- |
| `providers.csv` (here) | the **registry**: every declared AI provider, one row each - the environment variable its sessions carry, its live session store, and the bot co-author pattern its harness writes. The store's mount is `ext/mnt/agent/<provider>`, derived from the row (#636). Committed - every clone carries the same one. |

A row states only what was observed, with the room and the date in its note; a
column stays empty where nothing was observed, and an empty column means "not
attested" to every reader, never a guess.

Every reader of a provider fact reads this file and nothing else: the commit
hook (`rsc/test/prepare-commit-msg-hook.sh`) attests a session only for a
declared provider whose declared variable the environment carries; the machine
report (`corpus-yoga prerequisites`) and the mount verb (`corpus-yoga agent mount`)
iterate the rows; the browser
capture keys its mechanisms by declared names; `src/main/provider.py` is the
library every reader shares: the python readers import it, and the shell readers
take its rows rendered one per line, so the csv grammar is read in one place and a
field may hold a comma or a quote. The dev gate holds that every provider named
by a directory or a data path under `src/` is a row here.

The sibling registry is `rsc/machine/machines.csv`: a machine is an identity, and
so is a provider; the Signature a commit carries is `<machine>/<provider>/<session>`.
