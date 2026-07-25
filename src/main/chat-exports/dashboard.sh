#!/usr/bin/env bash
# dashboard.sh (yoga dashboard) — the corpus dashboard: paid captures, free render.
#
# Usage:
#   yoga dashboard [status]     # what is captured + currency of render and captures (read-only, free)
#   yoga dashboard sync         # FREE: render data/output/dashboard/presentation/index.html (idempotent)
#                               #   from data/output/markdown + the durable captures
#   yoga dashboard capture      # PAID (needs ANTHROPIC_API_KEY): re-read the corpus
#     [--conversations <path>]  #   source override: markdown corpus dir | json/ dir | conversations.json
#     [--only semantic-concepts|chat-categories]   # refresh one file (default: both)
#
# Captures land durable in data/output/dashboard/ (shared across machines); the category
# palette is authored in rsc/site/index.html; the capture schemas live under
# rsc/schema/dashboard/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
API_URL="https://api.anthropic.com/v1/messages"
FORMAT_TABLE_SCRIPT="$SCRIPT_DIR/format_table.py"

# ── helpers ───────────────────────────────────────────────────────────────────

# The corpus's shape, stated ONCE: conversation markdown at any depth under a root.
# Three call sites used to each decide this for themselves and disagreed — status counted
# 137 conversations with `find -path`, chat_list matched two directory levels, and
# corpus_conversations matched one. The corpus is two deep
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
# of `run`) — so the run tail's hoisting carries them into every `yoga run`.
currency() {
  local corpus="$REPO_DIR/data/output/markdown"
  local render="$REPO_DIR/data/output/dashboard/presentation/index.html"
  local d="$REPO_DIR/data/output/dashboard"
  local n m=0 f render_state
  [[ -d "$corpus" ]] || return 0   # L8: no corpus yet — nothing to be current against
  n="$(count_conversations "$corpus")"
  [[ "$n" -gt 0 ]] || return 0
  [[ -f "$d/chat-categories.json" ]] && m="$(jq '.rows | length' "$d/chat-categories.json")"
  if [[ ! -f "$render" ]]; then
    render_state='absent'
  else
    # the render's inputs are the corpus AND the captures — either newer means behind
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
    echo "    → run: ./yoga dashboard sync   # FREE — re-render from the current corpus + captures"
  fi
  if [[ "$m" -lt "$n" ]]; then
    echo "INFO: the captures cover ~$m of $n conversation(s) — the paid layer lags the corpus; sync does NOT fix this:"
    echo "    → run: ./yoga dashboard capture   # PAID — the model re-reads the corpus"
  fi
}

# ── entry point ───────────────────────────────────────────────────────────────

# The corpus itself: data/output/markdown/claude/chat/conversations — the projected
# markdownConversation corpus, source-agnostic by construction (whatever projects
# into it — captures today, gemini tomorrow — is what the model reads), and the
# very thing the dashboard describes. Its filenames carry ordered()'s canonical
# numbering and its frontmatter the uuids, so the chat list and the rekey map read
# straight off the OUTPUT layer: no batch selection, no atomise-first coupling —
# capture works the moment the corpus exists. (Sourced from the frontier batch's
# tmp/cache/<batch>/json/ before 2026-07-10; from data/input/conversations.json before that —
# each move one layer further down the input→cache→output lifecycle.)
corpus_conversations() {
  local d="$REPO_DIR/data/output/markdown"
  has_conversations "$d" && echo "$d"
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
  [[ -f "$cat" && -d "$conv" ]] || return 1
  "$REPO_DIR/src/run_python_script.sh" -c "
import json, sys
sys.path.insert(0, '$REPO_DIR/src/main')
from markdown_projection import corpus_index
corpus = {cid for _, _, _, cid in corpus_index('$conv')}
captured = {r[0] for r in json.load(open('$cat')).get('rows', [])}
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
  echo "coverage (exact): $captured captured · $never never captured · $gone captured-but-gone"
  echo "intent: re-read all $total conversation(s)"
}

capture() {
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
# of `run`) — so the run tail's hoisting carries them into every `yoga run`.
currency() {
  local corpus="$REPO_DIR/data/output/markdown"
  local render="$REPO_DIR/data/output/dashboard/presentation/index.html"
  local d="$REPO_DIR/data/output/dashboard"
  local n m=0 f render_state
  [[ -d "$corpus" ]] || return 0   # L8: no corpus yet — nothing to be current against
  n="$(count_conversations "$corpus")"
  [[ "$n" -gt 0 ]] || return 0
  [[ -f "$d/chat-categories.json" ]] && m="$(jq '.rows | length' "$d/chat-categories.json")"
  if [[ ! -f "$render" ]]; then
    render_state='absent'
  else
    # the render's inputs are the corpus AND the captures — either newer means behind
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
    echo "    → run: ./yoga dashboard sync   # FREE — re-render from the current corpus + captures"
  fi
  if [[ "$m" -lt "$n" ]]; then
    echo "INFO: the captures cover ~$m of $n conversation(s) — the paid layer lags the corpus; sync does NOT fix this:"
    echo "    → run: ./yoga dashboard capture   # PAID — the model re-reads the corpus"
  fi
}

# ── entry point ───────────────────────────────────────────────────────────────

# The corpus itself: data/output/markdown/claude/chat/conversations — the projected
# markdownConversation corpus, source-agnostic by construction (whatever projects
# into it — captures today, gemini tomorrow — is what the model reads), and the
# very thing the dashboard describes. Its filenames carry ordered()'s canonical
# numbering and its frontmatter the uuids, so the chat list and the rekey map read
# straight off the OUTPUT layer: no batch selection, no atomise-first coupling —
# capture works the moment the corpus exists. (Sourced from the frontier batch's
# tmp/cache/<batch>/json/ before 2026-07-10; from data/input/conversations.json before that —
# each move one layer further down the input→cache→output lifecycle.)
corpus_conversations() {
  local d="$REPO_DIR/data/output/markdown"
  has_conversations "$d" && echo "$d"
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
  [[ -f "$cat" && -d "$conv" ]] || return 1
  "$REPO_DIR/src/run_python_script.sh" -c "
import json, sys
sys.path.insert(0, '$REPO_DIR/src/main')
from markdown_projection import corpus_index
corpus = {cid for _, _, _, cid in corpus_index('$conv')}
captured = {r[0] for r in json.load(open('$cat')).get('rows', [])}
print(len(corpus & captured), len(corpus - captured), len(captured - corpus), len(corpus))
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
  # The one command that spends money left no record of what it bought: terminal scrollback
  # was the whole audit trail. A paid call is not reproducible for free, so the log is not a
  # convenience here — it is the only evidence. Path per the command/verb rule (#54).
  local log="$REPO_DIR/tmp/logs/dashboard/capture/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"
  mkdir -p "$(dirname "$log")"
  exec > >(tee -a "$log") 2>&1
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local conv="${conversations:-$(corpus_conversations)}"
  [[ -n "$conv" && -e "$conv" ]] || { echo "error: no conversation markdown under data/output/markdown (looked for $CONVERSATIONS_GLOB at any depth) — project the corpus with \`yoga run\`, or pass --conversations <markdown corpus dir | json/ dir | conversations.json>" >&2; exit 1; }
  echo "model: $MODEL · source: ${conv#"$REPO_DIR/"}${only:+ · --only $only}"
  coverage_report "$conv"
  capture_dashboard "$conv" "$only"
}

main() {
  case "${1:-}" in
    capture)     shift; capture "$@" ;;
    sync)        shift; exec "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/present_corpus.py" "$@" ;;
    '')          status ;;   # bare noun → status; there is no `status` verb (this IS it)
    -h|--help)   awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "yoga dashboard: unknown verb '${1}' — expected 'capture' (paid), 'sync' (free render), or bare (status)" >&2; exit 1 ;;
  esac
}

main "$@"
