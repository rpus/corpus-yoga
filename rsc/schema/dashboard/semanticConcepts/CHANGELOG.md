# semanticConcepts schema changelog

This schema has no machine-local validation matrix: the capture is validated
in-memory at capture time (dashboard.sh's validate_capture, before promotion to
lib/dashboard/) rather than writing per-datum `vN.log` files under `gen/`
(see `rsc/schema/WORKFLOW.md` — the markdownConversation precedent).

---

## v2

- Added the `source` column (`claude` / `gemini` / `both`): each concept is tagged
  with the source(s) it is salient in, captured in the same single paid reading —
  the conversation list in the prompt carries `[source]` markers, derived from the
  id shape (36-char uuid = claude, 16-hex = gemini). Minted 2026-07-10 for the
  dashboard's source toggle: the word cloud filters client-side; a pre-v2
  (untagged) capture still renders with the toggle disabled, and the next
  `yoga dashboard capture` upgrades it in place.

## v1

Initial schema: the format_table-styled two-column table `yoga dashboard capture`
stages to gen/dashboard and promotes to lib/dashboard/. Minted 2026-07-10 when the
capture's shape gate moved from a hand-written jq check into the schema system
(closing the review's altitude finding), the same day the capture went corpus-wide
(claude + gemini) and the identity column widened from claude's uuid to the
source-native conversation id.
