# chatCategories schema changelog

This schema has no machine-local validation matrix: the capture is validated
in-memory at capture time (src/main/indexing/capture.sh's validate_capture, before promotion to
data/output/indexing/) rather than writing per-datum `vN.log` files under `tmp/cache/`
(see `rsc/schema/WORKFLOW.md` — the markdownConversation precedent).

---

## v1

Initial schema: the format_table-styled two-column table `corpus-yoga dashboard capture`
stages to cache/dashboard and promotes to output/dashboard/. Minted 2026-07-10 when the
capture's shape gate moved from a hand-written jq check into the schema system
(closing the review's altitude finding), the same day the capture went corpus-wide
(claude + gemini) and the identity column widened from claude's uuid to the
source-native conversation id.

#### Refactored

- `ChatCategories` description (v1, in place) and the preamble above - the capture that stages and validates it is src/main/indexing/capture.sh, staging under tmp/cache/indexing and promoting to data/output/indexing/, where they named dashboard.sh, cache/dashboard and data/output/dashboard/, retired with the dashboard command (issues/1106). No validation effect.

- The artifact's home in the description (latest version, in place) - `data/output/indexing/inferred-chat-categories.json` since 2026-09-15 (issues/655), when the family moved from the dashboard root of rsc/schema to the indexing root, beside the curation the same command writes and the file gained its state prefix. No validation effect.

- `ChatCategories` description (v1, in place) — the dashboard artifact path gained the
  `data/` root (now `data/output/dashboard/chat-categories.json`) for the four-root
  migration (pull/20), which `rsc/schema/` was excluded from sweeping. No validation effect.
  The narrative above keeps the pre-migration layout of 2026-07-10, the day it describes.
- `ChatCategories` description (v1, in place) - the palette's home is named
  `rsc/site/index.template.html`, the template's name since issues/650 (2026-09-15); the
  file is the same. No validation effect.
