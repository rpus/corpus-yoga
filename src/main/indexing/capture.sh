#!/usr/bin/env bash
# capture.sh (corpus-yoga indexing capture) — the PAID semantic reading of the corpus:
# the model reads the conversation list (the numbered titles, provider-marked) for the two index tables, weighted
# concepts (inferred-semantic-concepts.json — the index's headwords once adopted) and the
# chat-to-category assignment (inferred-chat-categories.json — a categorical index the
# site build consumes). One paid sweep, one derive-then-deposit bracket.
#
# This file CAPTURES, bare or with flags; what is deposited and how far the paid
# layer lags the corpus is `corpus-yoga indexing`'s to say (indexing.py).
#
# Usage (via `corpus-yoga indexing capture`, or directly):
#   src/main/indexing/capture.sh                    # PAID (needs ANTHROPIC_API_KEY)
#     [--conversations <path>] [--only semantic-concepts|chat-categories]
#
# Captures land durable in data/output/indexing/ as inferred-*.json (shared across machines; the
# path keeps the artifact's name — the rendered page it feeds); the category
# palette is authored in rsc/site/index.template.html; the capture schemas live under
# rsc/schema/indexing/.

set -euo pipefail

SELF='src/main/indexing/capture.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"
PIPELINE="$REPO_DIR/src/main/export"   # the chat pipeline's helpers (timeline)
MAIN_DIR="$REPO_DIR/src/main"                         # the corpus shape and the rekey
# shellcheck source=src/main/report.sh
source "$REPO_DIR/src/main/report.sh"   # effect - what an act reports after its lines (issues/876)
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"   # the paid read is a send the declaration names (issues/29, issues/1022)
source "$REPO_DIR/src/main/cli/parse_argv.sh"   # -h and the refusal of undeclared argv, from the declaration (issues/474)
# shellcheck source=src/main/corpus_shape.sh
source "$MAIN_DIR/corpus_shape.sh"   # the corpus's shape, stated once
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-5-5}"
FORMAT_TABLE_SCRIPT="$REPO_DIR/src/main/format_table.py"
REPLY_SHAPE_SCRIPT="$REPO_DIR/src/main/indexing/reply_shape.py"   # the shape a table is asked for in, from its family (issues/1161)

# chat_list <source> → numbered "N: name" lines, from the one canonical ordering.
# The default source is the projected corpus itself (data/output/markdown — every source's
# conversations dir combined, claude first), whose filenames carry the cached
# ordering — read back by markdown_projection.corpus_index, the format authority.
# Each line carries a [source] marker, the conversation's PROVIDER and nothing else, a
# chat and a code session alike: the first segment of the stem on a corpus root
# (<provider>/<channel>/<file>), falling back to the id shape for a single
# conversations dir. The concept capture tags its rows from these, so every marker is
# a value the provider column admits (issues/682).
# A batch source (conversations.json or atomised json/) still works via
# timeline.py, re-deriving the claude numbering with ordered() (no markers: a
# batch is claude by construction, and the prompt says so).
chat_list() {
  local src="$1"
  if [[ -d "$src" ]] && { compgen -G "$src/*.md" > /dev/null || has_conversations "$src"; }; then
    "$REPO_DIR/src/run_python_script.sh" -c "
import sys
from markdown_projection import corpus_index
for n, stem, title, cid in corpus_index('$src'):
    parts = stem.split('/')
    source = parts[0] if len(parts) > 1 else ('claude' if len(cid) == 36 else 'gemini')
    print(f'{n} [{source}]: {title}')
"
  else
    "$REPO_DIR/src/run_python_script.sh" "$PIPELINE/timeline.py" "$src" --table chat-list
  fi
}

# table_request <columns_json> <column_semantics> <task> <data> <reply_schema> → prints the request body:
# the table's shape travels as output_config.format (issues/1161), so the API returns its rows
# typed, and the prompt says what each column means, never what JSON is.
table_request() {
  local columns="$1" semantics="$2" task="$3" data="$4" schema="$5"
  jq -n \
    --arg model  "$MODEL" \
    --arg user   "Columns: $columns
Column semantics:
$semantics

Task: $task

$data" \
    --argjson schema "$schema" \
    '{model: $model, max_tokens: 4096,
      system: "You are a data analyst.",
      output_config: {format: {type: "json_schema", schema: $schema}},
      messages: [{role: "user", content: $user}]}'
}

# capture_table <columns_json> <column_semantics> <task> <data> <table> <reply_schema> → prints {columns, rows} JSON
# column_semantics: one line per column — "name: what it means". The reply is kept beside the
# run's record, <stamp>.<table>.reply.json, since a paid call is not repeated for free.
capture_table() {
  local columns="$1" semantics="$2" task="$3" data="$4" table="$5" schema="$6"
  local request response kept
  request="$(table_request "$columns" "$semantics" "$task" "$data" "$schema")"
  # the key rides a file descriptor and the request stdin, so that the narrated command names
  # neither the secret nor the corpus; a reading takes longer than a probe, so its bound is
  # ten minutes unless the reader names another
  response="$(printf '%s' "$request" | CORPUS_YOGA_SEND_TIMEOUT="${CORPUS_YOGA_SEND_TIMEOUT:-600}" send quote messages \
    -H @<(printf 'x-api-key: %s\n' "$ANTHROPIC_API_KEY") \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d @-)"
  kept="$LOGS_DIR/indexing/capture/$(stamp_of indexing capture).$table.reply.json"
  mkdir -p "${kept%/*}"
  printf '%s\n' "$response" > "$kept"
  # A reading cut off at the token ceiling is not a short reading, it is an incomplete one,
  # and the text may still parse. Ask the response why it stopped rather than inferring it
  # from the rows that arrived (L8: failure surfaces; never fabricate where the honest state
  # is "unknown").
  local stop; stop="$(jq -r '.stop_reason // "unknown"' <<< "$response")"
  if [[ "$stop" != "end_turn" ]]; then
    echo "corpus-yoga indexing capture: the model stopped with stop_reason=$stop (not end_turn) — " \
         "the reading is incomplete and is NOT deposited" >&2
    return 1
  fi
  local text
  text="$(jq -r '[.content[]? | select(.type == "text") | .text] | join("")' <<< "$response")"   # the text blocks, wherever they stand
  if [[ -z "$text" ]]; then
    echo "corpus-yoga indexing capture: $(phrase "the {table} reply holds no text block - its blocks are {blocks}; the reply is kept at {kept}" \
      table="$table" blocks="$(jq -r '[.content[]?.type] | join(", ")' <<< "$response")" kept="${kept#"$REPO_DIR/"}")" >&2
    return 1
  fi
  # the reply is the table's rows as objects, typed by the shape sent; the table stores them as arrays
  printf '%s\n' "$text" | "$REPO_DIR/src/run_python_script.sh" "$REPLY_SHAPE_SCRIPT" table "$columns"
}

# ── per-table capture functions ───────────────────────────────────────────────

# The canonical category names — AUTHORED, not captured: read from the palette
# inlined in the homepage template (rsc/site/index.template.html), the one authority. Exits
# non-zero (not AttributeError) if the block can't be found, so a template reformat
# fails loudly; the caller pre-flights this before any paid call.
canonical_categories() {
  "$REPO_DIR/src/run_python_script.sh" -c "
import re, json, pathlib, sys
h = pathlib.Path('$REPO_DIR/rsc/site/index.template.html').read_text()
m = re.search(r'id=\"data-categories\"[^>]*>\s*(\{.*?\})\s*</script>', h, re.S)
if not m:
    sys.exit('canonical_categories: no data-categories palette block in rsc/site/index.template.html')
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
  local conv="$1" chats="$2" categories="$3" out_file="$4" text
  # asked for otherwise than stored: a conversation by its number in the list, rekeyed to its id
  # below, and a category from the authored palette, so none outside it can come back
  local shape
  shape="$("$REPO_DIR/src/run_python_script.sh" "$REPLY_SHAPE_SCRIPT" schema chatCategories '["chat", "category"]' \
    'chat={"type": "integer", "description": "the number of the conversation in the list"}' \
    "category=$(jq -nc --arg names "$categories" '{type: "string", enum: ($names | split(", "))}')")" || return 1
  text="$(capture_table \
    '["chat", "category"]' \
    'chat: integer index of the conversation (from the list below)
category: one of the provided category names' \
    "Assign each conversation to exactly one of these categories: $categories" \
    "Conversations:
$chats" chat-categories "$shape")" || return 1
  printf '%s\n' "$text" \
    | "$REPO_DIR/src/run_python_script.sh" "$MAIN_DIR/rekey_chats.py" --to-id --conversations "$conv" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# capture_concepts_to <chat_list> <out_file> — the weighted concept table, each
# concept tagged with the provider(s) it is salient in (from the chat list's [source]
# markers) — the dimension behind the dashboard's provider toggle (schema v2)
capture_concepts_to() {
  local chats="$1" out_file="$2" text shape
  shape="$("$REPO_DIR/src/run_python_script.sh" "$REPLY_SHAPE_SCRIPT" schema semanticConcepts '["word", "count", "provider"]')" || return 1
  text="$(capture_table \
    '["word", "count", "provider"]' \
    'word: key concept or theme (word or short phrase)
count: salience weight (not raw frequency); scale so the top concept = 100
provider: which provider the concept is salient in — "claude", "gemini", or "both", from the [source] markers in the conversation list (a list without markers is all claude)' \
    'Generate a weighted list of 20-50 key concepts and themes across all conversations, tagging each concept with the provider(s) whose conversations it is salient in.' \
    "Conversations:
$chats" semantic-concepts "$shape")" || return 1
  printf '%s\n' "$text" \
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_file"
}

# validate_capture <staged-file> <schema-family> — the staged capture must validate
# against the LATEST rsc/schema/indexing/<family> version before promotion
# (validate.py, in-memory — the markdownConversation no-matrix precedent: captures
# validate at write time, no per-datum logs). This retired the hand-written shape
# jq: the shape contract now lives in the schema system like every other data
# class. The palette join (category ∈ authored names) is a cross-file constraint
# beyond JSON Schema and stays checked separately below.
validate_capture() {
  local file="$1" family="$2" schema verdict
  schema="$(printf '%s\n' "$REPO_DIR/rsc/schema/indexing/$family"/v*.json | sort -V | tail -1)"
  verdict="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate.py" "$file" "$schema")"
  [[ "$verdict" == 'Valid!' ]] || {
    printf '%s\n' "$verdict" >&2
    effect "$(act indexing capture): NOT DONE - $(phrase "the reading fails {family} {version} at {fault}; staged in {stage}, not deposited" \
      family="$family" version="$(basename "$schema" .json)" \
      fault="$("$REPO_DIR/src/run_python_script.sh" "$REPLY_SHAPE_SCRIPT" fault "$file" "$schema")" stage="cache/indexing")"
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
# coverage_of <conversations-dir> <inferred-chat-categories.json> → "captured never-captured gone total"
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
from markdown_projection import corpus_index
corpus = {cid for _, _, _, cid in corpus_index('$conv')}
captured = ({r[0] for r in json.load(open('$cat')).get('rows', [])}
            if os.path.isfile('$cat') else set())
print(len(corpus & captured), len(corpus - captured), len(captured - corpus), len(corpus))
"
}

# The LEADING extent, and the intent: what is, and what this capture will do to it.
# Formatted from coverage_of, never re-derived — two joins that could disagree about the
# same corpus is the defect pull/55 fixed one layer up.
coverage_report() {
  local conv="$1" out captured never gone total
  out="$(coverage_of "$conv" "$DATA_DIR/output/indexing/inferred-chat-categories.json")" || return 0
  read -r captured never gone total <<< "$out"
  if [[ -f "$DATA_DIR/output/indexing/inferred-chat-categories.json" ]]; then
    echo "coverage (exact): $captured captured · $never never captured · $gone captured-but-gone"
  else
    echo "coverage (exact): no prior capture — $never conversation(s) uncovered"
  fi
  echo "intent: re-read all $total conversation(s)"
}


# ── the paid capture (corpus-yoga indexing capture) ─────────────────────────────────
# Both PAID model readings the dashboard shows, single-source and durable: the
# weighted concept list (word cloud) and the chat→category assignment. Run once
# over the corpus; both machines share the result.
#
# capture is DERIVE-then-DEPOSIT: both readings are captured into cache/indexing
# (the workshop, git-ignored, corpus-scoped like cache/indexing) and validated there, then
# deposited together, under the act's stamp, in data/output/indexing/capture/<stamp>/, only once
# both succeed (issues/1185). A failed or malformed capture — bad key, 529, non-JSON, empty
# rows — deposits nothing; set -e aborts before the deposit. Nothing a capture does changes the
# capture in use: corpus-yoga indexing adopt does.
# capture_dashboard <conversations_json> <only> — <only> is "" (both),
# "semantic-concepts", or "chat-categories". Whatever is requested is captured and
# validated in cache/ FIRST, then all of it deposited — so a deposit never holds
# one table of a capture whose second failed.
capture_dashboard() {
  local conv="$1" only="${2:-}"
  # corpus-scoped staging (like cache/indexing): the capture is a reading of the
  # whole corpus, tied to no batch
  local stage="$CACHE_ROOT/indexing"
  local dest="$DATA_DIR/output/indexing"
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

  echo "capturing the index tables from ${conv#"$REPO_DIR/"}${only:+ (--only $only)} → cache/indexing (deposited in data/output/indexing/capture/ on success)"
  if [[ "$want_concepts" == 1 ]]; then
    capture_concepts_to "$chats" "$stage/inferred-semantic-concepts.json" \
      || { effect "$(act indexing capture): NOT DONE - $(phrase "the {table} reading is not written; the line above says why, and nothing is deposited" table=semantic-concepts)"; exit 1; }
    validate_capture "$stage/inferred-semantic-concepts.json" semanticConcepts
    echo "  ✓ inferred-semantic-concepts.json ($(jq '.rows | length' "$stage/inferred-semantic-concepts.json") concepts)"
    # What the call bought, judged now (issues/644): the index's own scan says which concepts
    # anchor in a conversation turn and by which phrasings; the rest are named here, the
    # one place their spend is visible, and never reach the index.
    "$REPO_DIR/src/run_python_script.sh" -c 'import sys; from pathlib import Path; import indexing; indexing.anchor_report(Path(sys.argv[1]), Path(sys.argv[2]))' "$stage/inferred-semantic-concepts.json" "$conv"
  fi
  if [[ "$want_categories" == 1 ]]; then
    capture_chat_categories "$conv" "$chats" "$categories" "$stage/inferred-chat-categories.json" \
      || { effect "$(act indexing capture): NOT DONE - $(phrase "the {table} reading is not written; the line above says why, and nothing is deposited" table=chat-categories)"; exit 1; }
    validate_capture "$stage/inferred-chat-categories.json" chatCategories
    # Every assigned category MUST be an authored palette name, else present.sh's hue
    # lookup misses and those chats render uncoloured — the join's real dependency, which
    # a columns/rows shape-check alone would not catch (a model 'science'/'math' passes).
    local off
    off="$(jq -r --arg pal "$categories" '
      ($pal | split(", ")) as $ok
      | [.rows[][1]] | unique | map(select(. as $c | ($ok | index($c)) == null)) | join(", ")
    ' "$stage/inferred-chat-categories.json")"
    [[ -z "$off" ]] || { echo "corpus-yoga indexing capture: chat-categories assigns off-palette categories ($off) — not deposited. Palette: $categories" >&2; exit 1; }
    # The TRAILING extent (G19): the same exact join taken of the staged file, so it can be
    # compared with the leading one. A row count cannot do this job — it counted 125 while
    # the corpus held 137 and printed a ✓ beside it.
    local after captured never gone total
    if after="$(coverage_of "$conv" "$stage/inferred-chat-categories.json")"; then
      read -r captured never gone total <<< "$after"
      echo "  ✓ inferred-chat-categories.json — coverage (exact): $captured of $total captured" \
           "· $never never captured · $gone captured-but-gone"
      # Intent was "re-read all $total". Unmet intent is the thing to say out loud; a
      # capture that covers LESS than the durable one it would replace is not a new
      # record, it is a failed re-read, and promoting it would lose coverage that was
      # paid for once already.
      if [[ "$never" -gt 0 ]]; then
        echo "  ⚠ intent unmet: the capture re-read $total conversation(s) and returned" \
             "$captured — $never uncovered"
        local before_captured=0 b
        if b="$(coverage_of "$conv" "$dest/inferred-chat-categories.json")"; then
          read -r before_captured _ _ _ <<< "$b"
        fi
        if [[ "$captured" -lt "$before_captured" ]]; then
          echo "  ⚠ coverage $captured, where the capture in use covers $before_captured - deposited all the same; adopting it is the reader's choice"
        fi
      fi
    else
      echo "  ✓ inferred-chat-categories.json ($(jq '.rows | length' "$stage/inferred-chat-categories.json") assignments)" \
           "— coverage not computable (no corpus index for this source)"
    fi
  fi

  # deposited beside every earlier capture, under this act's stamp, the capture in use left as it
  # stands (issues/1185): corpus-yoga indexing adopt makes it the one in use
  local names=() deposited
  [[ "$want_concepts"   == 1 ]] && names+=(inferred-semantic-concepts.json)
  [[ "$want_categories" == 1 ]] && names+=(inferred-chat-categories.json)
  deposited="$("$REPO_DIR/src/run_python_script.sh" -c 'import sys; from pathlib import Path; import indexing; print(indexing.deposit(Path(sys.argv[1]), sys.argv[2], sys.argv[3:]))' \
    "$stage" "$(stamp_of indexing capture)" "${names[@]}")"
  effect "$(act indexing capture): DONE - deposited in ${deposited#"$REPO_DIR/"}; the capture in use stands until corpus-yoga indexing adopt names this one"
}

# ── the capture source ────────────────────────────────────────────────────────
# The corpus itself: data/output/markdown/claude/chat/conversations — the projected
# markdownConversation corpus, source-agnostic by construction (whatever projects
# into it — captures today, gemini tomorrow — is what the model reads), and the
# very thing the captured tables describe. Its filenames carry ordered()'s canonical
# numbering and its frontmatter the uuids, so the chat list and the rekey map read
# straight off the OUTPUT layer: no batch selection, no atomise-first coupling —
# capture works the moment the corpus exists. Reading from a batch's cache, or from
# an input file, couples the dashboard to a layer above the output it describes.
corpus_conversations() {
  local d="$DATA_DIR/output/markdown"
  has_conversations "$d" && echo "$d"
}

capture() {
  parse_argv indexing capture "$@"
  local conversations="" only=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversations) conversations="$2"; shift 2 ;;
      --only)          only="$2";          shift 2 ;;
      *) echo "corpus-yoga indexing capture: unknown argument: $1" >&2; exit 1 ;;
    esac
  done
  case "$only" in
    ''|semantic-concepts|chat-categories) ;;
    *) echo "corpus-yoga indexing capture --only: expected 'semantic-concepts' or 'chat-categories', got '$only'" >&2; exit 1 ;;
  esac
  # The PAID send is the work, so refusal is loud and OUTRANKS the key check (a refused
  # machine's missing key is irrelevant).
  send_cleared messages || exit 1
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] || { echo "error: ANTHROPIC_API_KEY is not set" >&2; exit 1; }
  # The one command that spends money: a paid call is not reproducible for free, so its
  # record is the evidence. The record is the launcher's tee of the whole verb (issues/708),
  # logs/indexing/capture/<stamp>.log, header included - nothing is written here.
  local conv
  conv="${conversations:-$(corpus_conversations || true)}"
  [[ -n "$conv" && -e "$conv" ]] || { effect "$(act indexing capture): NOT DONE - no conversation markdown under data/output/markdown (looked for $CONVERSATIONS_GLOB at any depth); corpus-yoga pipeline collate projects it, or --conversations names a markdown corpus dir, a json/ dir or a conversations.json" "corpus-yoga pipeline collate" "projects the corpus"; exit 1; }
  echo "model: $MODEL · source: ${conv#"$REPO_DIR/"}${only:+ · --only $only}"
  coverage_report "$conv"
  capture_dashboard "$conv" "$only"
}

main() {
  capture "$@"
}

# run, the capture; loaded, its functions alone - so that a check can exercise them without a capture
[[ "${BASH_SOURCE[0]}" != "$0" ]] || main "$@"
