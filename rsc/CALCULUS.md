# The corpus calculus

The operational, set-theoretic semantics of this repo's data — and, reflexively,
of the yogic code that tends it (see Reflexivity below) — **extracted from the
code that already works, not designed ahead of it**. Every rule below was converged
on independently by two or more implementations before it was written down here;
file references point at the implementations that discovered it. The companion
encoding (a generic protocol with the existing scripts as its instances) is a
planned refactor; this document deliberately precedes it, so that the calculus is
discovered from working code and then imposed back, never the reverse.

Laws are numbered (L1–L8) so that checks and reviews can cite them. Each is a
candidate property check for the pre-commit code tier: the document holds the
narrative, the code holds the shape, and the laws are the testable seam between.

This document is also an INTERFACE, not only a narrative: the bolded leads of
the operation and law bullets below are machine-read as the citable vocabulary
for the yoga CLI's command table (`calculus_terms()` in `src/main/cli/cli.py`;
table: `rsc/cli/`), and the pre-commit code tier rejects any
citation not defined here. Reformatting a bullet therefore shrinks the
vocabulary — loudly, never silently.

---

## Objects: corpora, classified on two axes

A **corpus** is a set of **units**, each of which atomises to a set of **atoms**
(its content identities). Two axes classify every corpus in the repo, and the
classification determines every operation's semantics.

### Axis 1 — identity: what names a unit durably

| identity scheme | used when | instances |
| --- | --- | --- |
| **uuid** | the unit persists while presentation shifts around it | conversations, messages, sessions, captures, projects, library dirs (`<ordinal>-<slug>-<uuid8>`, uuid8 suffix is the key) |
| **snapshot time** | units are versions of ONE mutable thing — ordination *is* identity | memory deposits (`data/output/memories/<ISO>.json`), batch names (export epoch) |
| **path / slug / ordinal** | presentation only — NEVER identity | filenames in `tmp/cache/`, ordinal prefixes, slug dressing |

The governing slogan (earned twice by duplicated library dirs): *the LLM speaks
ordinals, storage speaks uuid, presentation re-derives ordinals.* The one deliberate
exception proves the rule: memory snapshots have no uuid because they are not many
things — they are one thing at many times.

### Axis 2 — mutability: what a unit's history can do

| class | supersession | merge across machines | deletion licence | instances |
| --- | --- | --- | --- | --- |
| **append-only** | atom-subset: `A ⊑ B ⟺ atoms(A) ⊆ atoms(B)` | union, freshest-wins per unit | superseded ⇒ deletable | conversations (atoms = message uuids), sessions (atoms = records), captures |
| **mutable document** | content equality ONLY — every distinct state is unique history | accumulate distinct states; same-key-different-content is a loud CONFLICT | deletable once its states are deposited (the licence) | `memories.json`, an agent's `memory/` folder |
| **curated set** | n/a (grows by curation) | per-element union: move unique, drop byte-identical, CONFLICT on divergent | never (precious) | `data/output/artifacts/downloaded/` |
| **derived** | n/a — regenerate | none needed: re-derive | always (rebuildable) | all of `tmp/cache/`, `data/output/markdown/` |

The lifecycle roots follow from the classes: `data/input/` holds supplied inputs, `tmp/cache/`
caches rebuildable derivations (coupled to no one pipeline — some subdirs are
datum-scoped and die with their datum, others outlive any datum), `data/output/` holds what
outlives any batch or run, `tmp/logs/` holds run-keyed diagnostics of the machinery. The
non-reproducible **readings** of the corpus by the intelligences that tend it live
in `data/output/` alongside the rest of the durable corpus — curation is inference by a
user (`data/output/indexing/accepted.txt`, `data/output/indexing/rejected.txt`) exactly as concept
extraction is inference by a model (`data/output/dashboard/`); the repo privileges no
intelligence over another. They are corpus-derived and stay out of git with the
rest of `data/output/` (shared across machines by the same means — e.g. iCloud — as `data/input/`);
only their reproducible by-product, the pending queue, is a rebuildable `tmp/cache/`
derivation. (User insight, 2026-07-09.)

---

## Operations

All operations are generic over the classification; only **atomisation** is
per-corpus code.

- **atomise** — unit → set of atoms. Atoms are the format's content identities:
  uuid'd immutable constituents where the format provides them (messages, project
  docs); where it doesn't, the content itself — canonical values for bounded
  fields (memory fields, user objects: equality exact, no fingerprint, no
  collision caveat — user simplification, 2026-07-08), fingerprints only where
  content is unbounded (project doc bodies).
  Envelope timestamps are excluded: supersession claims retained *data*, not byte
  equality of snapshots. (`src/main/chat-exports/supersede.py` atomisers.)

- **supersession (⊑)** — per unit: `subset` / `ORPHANED` (unit absent later —
  unique data) / `DIVERGENT` (atoms missing later — unique data). Per product:
  the conjunction over components. Verdicts are **computed, never assumed** — no
  component's class is encoded into the verdict logic (the *unprejudiced
  principle*; user-stated, 2026-07-05). (`supersede.py`.)

- **merge / union** — per class, as tabled above. Identity-keyed sets union
  trivially because keys are global; the only genuine collisions (overlapping
  captures) resolve by the append-only order itself. (`library.py`'s normalise
  CLI `_merge`; cross-machine session copy, 2026-07-06.)

- **accumulate** — deposit a state iff it differs from the nearest earlier
  deposit; deposits are immutable and outlive their producers; a same-stamp
  content mismatch is a CONFLICT, exit 1. The comparison is nearest-earlier, not
  a folder-wide set, because these stores record a *trajectory*: an unchanged
  reading deposits nothing and each deposit is named by the snapshot that first
  exhibited it, so a repeat with nothing between it and its twin is a re-stamp of
  an unchanged reading (suppress) while a repeat after an intervening different
  reading is a genuine return the history must keep (deposit) — position is the
  semantics, not a proxy. Accumulation is what converts a mutable document's
  batch-retention problem into a deletion licence. One operation, one
  implementation: `accumulate()` in `src/main/chat-exports/accumulate.py`, called
  by both the chat-memory library (`memories.py`) and the
  per-conversation summary store (`summaries.py`).

- **transport** — identity-preserving copy between machines. Because identity is
  global and classes determine reconciliation, transport is `cp`: a session
  `.jsonl` moves a conversation's worth of corpus; session + `memory/` folder
  moves an *agent* (user doctrine, 2026-07-06 — proven by the v5 mint, whose
  evidence crossed machines as a file). Reified as a careful cp with the class
  semantics checked: `src/main/code-agents/agent.py` (`yoga agent`) —
  prefix-supersession for the append-only session and its eponymous workspace
  (subagent transcripts, persisted tool-results — files the log references,
  without which a rematerialised agent has dangling limbs); for the memory
  folder, a merge that treats leaf NAMES as dressing (novelty copies, an appendix
  supersedes in place, true divergence keeps both with the incoming fact
  re-dressed by its machine and links following, the index unioning by
  novelty-append). Transported agents live in the shared STORE (`data/input/claude/code/machine-transport`, one
  hand-made symlink per machine), keyed machine-then-project under the ORIGIN machine's name — the
  rooted `machine-name.txt` binding — so provenance is spatial and sender-declared, never
  the receiver's assertion (user layout, 2026-07-08, superseding a dead-drop
  design): transport MIRRORS the agent into its own single-writer outbox, and
  every merge subtlety lives in receive, where two agents actually meet.

- **project / re-derive** — durable identity → presentation: ordinals, markdown,
  matrices, name dressing. Presentation converges to current without ever being
  trusted. (`markdown_projection.ordered()` is the single ordering authority;
  `validate_versions.py` renders matrices at validation time.)

- **normalise** — re-derivation written BACK: converge every recognisable form
  of a durable artifact toward the canonical form, in place, safely
  re-runnable — L1's corollary made an operation (there are no migrations,
  only normalisations). Canonical and recognisable are both data
  (`rsc/naming/library_dir_vintages.csv`,
  `rsc/naming/memory_deposit_vintages.csv`), so migration, healing, and
  maintenance are one operation, and running it on a current corpus proves
  itself by silence. (`library.py`'s `dir_for()` dressing refresh and its
  normalise CLI; `memories.py`'s `normalise_stamps` — converged
  independently, 2026-07-06.)

- **capture** — acquire a non-reproducible reading from an oracle: a model
  re-reading the corpus into a weighted concept list and a chat→category
  assignment (`yoga dashboard capture` → `data/output/dashboard/semantic-concepts.json`,
  `chat-categories.json`), a DOM scrape of a conversation, a memory snapshot
  from a bulk export. The result cannot be regenerated byte-for-byte — the
  oracle is stochastic or the source ephemeral — so a capture is PRECIOUS
  (deposited durably, never disposable) and homed by vettability: `data/output/dashboard/`
  and `data/output/indexing/` for the corpus readings (durable, corpus-derived, shared
  across machines with the rest of `data/output/`); the `data/input/` browser-capture roots when large and
  private; `data/output/memories/` when a versioned deposit. And *curation is capture of a
  user decision* — the same act with a human oracle (`data/output/indexing/accepted.txt`,
  `data/output/indexing/rejected.txt`), which is why they sit beside the model's readings in
  `data/output/`; the repo privileges no intelligence over another (user insight,
  2026-07-09; sharpened 2026-07-13).
  (`yoga dashboard capture`; `yoga indexing accept`/`reject`; the browser-captures
  scrape; `memories.py`.)

- **curate** — the disposal loop: the machine proposes candidates as a derived
  report, a human disposes in durable files, a gate reports anything pending —
  never a disposal in prose. Three instances share the shape: headword curation
  (the captured concepts → `yoga indexing accept` into
  `data/output/indexing/accepted.txt` or `yoga indexing reject` into
  `data/output/indexing/rejected.txt` → `check_index_curation`); the schema
  WORKFLOW (a frontier failure proposes; a minted version narrated in its
  changelog disposes; the coverage and frontier gates report); and the
  model.json reference (the name scan proposes collisions a human curates into
  `rsc/schema/model_join.csv` edges at leisure; an edge asserting one shared
  type — `identical`, `snake_cased` — obligates: document in
  `rsc/schema/model.json` or reject into `rsc/schema/model_rejected.txt` →
  `check_model_obligations` gates BOTH directions of the grounding relation,
  so model.json documents exactly what model_join asserts, minus rejections —
  no unmet obligation, no orphan documentation). Promoted from candidate to
  doctrine by the third instance (issue #19) — exactly the condition the
  candidate entry had set for itself. Two properties of the loop have since
  met the same two-implementations bar (model.json, PR #36; indexing's
  zero-locator headwords, PR #37): the loop runs BOTH directions — every
  proposal disposed, and every disposal grounded, no orphan record — and its
  pressure follows the INPUT tier, not the instance: committed inputs gate
  (model.json), machine-local inputs advise (indexing) — L2's determinism
  split, read as enforcement policy.

- **validate** — datum × schema-version → the machine-local matrix. Two gates:
  *coverage* (every datum modelled by some version) and *frontier* (the newest
  datum modelled by the latest version). A frontier failure is data outgrowing
  its schema — the WORKFLOW's mint trigger, exercised at conversations v13/v14,
  apiConversation v8, session v5.

---

## Products

Composite objects are **products of corpora** with componentwise operations and
conjunction verdicts:

- **bulk export** = conversations × memories × projects × users. A batch is
  deletable iff *every* component is superseded — one mutable document holding
  unique state retains the batch however completely the rest are subsets.
- **agent** = session × memory. Componentwise transport moves it; componentwise
  merge semantics differ (append-only × a set of facts under name-dressing), so
  a forked agent is *two agents thereafter* — diverged facts are installed side
  by side under machine dressing, never auto-unified: the twins ARE the fork, made
  visible, and their reconciliation is a human decision ("hone, not clone").

The product construction is the whole content of "a bulk export is a synchronised
snapshot of four components" and of agent portability — the same shape, found twice.
And the shape has a name (user formulation, 2026-07-07): each product pairs a LOG
with an AGGREGATE — the JSONL is the log, MEMORY is the aggregate; conversations
are the log, memories.json is the aggregate. The log is append-only, totally
ordered, and merges by prefix; the aggregate is a lossy, judgment-made fold over
the log that no code can replay (the fold is the intelligence), which is exactly
why aggregates get their own records where logs need none: accumulation deposits
for the memory document, merge markers for the memory folder — where derivability
ends, logging resumes.

---

## Partiality: operations exist only where structure does

The agents differ, and so do the pipelines: an operation is defined only where the
corpus supplies its requisite structure, and its absence is information, not failure
(L8's contrapositive). Claude conversations have THREE sources (capture, bulk
export, scrape), so cross-source comparison, batch supersession, and the prefix
invariant all exist. Gemini is single-source (scrape only, no API, no ids in time
order, no timestamps in the DOM): supersession between sources is *undefined* — one
cannot opine on it — and creation ordering is unknowable, which is why gemini's
presentation carries no ordinals BY DECISION. Sessions have one source per machine
but global identity, so cross-machine union exists while cross-source comparison
does not arise. A reader (or agent) meeting a missing operation should first ask
which structure the source withholds, not which code is unfinished.

---

## Laws

Each law names its current enforcement (or the incident that taught it).

- **L1 — Idempotence.** Every operation, re-run, is a no-op: validation
  memoisation ("the log IS the memoisation"), deposit dedup, dressing refresh,
  the normalise CLI's fixpoint, the hook's double-run check. An operation that
  isn't idempotent is either wrong or not yet finished being designed.
  Corollary: there are no migrations, only normalisations — a one-shot
  state-A-to-state-B script is dead the moment it runs, while a normaliser
  converges every recognisable form toward the canonical one, where canonical
  and recognisable are both DATA (rsc/naming/library_dir_vintages.csv), so
  migration, healing, and maintenance are the same safely-rerunnable operation
  and running it on a current corpus proves itself by silence.
- **L2 — Determinism split.** Committed artifacts are machine-invariant; machine
  facts (data-tier reports, usernames, local paths) never enter them. Enforced
  structurally by the split report (`run.py` writes the committed log
  itself, code+schema only). Corollary: the deterministic tiers read identically
  on every machine — observed as both machines at 953/12/941 with differing data tiers.
- **L3 — Supersession is a partial order; deletion is licensed, never assumed.**
  ⊑ is transitive across batches; a deletion is justified by a SUPERSEDED verdict
  or by an accumulation licence (states deposited), and by nothing else.
- **L4 — Accumulation is monotone.** Deposits are never modified or removed; they
  outlive their producing batches (observed: three of five memory deposits
  outliving their batches, then reconciling byte-exactly with a restored one).
- **L5 — Presentation is re-derivable and never load-bearing.** Any displayed
  value (ordinal, slug, matrix row) is recomputable from durable identity plus
  the current corpus. Nothing resolves by presentation (the `74-helpdesk_query`
  duplication is the museum piece).
- **L6 — Conflicts are loud.** No operation silently overwrites divergent
  content: CONFLICT + nonzero exit, content left in place, human judgement
  summoned. (Deposit stamps, library merges, memory-folder merges.)
- **L7 — Ownership.** Each pipeline stage owns exactly one output subtree, which
  it may wipe wholesale; nothing else touches it. Blanket wipes above the owned
  leaf are forbidden (the destroyed inferred-tables incident).
- **L8 — Absence is a signal; failure surfaces.** Missing optional input =
  informative skip + exit 0; a crashed step must propagate (the corpus-mode
  silent-success regression, found and fixed in PR #1). Never fabricate a value
  where the honest state is "unknown" (gemini's missing ordinals; `yoga prerequisites`'
  "cannot verify").

- **L9 — Currency.** A consumed derivation is kept current, by the mechanism its
  cell of the freshness matrix (committed × mechanical, issue #19) dictates:
  committed and mechanical → the gate regenerates and byte-compares;
  machine-local, mechanical, machine-consumed → a `run` step (NECESSITY: `run`
  is the only mechanism that can reach it); machine-local, mechanical,
  human-consumed → a `run` step iff CLOSURE holds (every input is refreshed by
  that same run or is stable curation), else the owning noun's status surfaces
  the lag, the safe remedy beside it; curated → the disposal loop (see
  `curate`). Staleness is never silent: an artifact no mechanism can refresh
  automatically is an artifact whose status says so (the dashboard render over
  paid captures — the outlier that forced this law).

---

## Reflexivity: a corpus and some yogic code

The repo is two things: a (chat) corpus, and the yogic code that tends it. This
section records a discovered fact, not a design: the code, once reified, obeys
the same calculus as the corpus — classified on the same axes, operated on by
the same operations, governed by the same laws. Code is not a second ontology.

- **curated set (of code-facing data)** — `rsc/cli/`,
  `data/output/indexing/accepted.txt` with `data/output/indexing/rejected.txt` as its disposal
  record: grow by curation, an absence is a decision, never auto-modified.
- **append-only history** — the format-vintage tables
  (`rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`):
  states only accrue; the current one is a status flag, not an overwrite.
- **projection** — the yoga help text, the zsh completion, the `--plan` output:
  presentation re-derived on demand from durable authority and stored nowhere
  load-bearing (L5), with currency checked by CONTENT, not timestamps (the
  completion is compared byte-wise against a regeneration — observed catching
  its own author's drift, 2026-07-07).
- **committed derivation** — a class the corpus tables did not need:
  regenerable like anything in `tmp/cache/`, but COMMITTED as the machine-invariant
  record other clones diff against — `rsc/test/run.log`,
  `rsc/test/xref.csv`, and the expected-score files beside them. Operations:
  re-run to regenerate (L1); drift from the committed state is loud (L6);
  byte-identity on any clone is the invariant (L2). The deletion licence
  inverts: never hand-edited, only ever regenerated-and-recommitted.
- **atomisation of code** — a pipeline runner atomises to named steps
  (`src/main/steps.sh`), `--plan` is the projection of that atomisation, and
  the CLI table's step column is checked against it — a cross-source
  comparison, with the executing list as the senior source.
- **the terminal grammar (noun / verb)** — the CLI's own invocation surface draws
  the corpus's operation/read line. A bare `yoga <noun>` is a READ: status
  re-derived on demand, writing nothing — a projection (L5), idempotent by
  triviality. A `yoga <noun> <verb>` is an OPERATION, and `sync` is its idempotent
  archetype (L1: re-running is silence), the write kept behind the verb so a bare
  noun can never mutate the tree. Help is a third thing, a projection QUERY —
  `-h`/`--help` answered from the table, never an act — so it left the bare
  invocation and the `help` command both. And the usage each command prints is
  GENERATED from `rsc/cli/`, not stored in a `usage` column: a projection
  kept independently of its source is a projection that can drift, so generating it
  is L5 carried to its end, where the reconciling check has nothing left to
  reconcile (the completeness check deleted itself, and the score went down).
  Drawn to stop a bare noun writing; seen only afterwards to be the operation/read
  split the corpus already keeps.

The laws transfer verbatim: L2 *is* the committed/machine-local split; L6 fired
on a stale completion the day the completion existed; L8 is the yoga launcher's
honesty about a fresh machine (stdlib fallback, venv hint). The conversations
remain the primary objects — this section only records that the machinery
tending them has come to obey its own discipline, extracted, as ever, after
the fact.

## Encoding roadmap

The generic interface already exists in embryo, four times:
`supersede.py`'s `COMPONENTS` (atomisers + one generic comparator),
`library.py` (identity resolution + dressing normalisation + set merge),
`memories.py` (mutable-document accumulation), and
`src/main/code-agents/agent.py` (prefix-supersession + the memory-folder
merge). The spectre they jointly raise is a `Mergeable` protocol (user-named,
2026-07-07): a resource class supplies its merge, and the laws supply the
contract — idempotent (L1: re-merging is silence), monotone (L4: nothing
lost), loud on true conflict (L6), and commutative UP TO DRESSING (merging A
into B and B into A yield the same fact-set with mirrored twin names — L5
says that difference is not load-bearing). Two further properties are already
observable in the memory merge and should ride into the protocol:

- **Merges are detectable and hence invertible.** Every merge action is
  additive (novelty, twin, unioned index line) or prefix-extending (appendix),
  so a compact per-action record — file, action, prior length where extended —
  suffices to undo a past merge exactly, with no snapshots: delete the
  additions, truncate the extensions, drop the recorded lines. An annotation
  in MEMORY.md is the human-visible half of the same record; undo is then a
  deletion LICENSED by the record (L3), not an act of memory. Implemented for
  agent transport (`agent.py`): receive writes a marker block into MEMORY.md
  (begin/end comments wrapping the unioned lines, one hash-carrying act line
  per file action) and `yoga agent demerge` peels the latest block —
  hash-verified, all-or-nothing, refusing anything edited since — which is
  what makes safe VISITS possible: a guest agent received while the host is
  away extracts by transporting itself home, and the host demerges the residue.

The planned protocol (a `corpus.py` under the shared `src/main/` root, per the
module placement doctrine) — `units() → {key: atoms}`, a mutability class,
and generic `superseded` / `merge` / `transport` / `normalise` derived per
class — would collapse those onto instances, and future tooling (a cross-machine
`sync`, agent migration, culture-conformance predicates over session corpora)
becomes instantiation rather than new code. The laws above become property
checks in the pre-commit code tier as the protocol lands: L1 and L3 are directly
testable against synthetic corpora; L2 is already enforced; the rest are enforced
at review until then.
