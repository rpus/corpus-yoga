#!/usr/bin/env bash
# dashboard.sh — the paid model capture behind the corpus dashboard (yoga dashboard).
# NOT per-batch, NOT in the pipeline (2026-07-09): one deliberate single-source
# capture over the frontier batch (≈ the whole corpus), written durable to
# lib/dashboard/, shared by both rooms. The category PALETTE is authored inline
# in rsc/site/index.html (design, not inference); only the weighted concept list
# (word cloud) and the chat→category assignment are captured here.
#
#   yoga dashboard              # status: what is captured (read-only, free)
#   yoga dashboard capture      # PAID: re-read the corpus → lib/dashboard/
#                               #   [--conversations <path>] overrides the frontier — a
#                               #     json/ dir or a conversations.json (default: the
#                               #     newest atomised batch's gen/<batch>/json/)
#                               #   [--only semantic-concepts|chat-categories] refreshes
#                               #     just one file (default: both) — e.g. re-roll the
#                               #     category assignment without disturbing the concept
#                               #     base the indexing curation sits on
# Capture needs ANTHROPIC_API_KEY.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
API_URL="https://api.anthropic.com/v1/messages"
FORMAT_TABLE_SCRIPT="$SCRIPT_DIR/format_table.py"

# ── helpers ───────────────────────────────────────────────────────────────────

# chat_list <conversations_json> → numbered "N: name" lines
# Numbered "<n>: <name>" list, from the one canonical ordering (markdown_projection.ordered()),
# so the chat indices Claude returns line up with the timeline and the atomised json/ filenames.
chat_list() {
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/timeline.py" "$1" --table chat-list
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
# The LLM speaks ordinals (short, reliable in a prompt); the durable file speaks uuid
# (rekey_chats.py --to-uuid) so it survives corpus renumbering; present.sh re-derives
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
    | "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/rekey_chats.py" --to-uuid --conversations "$conv" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# capture_concepts_to <chat_list> <out_file> — the weighted concept table
capture_concepts_to() {
  local chats="$1" out_file="$2"
  capture_table \
    '["word", "count"]' \
    'word: key concept or theme (word or short phrase)
count: salience weight (not raw frequency); scale so the top concept = 100' \
    'Generate a weighted list of 20-50 key concepts and themes across all conversations.' \
    "Conversations:
$chats" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# validate_table <file> <col1> <col2> — abort if a staged capture is malformed, so
# junk never promotes to the durable lib/dashboard/. format_table.py already guarantees
# the file parses as JSON; this adds the SEMANTIC gate the paid path lacked: the right
# columns, and non-empty 2-column rows (an API error object becomes {"rows": []} or
# "null" and is caught here, in gen/, before it can reach lib/dashboard/).
validate_table() {
  local file="$1" c1="$2" c2="$3"
  jq -e --arg c1 "$c1" --arg c2 "$c2" '
    (.columns == [$c1, $c2])
    and (.rows | type) == "array" and (.rows | length) > 0
    and all(.rows[]; type == "array" and length == 2)
  ' "$file" >/dev/null 2>&1 || {
    echo "yoga dashboard capture: $file failed shape check (want columns [$c1, $c2], non-empty 2-col rows) — staged, NOT promoted" >&2
    exit 1
  }
}

# ── the dashboard capture (yoga dashboard capture) ────────────────────────────
# Both PAID model readings the dashboard shows, single-source and durable: the
# weighted concept list (word cloud) and the chat→category assignment. Run once
# over the frontier batch (≈ the whole corpus); both rooms share the result.
#
# capture is DERIVE-then-DEPOSIT: both readings are captured into gen/ (the workshop,
# git-ignored, batch-scoped like present.sh's output) and validated there, then
# PROMOTED into the durable lib/dashboard/ only once both succeed. A failed or
# malformed capture — bad key, 529, non-JSON, empty rows — leaves the durable files
# untouched; set -e aborts before the promotion step. Promotion is `mv` (an atomic
# rename within the repo's one filesystem), the two adjacent so the mixed-vintage
# window is two syscalls rather than a paid API round-trip.
# capture_dashboard <conversations_json> <only> — <only> is "" (both),
# "semantic-concepts", or "chat-categories". Whatever is requested is captured and
# validated in gen/ FIRST, then all of it promoted — so the default two-file refresh
# never leaves the durable pair at mixed vintages if the second capture fails.
capture_dashboard() {
  local conv="$1" only="${2:-}"
  local batch; batch="$(basename "$(dirname "$conv")")"
  local stage="$REPO_DIR/gen/chat-exports/$batch/dashboard"
  local dest="$REPO_DIR/lib/dashboard"
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

  echo "capturing dashboard readings from $batch${only:+ (--only $only)} → gen/ (promoted to lib/dashboard/ on success)"
  if [[ "$want_concepts" == 1 ]]; then
    capture_concepts_to "$chats" "$stage/semantic-concepts.json"
    validate_table "$stage/semantic-concepts.json" word count
    echo "  ✓ semantic-concepts.json ($(jq '.rows | length' "$stage/semantic-concepts.json") concepts)"
  fi
  if [[ "$want_categories" == 1 ]]; then
    capture_chat_categories "$conv" "$chats" "$categories" "$stage/chat-categories.json"
    validate_table "$stage/chat-categories.json" uuid category
    # Every assigned category MUST be an authored palette name, else present.sh's hue
    # lookup misses and those chats render uncoloured — the join's real dependency, which
    # a columns/rows shape-check alone would not catch (a model 'science'/'math' passes).
    local off
    off="$(jq -r --arg pal "$categories" '
      ($pal | split(", ")) as $ok
      | [.rows[][1]] | unique | map(select(. as $c | ($ok | index($c)) == null)) | join(", ")
    ' "$stage/chat-categories.json")"
    [[ -z "$off" ]] || { echo "yoga dashboard capture: chat-categories assigns off-palette categories ($off) — not promoted. Palette: $categories" >&2; exit 1; }
    echo "  ✓ chat-categories.json ($(jq '.rows | length' "$stage/chat-categories.json") assignments)"
  fi

  [[ "$want_concepts"   == 1 ]] && mv "$stage/semantic-concepts.json" "$dest/semantic-concepts.json"
  [[ "$want_categories" == 1 ]] && mv "$stage/chat-categories.json"   "$dest/chat-categories.json"
  echo "promoted → lib/dashboard/ — both rooms share it (lib/ is iCloud, not git)"
}

# ── read-only status (bare `yoga dashboard`) ──────────────────────────────────
status() {
  local d="$REPO_DIR/lib/dashboard" f
  echo "lib/dashboard/ — the paid model captures the dashboard renders"
  for f in semantic-concepts.json chat-categories.json; do
    if [[ -f "$d/$f" ]]; then
      echo "  ✓ $f ($(jq '.rows | length' "$d/$f") rows)"
    else
      echo "  ○ $f — not captured yet"
    fi
  done
  echo "refresh (PAID): yoga dashboard capture"
}

# ── entry point ───────────────────────────────────────────────────────────────

# The frontier batch's atomised per-conversation pieces (gen/<batch>/json/) — the
# corpus at its most complete, in the NORMALIZED per-conversation shape (uuid-keyed
# {uuid, name, created_at, chat_messages}) that claude produces today and a non-claude
# source (gemini) can produce tomorrow, so the capture becomes source-agnostic.
# Reading the CACHE (gen/) rather than the raw INPUT (ext/conversations.json) is the
# correct layer for the input→cache→output lifecycle — and it makes "frontier" mean
# the newest ATOMISED batch: a batch is a candidate only once the pipeline has
# processed it into json/, so a stray/half-downloaded ext/ dir has no json/ and can't
# be picked. Capture therefore needs `yoga run` to have atomised the batch, and errors
# clearly otherwise. "Newest" is by compare_batches.batch_time — the ONE batch-ordering
# authority, which parses both name styles (epoch and YYYY-MM-DD); export names have
# changed style in history, so lexical name order would misorder a mixed corpus.
# (Moved off ext/conversations.json → gen/json/, 2026-07-09.)
frontier_conversations() {
  "$REPO_DIR/src/run_python_script.sh" -c "
import sys, pathlib
from datetime import datetime, timezone
sys.path.insert(0, '$REPO_DIR/src/main/chat-exports')
from compare_batches import batch_time
gen = pathlib.Path('$REPO_DIR/gen/chat-exports')
floor = datetime.min.replace(tzinfo=timezone.utc)
atomised = [d for d in gen.glob('data-*') if (d / 'json').is_dir()]
if atomised:
    print(max(atomised, key=lambda d: batch_time(d.name) or floor) / 'json')
"
}

capture() {
  local conversations="" only=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversations) conversations="$2"; shift 2 ;;
      --only)          only="$2";          shift 2 ;;
      *) echo "yoga dashboard capture: unknown argument: $1" >&2; exit 1 ;;
    esac
  done
  case "$only" in
    ''|semantic-concepts|chat-categories) ;;
    *) echo "yoga dashboard capture --only: expected 'semantic-concepts' or 'chat-categories', got '$only'" >&2; exit 1 ;;
  esac
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] || { echo "error: ANTHROPIC_API_KEY is not set" >&2; exit 1; }
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  local conv="${conversations:-$(frontier_conversations)}"
  [[ -n "$conv" && -e "$conv" ]] || { echo "error: no atomised frontier batch — run the pipeline first (yoga run), or pass --conversations <json/ dir | conversations.json>" >&2; exit 1; }
  capture_dashboard "$conv" "$only"
}

main() {
  case "${1:-}" in
    capture)     shift; capture "$@" ;;
    ''|status)   status ;;
    -h|--help)   grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
    *) echo "yoga dashboard: unknown verb '${1}' — expected 'capture' (paid) or bare (status)" >&2; exit 1 ;;
  esac
}

main "$@"
