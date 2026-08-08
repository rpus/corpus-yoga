#!/usr/bin/env bash
# dashboard_status.sh — the dashboard's read-only status probe: what is captured,
# and the currency of render and captures (L9 — the noun's one honest freshness
# mechanism; the captures are paid, so no run step may keep them fresh).
#
# Callers (#381): the usr gate's corpus tail (step_ok dashboard — every
# `yoga pipeline run` carries the INFO atoms), and the cli face
# (src/main/cli/dashboard/dashboard.sh), which sources this file for its bare
# verb — the probe carries none of the paid capture's machinery.
#
# Sourced or executed: when sourced, SELF and SCRIPT_DIR here overwrite the
# sourcer's — safe only because the sourcer's own guard has run by its source line.

set -euo pipefail

SELF='src/main/pipeline/chat-exports/dashboard_status.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

# The corpus's shape, stated ONCE: conversation markdown at any depth under a root.
# Left to each call site, the depth is decided once per caller and they disagree — one
# matching any depth, one two directory levels, one a single level. The corpus is two deep
# (data/output/markdown/<source>/<kind>/conversations/), so capture reported "no projected
# corpus" about the directory status had just counted, and told the reader to re-run a
# pipeline that had already produced it. Depth belongs to the layout, not to each caller.
CONVERSATIONS_GLOB='*/conversations/*.md'

has_conversations() {   # a root holding conversation markdown at any depth
  [[ -d "$1" ]] && [[ -n "$(find "$1" -path "$CONVERSATIONS_GLOB" -print -quit 2>/dev/null)" ]]
}

count_conversations() {
  find "$1" -path "$CONVERSATIONS_GLOB" 2>/dev/null | wc -l | tr -d ' '
}

status() {
  local d="$REPO_DIR/data/output/dashboard" f
  echo "data/output/dashboard/ — the paid model captures the dashboard renders"
  for f in semantic-concepts.json chat-categories.json; do
    if [[ -f "$d/$f" ]]; then
      echo "  ✓ $f ($(jq '.rows | length' "$d/$f") rows)"
    else
      echo "  ○ $f — not captured yet"
    fi
  done
  currency
}

# The noun's own currency report (issue #19, outlier 2). The dashboard is
# human-consumed and its captures are paid: CLOSURE fails and NECESSITY does not
# apply, so no `run` step may keep it fresh — this status is its one honest
# freshness mechanism (L9). Two layers, each with the safe verb beside it:
# render vs corpus+captures (free sync), captures vs corpus (paid capture).
# Both are INFO atoms — normal conditions, not defects (the render lags because
# the corpus grew; the captures lag because they are paid and deliberately out
# of `run`) — so the run tail's hoisting carries them into every `yoga pipeline run`.
currency() {
  local corpus="$REPO_DIR/data/output/markdown"
  local render="$REPO_DIR/data/output/site/index.html"
  local d="$REPO_DIR/data/output/dashboard"
  local n m=0 f render_state
  [[ -d "$corpus" ]] || return 0   # L8: no corpus yet — nothing to be current against
  n="$(count_conversations "$corpus")"
  [[ "$n" -gt 0 ]] || return 0
  [[ -f "$d/chat-categories.json" ]] && m="$(jq '.rows | length' "$d/chat-categories.json")"
  if [[ ! -f "$render" ]]; then
    render_state='absent'
  else
    # the render's inputs are the corpus AND the captures — either newer means behind.
    # These -newer/-nt comparisons are the one advisory clock key surviving #369's
    # census, owned by this probe (#381): INFO atoms only, never a gate or a skip.
    local behind=''
    [[ -n "$(find "$corpus" -path "$CONVERSATIONS_GLOB" -newer "$render" -print -quit 2>/dev/null)" ]] \
      && behind='corpus'
    for f in semantic-concepts.json chat-categories.json; do
      [[ "$d/$f" -nt "$render" ]] && { [[ "$behind" == *captures* ]] || behind="${behind:+$behind and }captures"; }
    done
    render_state="${behind:+behind ($behind changed since the render)}"
    render_state="${render_state:-current}"
  fi
  echo "corpus: $n conversation(s) · captures cover ~$m · render: $render_state"
  if [[ "$render_state" != current ]]; then
    echo "INFO: the dashboard render is $render_state — free to fix:"
    echo "    → run: yoga dashboard sync   # FREE — re-render from the current corpus + captures"
  fi
  if [[ "$m" -lt "$n" ]]; then
    echo "INFO: the captures cover ~$m of $n conversation(s) — the paid layer lags the corpus; sync does NOT fix this:"
    echo "    → run: yoga dashboard capture   # PAID — the model re-reads the corpus"
  fi
}


# Executed directly (the corpus tail's step): the probe IS the bare verb.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  status
fi
