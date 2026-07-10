# chatCategories schema changelog

This schema has no machine-local validation matrix: the capture is validated
in-memory at capture time (dashboard.sh's validate_capture, before promotion to
lib/dashboard/) rather than writing per-datum `vN.log` files under `gen/`
(see `rsc/schema/WORKFLOW.md` — the markdownConversation precedent).

---

## v1

Initial schema: the format_table-styled two-column table `yoga dashboard capture`
stages to gen/dashboard and promotes to lib/dashboard/. Minted 2026-07-10 when the
capture's shape gate moved from a hand-written jq check into the schema system
(closing the review's altitude finding), the same day the capture went corpus-wide
(claude + gemini) and the identity column widened from claude's uuid to the
source-native conversation id.
