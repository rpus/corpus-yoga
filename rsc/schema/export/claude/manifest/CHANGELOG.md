# manifest schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v2

A manifest can list a fifth file, `frames`. Reading-room's bulk export of 2026-11-28
(`data-0fc4c1e0-…-2026-11-28-10-13-27`), captured by `corpus-yoga export capture` into the stage
with its manifest within it (issues/1204), is refused at v1 by the rehearsal of
2026-11-28T101753Z at `/data_files/3/category`, holding `frames`, where the category was a
closed enum over the four observed on 2026-08-24. The manifest, version "1.0" and created
2026-11-28T10:13:27Z, lists five files - `light_metadata`, `projects`, `memories`, `frames`,
`conversations`, each part 0, each batch_index its position - and the capture fetched all five,
`frames-000.zip` arriving as the `artifacts` directory, which
rsc/naming/export_archive_members.csv names. Validated on reading-room, 2026-11-28: v1 refuses
the manifest at that category alone; v2 refuses nothing in it. v2 widens one enum and narrows
nothing, so every manifest v1 admits, v2 admits.

### Replaces

v1

#### Restricted

None.

#### Relaxed

- `data_files[].category`: admits `frames`.

#### Refactored

- `data_files[].batch_index`, `data_files[].part`: their descriptions count the three manifests now observed, where they said both. No validation effect.

## v1

Initial schema, minted from the flow change of 2026-08-24 (issues/522): requesting a
bulk export still emails a link, but the link now downloads this manifest -
version "1.0", four data_files, each a one-use export_url - where the
pre-manifest flow delivered one archive. Minted from the two manifests
observed on reading-room, 2026-08-24 (created 12:30:34Z and 12:31:52Z, one
account, two export requests): they differ only in created_at and the one-use
URLs. Closed throughout, category a closed enum over the observed four - so
the flow's next drift fails loudly by name, as this vintage itself would have
under a schema for its predecessor.
