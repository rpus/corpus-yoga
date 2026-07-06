# The corpus calculus

The operational, set-theoretic semantics of this repo's data — **extracted from the
code that already works, not designed ahead of it**. Every rule below was converged
on independently by two or more implementations before it was written down here;
file references point at the implementations that discovered it. The companion
encoding (a generic protocol with the existing scripts as its instances) is a
planned refactor; this document deliberately precedes it, so that the calculus is
discovered from working code and then imposed back, never the reverse.

Laws are numbered (L1–L8) so that checks and reviews can cite them. Each is a
candidate property check for the pre-commit code tier: the document holds the
narrative, the code holds the shape, and the laws are the testable seam between.

---

## Objects: corpora, classified on two axes

A **corpus** is a set of **units**, each of which atomises to a set of **atoms**
(its content identities). Two axes classify every corpus in the repo, and the
classification determines every operation's semantics.

### Axis 1 — identity: what names a unit durably

| identity scheme | used when | instances |
| --- | --- | --- |
| **uuid** | the unit persists while presentation shifts around it | conversations, messages, sessions, captures, projects, library dirs (`<ordinal>-<slug>-<uuid8>`, uuid8 suffix is the key) |
| **snapshot time** | units are versions of ONE mutable thing — ordination *is* identity | memory deposits (`lib/memories/<ISO>.json`), batch names (export epoch) |
| **path / slug / ordinal** | presentation only — NEVER identity | filenames in `gen/`, ordinal prefixes, slug dressing |

The governing slogan (earned twice by duplicated library dirs): *the LLM speaks
ordinals, storage speaks uuid, presentation re-derives ordinals.* The one deliberate
exception proves the rule: memory snapshots have no uuid because they are not many
things — they are one thing at many times.

### Axis 2 — mutability: what a unit's history can do

| class | supersession | merge across machines | deletion licence | instances |
| --- | --- | --- | --- | --- |
| **append-only** | atom-subset: `A ⊑ B ⟺ atoms(A) ⊆ atoms(B)` | union, freshest-wins per unit | superseded ⇒ deletable | conversations (atoms = message uuids), sessions (atoms = records), captures |
| **mutable document** | content equality ONLY — every distinct state is unique history | accumulate distinct states; same-key-different-content is a loud CONFLICT | deletable once its states are deposited (the licence) | `memories.json`, an agent's `memory/` folder |
| **curated set** | n/a (grows by curation) | per-element union: move unique, drop byte-identical, CONFLICT on divergent | never (precious) | `lib/artifacts/downloaded/` |
| **derived** | n/a — regenerate | none needed: re-derive | always (rebuildable) | all of `gen/`, `lib/markdown/` |

The lifecycle roots follow from the classes: `ext/` holds supplied inputs, `gen/`
holds derived datum-scoped work (dies with its datum), `lib/` holds what outlives
any batch or run, `logs/` holds run-keyed diagnostics of the machinery.

---

## Operations

All operations are generic over the classification; only **atomisation** is
per-corpus code.

- **atomise** — unit → set of atoms. Atoms are the format's content identities:
  uuid'd immutable constituents where the format provides them (messages, project
  docs), content fingerprints where it doesn't (memory fields, user objects).
  Envelope timestamps are excluded: supersession claims retained *data*, not byte
  equality of snapshots. (`src/main/chat-exports/compare_batches.py` atomisers.)

- **supersession (⊑)** — per unit: `subset` / `ORPHANED` (unit absent later —
  unique data) / `DIVERGENT` (atoms missing later — unique data). Per product:
  the conjunction over components. Verdicts are **computed, never assumed** — no
  component's class is encoded into the verdict logic (the *unprejudiced
  principle*; user-stated, 2026-07-05). (`compare_batches.py`.)

- **merge / union** — per class, as tabled above. Identity-keyed sets union
  trivially because keys are global; the only genuine collisions (overlapping
  captures) resolve by the append-only order itself. (`library.py`'s normalise
  CLI `_merge`; cross-machine session copy, 2026-07-06.)

- **accumulate** — deposit a state iff it differs from the nearest earlier
  deposit; deposits are immutable and outlive their producers; a same-stamp
  content mismatch is a CONFLICT, exit 1. Accumulation is what converts a
  mutable document's batch-retention problem into a deletion licence.
  (`src/main/chat-exports/accumulate_memories.py`.)

- **transport** — identity-preserving copy between machines. Because identity is
  global and classes determine reconciliation, transport is `cp`: a session
  `.jsonl` moves a conversation's worth of corpus; session + `memory/` folder
  moves an *agent* (user doctrine, 2026-07-06 — proven by the v5 mint, whose
  evidence crossed machines as a file).

- **project / re-derive** — durable identity → presentation: ordinals, markdown,
  matrices, name dressing. Re-derivation may write back to the filesystem as
  *normalisation*: `library.py`'s `dir_for()` refreshes a dir's ordinal-slug
  dressing on every touch, so presentation converges to current without ever
  being trusted. (`markdown_projection.ordered()` is the single ordering
  authority; `validate_versions.py` renders matrices at validation time.)

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
  merge semantics differ (append-only × mutable document), so a forked agent is
  *two agents thereafter* — merge of diverged memories is a CONFLICT-mediated
  human decision, not an automatic union ("hone, not clone").

The product construction is the whole content of "a bulk export is a synchronised
snapshot of four components" and of agent portability — the same shape, found twice.

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
  structurally by the split report (`pre_commit.py` writes the committed log
  itself, code+schema only). Corollary: the deterministic tiers read identically
  on every machine — observed as both rooms at 953/12/941 with differing data tiers.
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
  where the honest state is "unknown" (gemini's missing ordinals; PREREQUISITES'
  "cannot verify").

---

## Encoding roadmap

The generic interface already exists in embryo, three times:
`compare_batches.py`'s `COMPONENTS` (atomisers + one generic comparator),
`library.py` (identity resolution + dressing normalisation + set merge), and
`accumulate_memories.py` (mutable-document accumulation). The planned
protocol (a `corpus.py` under the shared `src/main/` root, per the module placement
doctrine) — `units() → {key: atoms}`, a mutability class,
and generic `superseded` / `merge` / `transport` / `normalise` derived per
class — would collapse those onto instances, and future tooling (a cross-machine
`sync`, agent migration, culture-conformance predicates over session corpora)
becomes instantiation rather than new code. The laws above become property
checks in the pre-commit code tier as the protocol lands: L1 and L3 are directly
testable against synthetic corpora; L2 is already enforced; the rest are enforced
at review until then.
