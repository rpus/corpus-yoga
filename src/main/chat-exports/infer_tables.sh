#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/chat-exports/infer_tables.sh --chat-export ext/chat-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/chat-exports/infer_tables.sh --chat-exports ext/chat-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"
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
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
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
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
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
    | "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" \
    > "$out_dir/data-semantic.json"
  echo "  ✓ data-semantic"
}

# ── per-export logic ──────────────────────────────────────────────────────────

infer_export() {
  local chat_export="${1%/}"
  local name; name="$(basename "$chat_export")"
  local out_dir="$OUTPUT_DIR/$name/inferred"
  local conv="$chat_export/conversations.json"

  rm -rf "$out_dir"
  mkdir -p "$out_dir"

  {
    echo "── $name"
    infer_categories      "$conv" "$out_dir"
    infer_chat_categories "$conv" "$out_dir"
    infer_semantic        "$conv" "$out_dir"
    echo "→ $out_dir"
  } > "$out_dir/infer.log" 2>&1
}

# ── entry point ───────────────────────────────────────────────────────────────

parse_args() {
  chat_export=""
  chat_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)  chat_export="$2";  shift 2 ;;
      --chat-exports) chat_exports="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path> | --chat-exports <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/data-directory>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo "Pass --help for more information."
    exit 1
  fi
  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "error: ANTHROPIC_API_KEY is not set"
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$chat_export" ]]; then
    infer_export "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      infer_export "$d"
    done
  fi
}

main "$@"
