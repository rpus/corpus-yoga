#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/infer_tables.sh --data-dir ../data-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/infer_tables.sh --data-root ../data-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen"
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-4-6}"
API_URL="https://api.anthropic.com/v1/messages"
FORMAT_TABLE_SCRIPT="$SCRIPT_DIR/format_table.py"

# ── helpers ───────────────────────────────────────────────────────────────────

# chat_list <conversations_json> → numbered "N: name" lines
chat_list() {
  jq -r '[sort_by(.created_at) | to_entries[] | "\(.key): \(.value.name)"] | join("\n")' "$1"
}

# infer_table <columns_json> <column_semantics> <task> <data> → prints {columns, rows} JSON
# column_semantics: one line per column — "name: what it means"
infer_table() {
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
    '{model: $model, max_tokens: 1024,
      system: "You are a data analyst. Return only valid JSON.",
      messages: [{role: "user", content: $user}]}')"
  response="$(curl -sf "$API_URL" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$request")"
  jq -r '.content[0].text' <<< "$response"
}

# ── per-table inference functions ─────────────────────────────────────────────

# infer_categories <conversations_json> <out_dir>
infer_categories() {
  local conv="$1" out_dir="$2"
  infer_table \
    '["category", "hue"]' \
    'category: short lowercase semantic topic label
hue: HSV hue in degrees (0-360), perceptually distinct across categories' \
    'Propose 6-10 semantic categories that cover the conversations well.' \
    "Conversations:
$(chat_list "$conv")" \
    | python "$FORMAT_TABLE_SCRIPT" \
    > "$out_dir/data-categories.json"
  echo "  ✓ data-categories"
}

# infer_chat_categories <conversations_json> <out_dir>
# Requires: data-categories.json already present in <out_dir>
infer_chat_categories() {
  local conv="$1" out_dir="$2"
  local categories
  categories="$(jq -r '[.rows[] | .[0]] | join(", ")' "$out_dir/data-categories.json")"
  infer_table \
    '["chat", "category"]' \
    'chat: integer index of the conversation (from the list below)
category: one of the provided category names' \
    "Assign each conversation to exactly one of these categories: $categories" \
    "Conversations:
$(chat_list "$conv")" \
    | python "$FORMAT_TABLE_SCRIPT" \
    > "$out_dir/data-chat-categories.json"
  echo "  ✓ data-chat-categories"
}

# infer_semantic <conversations_json> <out_dir>
infer_semantic() {
  local conv="$1" out_dir="$2"
  infer_table \
    '["word", "count"]' \
    'word: key concept or theme (word or short phrase)
count: salience weight (not raw frequency); scale so the top concept = 100' \
    'Generate a weighted list of 20-50 key concepts and themes across all conversations.' \
    "Conversations:
$(chat_list "$conv")" \
    | python "$FORMAT_TABLE_SCRIPT" \
    > "$out_dir/data-semantic.json"
  echo "  ✓ data-semantic"
}

# ── per-export logic ──────────────────────────────────────────────────────────

infer_export() {
  local data_dir="${1%/}"
  local name; name="$(basename "$data_dir")"
  local out_dir="$OUTPUT_DIR/$name/inferred"
  local conv="$data_dir/conversations.json"

  echo "── $name"
  rm -rf "$out_dir"
  mkdir -p "$out_dir"

  {
    infer_categories      "$conv" "$out_dir"
    infer_chat_categories "$conv" "$out_dir"
    infer_semantic        "$conv" "$out_dir"
    echo "→ $out_dir"
  } > "$out_dir/infer.log" 2>&1
}

# ── entry point ───────────────────────────────────────────────────────────────

main() {
  local data_dir="" data_root=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --data-dir)  data_dir="$2";  shift 2 ;;
      --data-root) data_root="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --data-dir <path> | --data-root <path>"
         exit 1 ;;
    esac
  done

  if [[ -z "$data_dir" && -z "$data_root" ]]; then
    echo "Usage: $0 --data-dir <path/to/data-directory>"
    echo "       $0 --data-root <path/to/data-exports>"
    exit 1
  fi

  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "Error: ANTHROPIC_API_KEY is not set"
    exit 1
  fi

  # shellcheck source=/dev/null
  source ~/venvs/general/bin/activate

  if [[ -n "$data_dir" ]]; then
    infer_export "$(cd "$data_dir" && pwd)"
  else
    for d in "$(cd "$data_root" && pwd)"/data-*/; do
      infer_export "$d"
    done
  fi

  deactivate
}

main "$@"
