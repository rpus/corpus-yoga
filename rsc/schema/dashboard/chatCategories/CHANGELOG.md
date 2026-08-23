# chatCategories schema changelog

This schema has no machine-local validation matrix: the capture is validated
in-memory at capture time (dashboard.sh's validate_capture, before promotion to
data/output/dashboard/) rather than writing per-datum `vN.log` files under `tmp/cache/`
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

- `ChatCategories` description (v1, in place) — the dashboard artifact path gained the
  `data/` root (now `data/output/dashboard/chat-categories.json`) for the four-root
  migration (#20), which `rsc/schema/` was excluded from sweeping. No validation effect.
  The narrative above keeps the pre-migration layout of 2026-07-10, the day it describes.
