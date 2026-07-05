#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/chat-exports/present.sh --chat-export ext/chat-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/chat-exports/present.sh --chat-exports ext/chat-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"
TEMPLATE="$REPO_DIR/rsc/index.html"
WORD_FREQ_SCRIPT="$SCRIPT_DIR/word_freq_literal.py"
FORMAT_TABLE_SCRIPT="$SCRIPT_DIR/format_table.py"
TIMELINE_SCRIPT="$SCRIPT_DIR/timeline.py"
CHECK_HARVESTED_SCRIPT="$SCRIPT_DIR/check_harvested.py"
FILES_FROM_DOWNLOADED_SCRIPT="$SCRIPT_DIR/files_from_downloaded.py"
DOWNLOADED_DIR="$REPO_DIR/lib/artifacts/downloaded"

# ── jq snippets ───────────────────────────────────────────────────────────────

# The conversation-keyed tables (data-chats, data-spans, data-local-resources) and the inference
# chat list all come from timeline.py, which derives `chat` from the one canonical ordering in
# markdown_projection.ordered() (created_at order, 1-based). present.sh only orchestrates and
# columnarises; the ordering/numbering lives in one place, shared with the atomised json/ names.
timeline() { "$REPO_DIR/src/run_python_script.sh" "$TIMELINE_SCRIPT" "$1" --table "$2"; }

# Tooltip: files sourced from lib/artifacts/downloaded/ — pre-curated and
# path-consistent. local_resource paths (what Claude reported) are unreliable.
# The library is uuid8-keyed (identity); data-chats.json ($1) supplies the
# uuid → current-ordinal join for this batch's presentation.
files_from_downloaded() {
  "$REPO_DIR/src/run_python_script.sh" "$FILES_FROM_DOWNLOADED_SCRIPT" "$DOWNLOADED_DIR" "$1"
}

jq_literal() { jq '{
  human:     {columns: ["word","count"], rows: [.human[]     | [.word,.count]]},
  assistant: {columns: ["word","count"], rows: [.assistant[] | [.word,.count]]},
  both:      {columns: ["word","count"], rows: [.both[]      | [.word,.count]]}
}'; }

# ── helpers ───────────────────────────────────────────────────────────────────

# format_table: reads JSON from stdin, writes aligned table JSON to stdout.
format_table() {
  local tmp
  tmp=$(mktemp)
  cat > "$tmp"
  "$REPO_DIR/src/run_python_script.sh" "$FORMAT_TABLE_SCRIPT" "$tmp"
  rm -f "$tmp"
}

# inject <html_file> <key> <json>
# Replaces the inlined JSON block for <key> in the HTML file.
# Looks for <!-- key.json:begin/end --> markers first; falls back to matching
# the <script id="key"> tag directly (for sections without markers).
inject() {
  local file="$1" key="$2" json="$3"
  local tmp
  tmp=$(mktemp)
  printf '%s' "$json" > "$tmp"
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/inject.py" "$file" "$key" "$tmp"
  rm -f "$tmp"
}

# update_export_tooltip <html_file> <export_name>
update_export_tooltip() {
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/update_export_tooltip.py" "$1" "$2"
}

# update_title <html_file> <conversations_json>
update_title() {
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/update_title.py" "$1" "$2"
}

# ── per-export logic ──────────────────────────────────────────────────────────

present_export() {
  local chat_export="${1%/}"
  local name
  name="$(basename "$chat_export")"
  local out_dir="$OUTPUT_DIR/$name/presentation"
  local inferred_dir="$OUTPUT_DIR/$name/inferred"
  local conv="$chat_export/conversations.json"
  local out="$out_dir/index.html"

  rm -rf "$out_dir"
  mkdir -p "$out_dir"

  {
    cp "$TEMPLATE" "$out"

    local json

    # data-chats
    json="$(timeline "$conv" chats | format_table)"
    inject "$out" "data-chats" "$json"
    printf '%s\n' "$json" > "$out_dir/data-chats.json"
    echo "  ✓ data-chats"

    # data-spans: group consecutive same-chat messages into spans, then columnarise
    json="$(timeline "$conv" spans | format_table)"
    inject "$out" "data-spans" "$json"
    printf '%s\n' "$json" > "$out_dir/data-spans.json"
    echo "  ✓ data-spans"

    # data-files (tooltip): sourced from lib/artifacts/downloaded/
    json="$(files_from_downloaded "$out_dir/data-chats.json" | format_table)"
    inject "$out" "data-files" "$json"
    printf '%s\n' "$json" > "$out_dir/data-files.json"
    echo "  ✓ data-files"

    # data-local-resources: local_resource records from conversations.json,
    # with mime_type. Not in the tooltip; used by check_harvested for harvest
    # reporting and binary file classification.
    json="$(timeline "$conv" local-resources | format_table)"
    printf '%s\n' "$json" > "$out_dir/data-local-resources.json"
    "$REPO_DIR/src/run_python_script.sh" "$CHECK_HARVESTED_SCRIPT" "$name"

    # data-literal: word frequency (Python) then columnarise (jq)
    if [[ -f "$WORD_FREQ_SCRIPT" ]]; then
      json="$("$REPO_DIR/src/run_python_script.sh" "$WORD_FREQ_SCRIPT" "$conv" | jq_literal | format_table)"
      inject "$out" "data-literal" "$json"
      printf '%s\n' "$json" > "$out_dir/data-literal.json"
      echo "  ✓ data-literal"
    else
      echo "  ⚠ data-literal: $(basename "$WORD_FREQ_SCRIPT") not found — skipped"
    fi

    # claude-generated tables: use inferred data if available, else inject empty stub
    for key in data-categories data-chat-categories data-semantic; do
      local inferred_file="$inferred_dir/$key.json"
      local cols desc note
      case "$key" in
        data-categories)
          cols='["category", "hue"]'
          desc='Hue values in HSV degrees (0-360). Categories: mathematics(220), physics(180), philosophy(270), meta(40), tooling(25), creative(330), practical(90), social(0).'
          ;;
        data-chat-categories)
          cols='["chat", "category"]'
          desc='A join table assigning each chat to one category. Requires data-categories to be populated first. Stored uuid-keyed under inferred/ (identity survives corpus renumbering); the chat index here is re-derived at presentation time as the canonical 1-based ordinal (created_at order) from markdown_projection.ordered(), same as the timeline and the json/ filenames. Category assignment by Claude reading conversation summaries.'
          ;;
        data-semantic)
          cols='["word", "count"]'
          desc='Weights are inferred concept salience, not raw frequencies. To regenerate: extract summaries, paste to Claude, ask for weighted concept list.'
          ;;
      esac
      if [[ -f "$inferred_file" ]]; then
        # indicative — inference ran, so this table WAS generated
        note="Generated by Claude. $desc"
        if [[ "$key" == "data-chat-categories" ]]; then
          # durable storage speaks uuid; presentation re-derives the current ordinal
          json="$("$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/rekey_chats.py" \
                    --to-ordinal --conversations "$conv" < "$inferred_file" \
                  | jq --arg note "$note" '. + {note: $note}' | format_table)"
        else
          json="$(jq --arg note "$note" '. + {note: $note}' "$inferred_file" | format_table)"
        fi
        inject "$out" "$key" "$json"
        printf '%s\n' "$json" > "$out_dir/$key.json"
        echo "  ✓ $key (generated): $note"
      else
        # infinitive — inference was skipped, so this table is yet TO BE generated
        note="To be generated by Claude — run with --pay-for-inference. $desc"
        json="$(jq -n --argjson cols "$cols" --arg note "$note" \
          '{"columns": $cols, "rows": [], "note": $note}' | format_table)"
        inject "$out" "$key" "$json"
        printf '%s\n' "$json" > "$out_dir/$key.json"
        echo "  ○ $key (pending): $note"
      fi
    done

    update_title "$out" "$conv"
    update_export_tooltip "$out" "$name"
    echo "→ $out"
  } > "$out_dir/present.log" 2>&1
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
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$chat_export" ]]; then
    present_export "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      present_export "$d"
    done
  fi
}

main "$@"
