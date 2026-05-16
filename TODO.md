# TODO

When something is discovered or changes: write it here. The human maintainer audits
TODO (and commits) and decides what gets promoted into permanent docs, acted on, or
discarded. Documentation updated in-place without going through TODO rots silently.

---

## Pre-public checklist

- [ ] Add a LICENSE file before making the repo public.
- [ ] `src/main/schema_recommendations.py` — all 9 checks are stubbed. Script is pipeline-agnostic (correct location). Once implemented, call it from all three pipeline `validate.sh` scripts on validation success.
