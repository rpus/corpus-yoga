#!/usr/bin/env bash
# dashboard.sh (yoga dashboard) — the corpus dashboard: paid captures, free render.
#
# Usage:
#   yoga dashboard [status]     # what is captured + currency of render and captures (read-only, free)
#   yoga dashboard sync         # FREE: render data/output/site/index.html (idempotent)
#                               #   from data/output/markdown + the durable captures
#   yoga dashboard capture      # PAID (needs ANTHROPIC_API_KEY): re-read the corpus
#     [--conversations <path>]  #   source override: markdown corpus dir | json/ dir | conversations.json
#     [--only semantic-concepts|chat-categories]   # refresh one file (default: both)
#
# Captures land durable in data/output/dashboard/ (shared across machines); the category
# palette is authored in rsc/site/index.html; the capture schemas live under
# rsc/schema/dashboard/. The capture half is acquisition and lives here with its
# command (#381); the render/probe machinery stays with the pipeline
# (src/main/pipeline/chat-exports/), reached root-relatively below.

set -euo pipefail

# Guard at this file's own address first; sourcing the probe overwrites SELF
# and SCRIPT_DIR with the probe's, so both are re-asserted after the sources —
# the banner below must speak this file's address, not the probe's.
SELF='src/main/cli/dashboard/dashboard.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
PIPELINE="$REPO_DIR/src/main/pipeline/chat-exports"   # the render/probe half's home (#381)
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"   # the shell face of YOGA_NO_SEND (#29)
# shellcheck source=src/main/pipeline/chat-exports/dashboard_status.sh
source "$PIPELINE/dashboard_status.sh"   # status/currency + the corpus-shape helpers, one authority
SELF='src/main/cli/dashboard/dashboard.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
API_URL="https://api.anthropic.com/v1/messages"
FORMAT_TABLE_SCRIPT="$PIPELINE/format_table.py"

# chat_list <source> → numbered "N: name" lines, from the one canonical ordering.
# The default source is the projected corpus itself (data/output/markdown — every source's
# conversations dir combined, claude first), whose filenames carry the cached
# ordering — read back by markdown_projection.corpus_index, the format authority.
# Each line carries a [source] marker: the stem's <source> dir prefix on a
# multi-source corpus (claude / gemini / code — a code session's id is a 36-char
# uuid too, so the id shape alone cannot name it), falling back to the id shape
# for a single conversations dir — the concept capture tags its rows from these.
# A batch source (conversations.json or atomised json/) still works via
# timeline.py, re-deriving the claude numbering with ordered() (no markers: a
# batch is claude by construction, and the prompt says so).
chat_list() {
  local src="$1"
  if [[ -d "$src" ]] && { compgen -G "$src/*.md" > /dev/null || has_conversations "$src"; }; then
    "$REPO_DIR/src/run_python_script.sh" -c "
import sys
sys.path.insert(0, '$REPO_DIR/src/main')
from markdown_projection import corpus_index
for n, stem, title, cid in corpus_index('$src'):
    # stem is <provider>/<channel>/<file> at a corpus root; the marker keeps its
    # historical vocabulary (claude | gemini | code) — 'code' names the channel
    parts = stem.split('/')
    source = ('code' if len(parts) == 3 and parts[1] == 'code' else parts[0]) \
        if len(parts) > 1 else ('claude' if len(cid) == 36 else 'gemini')
    print(f'{n} [{source}]: {title}')
"
  else
    "$REPO_DIR/src/run_python_script.sh" "$PIPELINE/timeline.py" "$src" --table chat-list
  fi
}

# capture_table <columns_json> <column_semantics> <task> <data> → prints {columns, rows} JSON
# column_semantics: one line per column — "name: what it means"
capture_table() {
  local columns="$1" semantics="$2" task="$3" data="$4"
  local request response
  request="$(jq -n \
    --arg model  "$MODEL" \
    --arg user   "Table schema — columns: $columns
Column semantics:
$semantics

Task: $task

$data

Return a JSON object with exactly two keys: \"columns\" (the schema array above) and \"rows\" (array of arrays). No markdown, no prose, no code fences. Start with { and end with }." \
    '{model: $model, max_tokens: 4096,
      system: "You are a data analyst. Return only valid JSON.",
      messages: [{role: "user", content: $user}]}')"
  response="$(curl -sf "$API_URL" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$request")"
  # A reading cut off at the token ceiling is not a short reading, it is an incomplete one,
  # and the text may still parse. Ask the response why it stopped rather than inferring it
  # from the rows that arrived (L8: failure surfaces; never fabricate where the honest state
  # is "unknown").
  local stop; stop="$(jq -r '.stop_reason // "unknown"' <<< "$response")"
  if [[ "$stop" != "end_turn" ]]; then
    echo "yoga dashboard capture: the model stopped with stop_reason=$stop (not end_turn) — " \
         "the reading is incomplete and is NOT promoted" >&2
    return 1
  fi
  jq -r '.content[0].text' <<< "$response"
}

# ── per-table capture functions ───────────────────────────────────────────────

# The canonical category names — AUTHORED, not captured: read from the palette
# inlined in the homepage template (rsc/site/index.html), the one authority. Exits
# non-zero (not AttributeError) if the block can't be found, so a template reformat
# fails loudly; the caller pre-flights this before any paid call.
canonical_categories() {
  "$REPO_DIR/src/run_python_script.sh" -c "
import re, json, pathlib, sys
h = pathlib.Path('$REPO_DIR/rsc/site/index.html').read_text()
m = re.search(r'id=\"data-categories\"[^>]*>\s*(\{.*?\})\s*</script>', h, re.S)
if not m:
    sys.exit('canonical_categories: no data-categories palette block in rsc/site/index.html')
print(', '.join(r[0] for r in json.loads(m.group(1))['rows']))
"
}

# capture_chat_categories <conversations_json> <chat_list> <categories> <out_file> — the chat→category assignment.
# The palette is authored (canonical_categories); only the ASSIGNMENT is captured.
# The LLM speaks ordinals (short, reliable in a prompt); the durable file speaks the conversation id (claude uuid / gemini app id)
# (rekey_chats.py --to-id) so it survives corpus renumbering; present.sh re-derives
# the then-current ordinals at injection time. Both the chat list and the palette are
# passed in (resolved by the caller before any paid call) so their failure aborts
# before we spend, not silently or mid-run.
capture_chat_categories() {
  local conv="$1" chats="$2" categories="$3" out_file="$4"
  capture_table \
    '["chat", "category"]' \
    'chat: integer index of the conversation (from the list below)
category: one of the provided category names' \
    "Assign each conversation to exactly one of these categories: $categories" \
    "Conversations:
$chats" \
    | "$REPO_DIR/src/run_python_script.sh" "$PIPELINE/rekey_chats.py" --to-id --conversations "$conv" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# capture_concepts_to <chat_list> <out_file> — the weighted concept table, each
# concept tagged with the provider(s) it is salient in (from the chat list's [source]
# markers) — the dimension behind the dashboard's provider toggle (schema v2)
capture_concepts_to() {
  local chats="$1" out_file="$2"
  capture_table \
    '["word", "count", "provider"]' \
    'word: key concept or theme (word or short phrase)
count: salience weight (not raw frequency); scale so the top concept = 100
provider: which provider the concept is salient in — "claude", "gemini", or "both", from the [source] markers in the conversation list (a list without markers is all claude)' \
    'Generate a weighted list of 20-50 key concepts and themes across all conversations, tagging each concept with the provider(s) whose conversations it is salient in.' \
    "Conversations:
$chats" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# validate_capture <staged-file> <schema-family> — the staged capture must validate
# against the LATEST rsc/schema/dashboard/<family> version before promotion
# (validate.py, in-memory — the markdownConversation no-matrix precedent: captures
# validate at write time, no per-datum logs). This retired the hand-written shape
# jq: the shape contract now lives in the schema system like every other data
# class. The palette join (category ∈ authored names) is a cross-file constraint
# beyond JSON Schema and stays checked separately below.
validate_capture() {
  local file="$1" family="$2" schema verdict
  schema="$(printf '%s\n' "$REPO_DIR/rsc/schema/dashboard/$family"/v*.json | sort -V | tail -1)"
  verdict="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate.py" "$file" "$schema")"
  [[ "$verdict" == 'Valid!' ]] || {
    echo "yoga dashboard capture: $file fails $family $(basename "$schema" .json) — staged, NOT promoted" >&2
    printf '%s\n' "$verdict" >&2
    exit 1
  }
}





# The EXACT coverage join, computed where it is already free: the capture walks
# the corpus for its chat list anyway, so before a cent is spent it names the
# gap the status only estimates — status quantifies the lag with the cheap
# row-count proxy (~M, no id join); the effecting verb reports captured ∩
# corpus exactly, with the never-captured count the paid re-read is about to
# close and any captured-but-gone ids the proxy silently counts as coverage.
# (The user's shape: status is; effecting; status is.) Corpus-dir sources only
# — a batch source has no corpus_index — and no prior capture means no join.
# coverage_of <conversations-dir> <chat-categories.json> → "captured never-captured gone total"
# ONE measurement, taken of whichever file is named: the durable one before the effect, the
# staged one after it. G19's bracket is only readable if both ends measure the same thing —
# the exact id join, never the ~M row-count proxy the status uses.
coverage_of() {
  local conv="$1" cat="$2"
  # A MISSING capture file is a measurement, not a failure: nothing captured, everything
  # uncovered. Returning early printed nothing at all for a first-ever capture — no extent,
  # and no intent either, which is the one thing that IS knowable then.
  [[ -d "$conv" ]] || return 1
  "$REPO_DIR/src/run_python_script.sh" -c "
import json, os, sys
sys.path.insert(0, '$REPO_DIR/src/main')
from markdown_projection import corpus_index
corpus = {cid for _, _, _, cid in corpus_index('$conv')}
captured = ({r[0] for r in json.load(open('$cat')).get('rows', [])}
            if os.path.isfile('$cat') else set())
print(len(corpus & captured), len(corpus - captured), len(captured - corpus), len(corpus))
"
}

# The LEADING extent, and the intent: what is, and what this capture will do to it.
# Formatted from coverage_of, never re-derived — two joins that could disagree about the
# same corpus is the defect #55 fixed one layer up.
coverage_report() {
  local conv="$1" out captured never gone total
  out="$(coverage_of "$conv" "$REPO_DIR/data/output/dashboard/chat-categories.json")" || return 0
  read -r captured never gone total <<< "$out"
  if [[ -f "$REPO_DIR/data/output/dashboard/chat-categories.json" ]]; then
    echo "coverage (exact): $captured captured · $never never captured · $gone captured-but-gone"
  else
    echo "coverage (exact): no prior capture — $never conversation(s) uncovered"
  fi
  echo "intent: re-read all $total conversation(s)"
}


# ── the dashboard capture (yoga dashboard capture) ────────────────────────────
# Both PAID model readings the dashboard shows, single-source and durable: the
# weighted concept list (word cloud) and the chat→category assignment. Run once
# over the corpus; both machines share the result.
#
# capture is DERIVE-then-DEPOSIT: both readings are captured into tmp/cache/dashboard
# (the workshop, git-ignored, corpus-scoped like tmp/cache/indexing) and validated there, then
# PROMOTED into the durable data/output/dashboard/ only once both succeed. A failed or
# malformed capture — bad key, 529, non-JSON, empty rows — leaves the durable files
# untouched; set -e aborts before the promotion step. Promotion is `mv` (an atomic
# rename within the repo's one filesystem), the two adjacent so the mixed-vintage
# window is two syscalls rather than a paid API round-trip.
# capture_dashboard <conversations_json> <only> — <only> is "" (both),
# "semantic-concepts", or "chat-categories". Whatever is requested is captured and
# validated in tmp/cache/ FIRST, then all of it promoted — so the default two-file refresh
# never leaves the durable pair at mixed vintages if the second capture fails.
capture_dashboard() {
  local conv="$1" only="${2:-}"
  local src_label; src_label="$(basename "$(dirname "$conv")")/$(basename "$conv")"
  # corpus-scoped staging (like tmp/cache/indexing): the capture is a reading of the
  # whole corpus, tied to no batch
  local stage="$REPO_DIR/tmp/cache/dashboard"
  local dest="$REPO_DIR/data/output/dashboard"
  mkdir -p "$stage" "$dest"

  local want_concepts=1 want_categories=1
  case "$only" in
    semantic-concepts) want_categories=0 ;;
    chat-categories)   want_concepts=0 ;;
  esac

  # Resolve BOTH free inputs up front, as plain assignments (not `local x=$(…)`, which
  # would swallow the failure), so a broken timeline.py / missing venv / reformatted
  # palette aborts here — before any paid call — rather than mid-run after we have
  # already spent. timeline.py parses conversations.json once, not once per table.
  local chats categories=""
  chats="$(chat_list "$conv")"
  [[ "$want_categories" == 1 ]] && categories="$(canonical_categories)"

  echo "capturing dashboard readings from $src_label${only:+ (--only $only)} → tmp/cache/dashboard (promoted to data/output/dashboard/ on success)"
  if [[ "$want_concepts" == 1 ]]; then
    capture_concepts_to "$chats" "$stage/semantic-concepts.json"
    validate_capture "$stage/semantic-concepts.json" semanticConcepts
    echo "  ✓ semantic-concepts.json ($(jq '.rows | length' "$stage/semantic-concepts.json") concepts)"
  fi
  if [[ "$want_categories" == 1 ]]; then
    capture_chat_categories "$conv" "$chats" "$categories" "$stage/chat-categories.json"
    validate_capture "$stage/chat-categories.json" chatCategories
    # Every assigned category MUST be an authored palette name, else present.sh's hue
    # lookup misses and those chats render uncoloured — the join's real dependency, which
    # a columns/rows shape-check alone would not catch (a model 'science'/'math' passes).
    local off
    off="$(jq -r --arg pal "$categories" '
      ($pal | split(", ")) as $ok
      | [.rows[][1]] | unique | map(select(. as $c | ($ok | index($c)) == null)) | join(", ")
    ' "$stage/chat-categories.json")"
    [[ -z "$off" ]] || { echo "yoga dashboard capture: chat-categories assigns off-palette categories ($off) — not promoted. Palette: $categories" >&2; exit 1; }
    # The TRAILING extent (G19): the same exact join taken of the staged file, so it can be
    # compared with the leading one. A row count cannot do this job — it counted 125 while
    # the corpus held 137 and printed a ✓ beside it.
    local after captured never gone total
    if after="$(coverage_of "$conv" "$stage/chat-categories.json")"; then
      read -r captured never gone total <<< "$after"
      echo "  ✓ chat-categories.json — coverage (exact): $captured of $total captured" \
           "· $never never captured · $gone captured-but-gone"
      # Intent was "re-read all $total". Unmet intent is the thing to say out loud; a
      # capture that covers LESS than the durable one it would replace is not a new
      # record, it is a failed re-read, and promoting it would lose coverage that was
      # paid for once already.
      if [[ "$never" -gt 0 ]]; then
        echo "  ⚠ intent unmet: the capture re-read $total conversation(s) and returned" \
             "$captured — $never uncovered"
        local before_captured=0 b
        if b="$(coverage_of "$conv" "$dest/chat-categories.json")"; then
          read -r before_captured _ _ _ <<< "$b"
        fi
        if [[ "$captured" -lt "$before_captured" ]]; then
          echo "yoga dashboard capture: coverage would fall from $before_captured to" \
               "$captured — NOT promoted; the staged reading is left in $stage for inspection" >&2
          return 1
        fi
      fi
    else
      echo "  ✓ chat-categories.json ($(jq '.rows | length' "$stage/chat-categories.json") assignments)" \
           "— coverage not computable (no corpus index for this source)"
    fi
  fi

  [[ "$want_concepts"   == 1 ]] && mv "$stage/semantic-concepts.json" "$dest/semantic-concepts.json"
  [[ "$want_categories" == 1 ]] && mv "$stage/chat-categories.json"   "$dest/chat-categories.json"
  echo "promoted → data/output/dashboard/ — both machines share it (data/output/ is iCloud, not git)"
}

# ── read-only status (bare `yoga dashboard`) ──────────────────────────────────
# ── entry point ───────────────────────────────────────────────────────────────

# The corpus itself: data/output/markdown/claude/chat/conversations — the projected
# markdownConversation corpus, source-agnostic by construction (whatever projects
# into it — captures today, gemini tomorrow — is what the model reads), and the
# very thing the dashboard describes. Its filenames carry ordered()'s canonical
# numbering and its frontmatter the uuids, so the chat list and the rekey map read
# straight off the OUTPUT layer: no batch selection, no atomise-first coupling —
# capture works the moment the corpus exists. Reading from a batch's cache, or from
# an input file, couples the dashboard to a layer above the output it describes.
corpus_conversations() {
  local d="$REPO_DIR/data/output/markdown"
  has_conversations "$d" && echo "$d"
}

capture() {
  local conversations="" only="" dry_run=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversations) conversations="$2"; shift 2 ;;
      --only)          only="$2";          shift 2 ;;
      --dry-run)       dry_run=1;          shift ;;
      *) echo "yoga dashboard capture: unknown argument: $1" >&2; exit 1 ;;
    esac
  done
  case "$only" in
    ''|semantic-concepts|chat-categories) ;;
    *) echo "yoga dashboard capture --only: expected 'semantic-concepts' or 'chat-categories', got '$only'" >&2; exit 1 ;;
  esac
  # the key is the EFFECT's prerequisite, not the preview's: --dry-run must work on a
  # machine that cannot spend, or it cannot answer "what would this cost me?" there
  # The PAID send is the work, so refusal is loud and OUTRANKS the key check (a refused
  # machine's missing key is irrelevant) — but --dry-run sends nothing and must keep
  # working under YOGA_NO_SEND: it is the preamble a refused machine still deserves (#29).
  [[ -n "$dry_run" ]] || assert_may_send "PAID model reads of the corpus (yoga dashboard capture)" || exit 1
  [[ -n "$dry_run" || -n "${ANTHROPIC_API_KEY:-}" ]] || { echo "error: ANTHROPIC_API_KEY is not set" >&2; exit 1; }
  # The one command that spends money left no record of what it bought: terminal scrollback
  # was the whole audit trail. A paid call is not reproducible for free, so the log is not a
  # convenience here — it is the only evidence. Path per the command/verb rule (#54).
  local log
  log="$REPO_DIR/tmp/logs/dashboard/capture/$(date -u '+%Y-%m-%dT%H%M%SZ').log"
  mkdir -p "$(dirname "$log")"
  exec > >(tee -a "$log") 2>&1
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local conv
  conv="${conversations:-$(corpus_conversations)}"
  [[ -n "$conv" && -e "$conv" ]] || { echo "error: no conversation markdown under data/output/markdown (looked for $CONVERSATIONS_GLOB at any depth) — project the corpus with \`yoga pipeline run\`, or pass --conversations <markdown corpus dir | json/ dir | conversations.json>" >&2; exit 1; }
  echo "model: $MODEL · source: ${conv#"$REPO_DIR/"}${only:+ · --only $only}"
  coverage_report "$conv"
  # A dry run is the leading half, run alone: the extent and the intent, and nothing else.
  # It needs no separate implementation because it IS the bracket's first call — which is
  # also why it cannot lie about an effect it did not perform. Worth most on this verb of
  # all: the others preview a free or reversible act, this one previews a purchase.
  if [[ -n "$dry_run" ]]; then
    echo "--dry-run: nothing captured, nothing promoted, nothing spent"
    return 0
  fi
  capture_dashboard "$conv" "$only"
}

main() {
  case "${1:-}" in
    capture)     shift; capture "$@" ;;
    sync)        shift; exec "$REPO_DIR/src/run_python_script.sh" "$PIPELINE/present_corpus.py" "$@" ;;
    '')          status ;;   # bare noun → status; there is no `status` verb (this IS it)
    -h|--help)   awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "yoga dashboard: unknown verb '${1}' — expected 'capture' (paid), 'sync' (free render), or bare (status)" >&2; exit 1 ;;
  esac
}

main "$@"
