#!/usr/bin/env bash
# dashboard.sh — the paid model capture behind the corpus dashboard (yoga dashboard).
# NOT per-batch, NOT in the pipeline (2026-07-09): one deliberate single-source
# capture over THE CORPUS ITSELF (output/markdown — every source's conversations,
# claude and gemini alike: the same projected corpus the dashboard describes and
# serve renders; sourced from markdownConversation form, 2026-07-10; gemini joined
# the same day, its ordering a capture of the web-UI listing), written durable to
# output/dashboard/, shared
# by both rooms. The category PALETTE is authored inline in rsc/site/index.html
# (design, not inference); only the weighted concept list (word cloud) and the
# chat→category assignment are captured here.
#
#   yoga dashboard              # status: what is captured (read-only, free)
#   yoga dashboard present      # FREE: render the corpus dashboard page from
#                               #   output/markdown + output/dashboard → cache/dashboard/presentation/
#                               #   (keys = corpus ordinals, all sources; the per-batch
#                               #   pages under cache/chat-exports/ remain export artifacts)
#   yoga dashboard capture      # PAID: re-read the corpus → output/dashboard/
#                               #   [--conversations <path>] overrides the source — a
#                               #     projected markdown corpus dir, an atomised json/
#                               #     dir, or a conversations.json (default:
#                               #     output/markdown — the whole corpus, every source)
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

# chat_list <source> → numbered "N: name" lines, from the one canonical ordering.
# The default source is the projected corpus itself (output/markdown — every source's
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
  if [[ -d "$src" ]] && { compgen -G "$src/*.md" > /dev/null || compgen -G "$src/*/*/conversations/*.md" > /dev/null; }; then
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
    "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/timeline.py" "$src" --table chat-list
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
    | "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/rekey_chats.py" --to-id --conversations "$conv" \
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

# ── the dashboard capture (yoga dashboard capture) ────────────────────────────
# Both PAID model readings the dashboard shows, single-source and durable: the
# weighted concept list (word cloud) and the chat→category assignment. Run once
# over the corpus; both rooms share the result.
#
# capture is DERIVE-then-DEPOSIT: both readings are captured into cache/dashboard
# (the workshop, git-ignored, corpus-scoped like cache/indexing) and validated there, then
# PROMOTED into the durable output/dashboard/ only once both succeed. A failed or
# malformed capture — bad key, 529, non-JSON, empty rows — leaves the durable files
# untouched; set -e aborts before the promotion step. Promotion is `mv` (an atomic
# rename within the repo's one filesystem), the two adjacent so the mixed-vintage
# window is two syscalls rather than a paid API round-trip.
# capture_dashboard <conversations_json> <only> — <only> is "" (both),
# "semantic-concepts", or "chat-categories". Whatever is requested is captured and
# validated in cache/ FIRST, then all of it promoted — so the default two-file refresh
# never leaves the durable pair at mixed vintages if the second capture fails.
capture_dashboard() {
  local conv="$1" only="${2:-}"
  local src_label; src_label="$(basename "$(dirname "$conv")")/$(basename "$conv")"
  # corpus-scoped staging (like cache/indexing): the capture is a reading of the
  # whole corpus, tied to no batch
  local stage="$REPO_DIR/cache/dashboard"
  local dest="$REPO_DIR/output/dashboard"
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

  echo "capturing dashboard readings from $src_label${only:+ (--only $only)} → cache/dashboard (promoted to output/dashboard/ on success)"
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
    echo "  ✓ chat-categories.json ($(jq '.rows | length' "$stage/chat-categories.json") assignments)"
  fi

  [[ "$want_concepts"   == 1 ]] && mv "$stage/semantic-concepts.json" "$dest/semantic-concepts.json"
  [[ "$want_categories" == 1 ]] && mv "$stage/chat-categories.json"   "$dest/chat-categories.json"
  echo "promoted → output/dashboard/ — both rooms share it (output/ is iCloud, not git)"
}

# ── read-only status (bare `yoga dashboard`) ──────────────────────────────────
status() {
  local d="$REPO_DIR/output/dashboard" f
  echo "output/dashboard/ — the paid model captures the dashboard renders"
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

# The corpus itself: output/markdown/claude/chat/conversations — the projected
# markdownConversation corpus, source-agnostic by construction (whatever projects
# into it — captures today, gemini tomorrow — is what the model reads), and the
# very thing the dashboard describes. Its filenames carry ordered()'s canonical
# numbering and its frontmatter the uuids, so the chat list and the rekey map read
# straight off the OUTPUT layer: no batch selection, no atomise-first coupling —
# capture works the moment the corpus exists. (Sourced from the frontier batch's
# cache/<batch>/json/ before 2026-07-10; from input/conversations.json before that —
# each move one layer further down the input→cache→output lifecycle.)
corpus_conversations() {
  local d="$REPO_DIR/output/markdown"
  [[ -d "$d" ]] && compgen -G "$d/*/conversations/*.md" > /dev/null && echo "$d"
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
  local conv="${conversations:-$(corpus_conversations)}"
  [[ -n "$conv" && -e "$conv" ]] || { echo "error: no projected corpus under output/markdown — run the browser-captures pipeline first (yoga run), or pass --conversations <markdown corpus dir | json/ dir | conversations.json>" >&2; exit 1; }
  capture_dashboard "$conv" "$only"
}

main() {
  case "${1:-}" in
    capture)     shift; capture "$@" ;;
    present)     shift; exec "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/present_corpus.py" "$@" ;;
    ''|status)   status ;;
    -h|--help)   grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
    *) echo "yoga dashboard: unknown verb '${1}' — expected 'capture' (paid), 'present' (free render), or bare (status)" >&2; exit 1 ;;
  esac
}

main "$@"
