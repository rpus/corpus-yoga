# login_history schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v1

Initial schema, minted 2026-08-24 with the manifest-era intake (#522): the
component had shipped in every observed export but never had a family. One
shape across both vintages - an object of `login_events`, each event the
account uuid, instant, IP, parsed user agent, method, and coarse location;
`os_version`, `region` and `city` observed null; `method` observed only as
"google", the set left open. Validated against both held exports' files
(29 and 30 events) at mint.
