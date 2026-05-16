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
CHECK_HARVESTED_SCRIPT="$SCRIPT_DIR/check_harvested.py"
FILES_FROM_DOWNLOADED_SCRIPT="$SCRIPT_DIR/files_from_downloaded.py"
DOWNLOADED_DIR="$REPO_DIR/lib/artifacts/downloaded"

# ── jq snippets ───────────────────────────────────────────────────────────────

jq_chats() { jq '{
  columns: ["chat", "name", "dormant_from"],
  rows: [sort_by(.created_at) | to_entries[] | [.key, .value.name, (.value.updated_at | sub("\\.[0-9]+Z$"; "Z"))]]
}' "$@"; }

jq_spans() { jq '
  [sort_by(.created_at) | to_entries[] |
    .key as $i | .value.chat_messages[] |
    {chat: $i, from: (.created_at | sub("\\.[0-9]+Z$"; "Z")), to: (.created_at | sub("\\.[0-9]+Z$"; "Z")), messages: 1}
  ] | sort_by(.from) |
  reduce .[] as $m (
    {acc: [], cur: null};
    if .cur == null then
      {acc: .acc, cur: {chat: $m.chat, from: $m.from, to: $m.from, messages: 1}}
    elif .cur.chat == $m.chat then
      {acc: .acc, cur: (.cur + {to: $m.to, messages: (.cur.messages + 1)})}
    else
      {acc: (.acc + [.cur]), cur: {chat: $m.chat, from: $m.from, to: $m.from, messages: 1}}
    end
  ) | .acc + [.cur] |
  {
    columns: ["chat", "from", "to", "messages"],
    rows: [.[] | [.chat, .from, .to, .messages]]
  }
' "$@"; }

# Tooltip: files sourced from lib/artifacts/downloaded/ — pre-curated and
# path-consistent. local_resource paths (what Claude reported) are unreliable.
files_from_downloaded() {
  python "$FILES_FROM_DOWNLOADED_SCRIPT" "$DOWNLOADED_DIR"
}

# Harvest input: local_resource records from conversations.json with mime_type.
# Not used for the tooltip, but passed to check_harvested.py so it can classify
# binary files and report what was returned to the user but not yet extracted.
jq_local_resources() { jq '{
  columns: ["chat", "file", "mime_type"],
  rows: [
    (sort_by(.created_at) | to_entries[]) |
    .key as $i |
    .value.chat_messages[].content[] |
    select(.type == "tool_result") |
    .content[]? |
    select(.type == "local_resource") |
    [$i, (.file_path | ltrimstr("/mnt/user-data/outputs/")), .mime_type]
  ] | unique
}' "$@"; }

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
  python "$FORMAT_TABLE_SCRIPT" "$tmp"
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
  python - "$file" "$key" "$tmp" <<'PY'
import re, sys

path, key, json_path = sys.argv[1], sys.argv[2], sys.argv[3]
content = open(json_path).read()
html    = open(path).read()
begin   = f'  <!-- {key}.json:begin -->'
end     = f'  <!-- {key}.json:end -->'

if begin in html:
    def repl(m):
        return (f'  <!-- {key}.json:begin -->\n'
                f'  <script id="{key}" type="application/json">\n'
                + content +
                f'\n  </script>\n'
                f'  <!-- {key}.json:end -->')
    result = re.sub(re.escape(begin) + r'.*?' + re.escape(end), repl, html, flags=re.DOTALL)
else:
    pattern = r'(<script id="' + re.escape(key) + r'"[^>]*>).*?(</script>)'
    def repl(m):
        return m.group(1) + '\n' + content + '\n  ' + m.group(2)
    result = re.sub(pattern, repl, html, flags=re.DOTALL)

open(path, 'w').write(result)
PY
  rm -f "$tmp"
}

# update_export_tooltip <html_file> <export_name>
update_export_tooltip() {
  local file="$1" export_name="$2"
  python - "$file" "$export_name" <<'PY'
import re, sys
path, name = sys.argv[1], sys.argv[2]
html = open(path).read()
result = re.sub(
    r'(<h2\b[^>]*)>(Engagement timeline</h2>)',
    lambda m: f'{m.group(1)} title="{name}">{m.group(2)}',
    html
)
open(path, 'w').write(result)
PY
}

# update_title <html_file> <conversations_json>
update_title() {
  local file="$1" conv="$2"
  python - "$file" "$conv" <<'PY'
import json, re, sys
from datetime import datetime

path, conv_path = sys.argv[1], sys.argv[2]
with open(conv_path) as f:
    data = json.load(f)
dates = sorted(c['created_at'] for c in data)
t0, t1 = (datetime.fromisoformat(d.replace('Z', '+00:00')) for d in (dates[0], dates[-1]))
count  = len(data)
if t0.year == t1.year:
    date_range = (t0.strftime('%B %Y') if t0.month == t1.month
                  else f"{t0.strftime('%B')}–{t1.strftime('%B %Y')}")
else:
    date_range = f"{t0.strftime('%B %Y')}–{t1.strftime('%B %Y')}"
title  = f'Conversation corpus — {count} chats, {date_range}'
result = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', open(path).read())
open(path, 'w').write(result)
print(f'  title: {title}')
PY
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
    json="$(jq_chats "$conv" | format_table)"
    inject "$out" "data-chats" "$json"
    printf '%s\n' "$json" > "$out_dir/data-chats.json"
    echo "  ✓ data-chats"

    # data-spans: group consecutive same-chat messages into spans, then columnarise
    json="$(jq_spans "$conv" | format_table)"
    inject "$out" "data-spans" "$json"
    printf '%s\n' "$json" > "$out_dir/data-spans.json"
    echo "  ✓ data-spans"

    # data-files (tooltip): sourced from lib/artifacts/downloaded/
    json="$(files_from_downloaded | format_table)"
    inject "$out" "data-files" "$json"
    printf '%s\n' "$json" > "$out_dir/data-files.json"
    echo "  ✓ data-files"

    # data-local-resources: local_resource records from conversations.json,
    # with mime_type. Not in the tooltip; used by check_harvested for harvest
    # reporting and binary file classification.
    json="$(jq_local_resources "$conv" | format_table)"
    printf '%s\n' "$json" > "$out_dir/data-local-resources.json"
    python "$CHECK_HARVESTED_SCRIPT" "$name"

    # data-literal: word frequency (Python) then columnarise (jq)
    if [[ -f "$WORD_FREQ_SCRIPT" ]]; then
      json="$(python "$WORD_FREQ_SCRIPT" "$conv" | jq_literal | format_table)"
      inject "$out" "data-literal" "$json"
      printf '%s\n' "$json" > "$out_dir/data-literal.json"
      echo "  ✓ data-literal"
    else
      echo "  ⚠ data-literal: $(basename "$WORD_FREQ_SCRIPT") not found — skipped"
    fi

    # claude-generated tables: use inferred data if available, else inject empty stub
    for key in data-categories data-chat-categories data-semantic; do
      local inferred_file="$inferred_dir/$key.json"
      local cols note
      case "$key" in
        data-categories)
          cols='["category", "hue"]'
          note='Claude-generated. Hue values in HSV degrees (0-360). Categories: mathematics(220), physics(180), philosophy(270), meta(40), tooling(25), creative(330), practical(90), social(0).'
          ;;
        data-chat-categories)
          cols='["chat", "category"]'
          note='Claude-generated join table. Requires data-categories to be populated first. Chat index from: jq '"'"'[sort_by(.created_at) | to_entries[] | {chat: .key, name: .value.name}]'"'"' conversations.json. Category assignment by Claude reading conversation summaries.'
          ;;
        data-semantic)
          cols='["word", "count"]'
          note='Claude-generated from conversation summaries. Weights are inferred concept salience, not raw frequencies. To regenerate: extract summaries, paste to Claude, ask for weighted concept list.'
          ;;
      esac
      if [[ -f "$inferred_file" ]]; then
        json="$(jq --arg note "$note" '. + {note: $note}' "$inferred_file" | format_table)"
        inject "$out" "$key" "$json"
        printf '%s\n' "$json" > "$out_dir/$key.json"
        echo "  ✓ $key (inferred)"
      else
        json="$(jq -n --argjson cols "$cols" --arg note "$note" \
          '{"columns": $cols, "rows": [], "note": $note}' | format_table)"
        inject "$out" "$key" "$json"
        printf '%s\n' "$json" > "$out_dir/$key.json"
        echo "  ✓ $key (empty): $note"
      fi
    done

    update_title "$out" "$conv"
    update_export_tooltip "$out" "$name"
    echo "→ $out"
  } > "$out_dir/present.log" 2>&1
}

# ── entry point ───────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local chat_export="" chat_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)  chat_export="$2";  shift 2 ;;
      --chat-exports) chat_exports="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --chat-export <path> | --chat-exports <path>"
         echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/data-directory>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$REPO_DIR/src/activate_venv.sh"

  if [[ -n "$chat_export" ]]; then
    present_export "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      present_export "$d"
    done
  fi
}

main "$@"
