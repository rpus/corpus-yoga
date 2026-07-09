#!/usr/bin/env bash
# RUNME.sh — Process all Claude data exports.
#
# Runs three pipelines against their sibling input directories:
#
#   chat-exports     ext/chat-exports/      claude.ai bulk exports, conversations.json etc. (you unzip downloads here)
#   code-projects    ext/code-projects/     Claude Code CLI sessions (symlinked to ~/.claude/projects/ by its PREP.sh)
#   browser-captures ext/browser-captures/  Per-conversation captures (written by --capture-from-browser):
#                                           claude/ live API JSON (validated + projected to markdown);
#                                           gemini/ DOM-scraped markdown (terminal artifact — no API, nothing to validate)
#
# Any ext/ entry may instead be a hand-made symlink, to keep the data outside the clone.
#
# Each pipeline validates its inputs against all schema versions, then (for chat-exports)
# extracts files and renders a dashboard (reading the durable lib/dashboard/ captures).
#
# Usage:
#   ./RUNME.sh                                      # all pipelines (claude api, gemini dom)
#   ./RUNME.sh --plan                               # print the ordered step plan; run nothing
#   ./RUNME.sh --capture-from-browser               # also capture/update via Safari (slow)
#   ./RUNME.sh --capture-from-browser --new-claude-scrape  # also DOM-scrape claude + check projection vs scrape
#
# After running, check results with:
#   src/test/pre_commit.sh            # full check suite; read via: git diff --cached src/test/pre_commit.log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  browser_captures=""
  new_claude_scrape=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --capture-from-browser) browser_captures="1";                   shift ;;
      --new-claude-scrape) new_claude_scrape="--new-claude-scrape";               shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 [--capture-from-browser] [--new-claude-scrape]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

require_cmd() {
  local cmd="$1" hint="$2"
  if ! command -v "$cmd" &>/dev/null; then
    echo "error: $cmd not found — $hint" >&2
    exit 1
  fi
}

find_python3() {
  if command -v python3 &>/dev/null; then
    echo "python3"; return 0
  fi
  if command -v python &>/dev/null; then
    if python --version 2>&1 | grep -q "^Python 3"; then
      echo "python"; return 0
    fi
  fi
  echo "error: Python 3 not found — install via: brew install python" >&2
  return 1
}

ensure_venv() {
  local python="$1"
  if [[ ! -f "$VENV/bin/activate" ]]; then
    echo "creating venv at $VENV"
    "$python" -m venv "$VENV"
  fi
}

install_deps() {
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  echo "checking for pip upgrade"
  pip install --upgrade pip
  pip install -q -r "$SCRIPT_DIR/src/requirements.txt"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ────────────────────────────────────────────────────────────"
  local rc=0
  "$SCRIPT_DIR/src/main/${name}/PREP.sh" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  local rc=0
  "$SCRIPT_DIR/src/main/$name/RUNME.sh" "--${name}" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline_safe() {
  local name="$1"; shift
  if ! run_pipeline "$name" "$@"; then
    pipeline_failures+=("$name")
  fi
}

# The error:/FAIL: lines from one failed pipeline's section of the log — so the
# tail can QUOTE the failure, not send the reader scrolling. Sections are
# delimited by the "── <name> ─…" headers prep_pipeline/run_pipeline print;
# by tail time those lines are long flushed through the tee.
section_error_lines() {
  local label="$1" header
  case "$label" in
    *" (prep)") header="── prep: ${label% (prep)} " ;;
    *)          header="── ${label} " ;;
  esac
  awk -v h="$header" '
    index($0, "── ") == 1 { insec = (index($0, h) == 1) }
    insec && /^[[:space:]]*(error:|FAIL:)/ { sub(/^[[:space:]]*/, ""); print }
  ' "$LOG_FILE"
}

prep_pipeline_safe() {
  local name="$1"; shift
  if ! prep_pipeline "$name" "$@"; then
    pipeline_failures+=("$name (prep)")
  fi
}

LOG_FILE="$SCRIPT_DIR/logs/RUNME/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"

# The pipelines' own --plan output is the one authority on their step order
# (each prints exactly the step list it executes — see src/main/steps.sh);
# only this script's own frame (tooling, preps, tail) is narrated here, beside
# the main() that performs it.
print_plan() {
  echo "RUNME.sh — the ordered plan (conditional steps annotated; nothing executed):"
  echo "  tooling: require jq; find python3; create venv at \$VENV if absent; pip install src/requirements.txt"
  echo "  browser-captures/PREP.sh (only with --capture-from-browser: Safari capture/update sweep)"
  "$SCRIPT_DIR/src/main/browser-captures/RUNME.sh" --plan | sed 's/^/  /'
  echo "  chat-exports/PREP.sh"
  "$SCRIPT_DIR/src/main/chat-exports/RUNME.sh" --plan | sed 's/^/  /'
  echo "  code-projects/PREP.sh"
  "$SCRIPT_DIR/src/main/code-projects/RUNME.sh" --plan | sed 's/^/  /'
  echo "  tail: FAIL/WARN counts; failed pipelines with their error:/FAIL: lines quoted; gather '→ run:' suggestions; pre_commit reminder; log path"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") $* — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  local -a pipeline_failures=()

  [[ -n "$browser_captures" ]] && prep_pipeline_safe browser-captures ${new_claude_scrape:+"$new_claude_scrape"}
  run_pipeline_safe  browser-captures "$SCRIPT_DIR/ext/browser-captures/claude" ${new_claude_scrape:+"$new_claude_scrape"}

  prep_pipeline_safe chat-exports
  run_pipeline_safe  chat-exports "$SCRIPT_DIR/ext/chat-exports"

  prep_pipeline_safe code-projects
  run_pipeline_safe  code-projects "$SCRIPT_DIR/ext/code-projects"

  echo "── done $(date -u '+%Y-%m-%dT%H:%M:%SZ') ───────────────────────────────────────────"
  # The tail carries SUMMARIES only — the body already marks each fact at its
  # source (FAIL: something that needs acting on, remedy beside it; WARN: a
  # fact worth eyes that gates nothing) and is grep-able by those sigils. Here:
  # the verdict: line(s) (one-line computed conclusions), the "→ run:"
  # suggested commands, the FAIL/WARN counts, and — when a pipeline died — its
  # error:/FAIL: lines quoted under its name (section_error_lines), so a failure
  # is summarised in the tail exactly as a warning is, never just "scroll up".
  # The log is safe to read mid-tee: those lines are long flushed.
  local n_fail n_warn verdicts suggestions
  n_fail="$(grep -cE '^[[:space:]]*FAIL:' "$LOG_FILE" 2>/dev/null || true)"
  n_warn="$(grep -cE '^[[:space:]]*WARN:' "$LOG_FILE" 2>/dev/null || true)"
  verdicts="$(grep -E '^verdict:' "$LOG_FILE" 2>/dev/null | sort -u)" || true
  suggestions="$(grep -F '→ run:' "$LOG_FILE" 2>/dev/null | sed 's/^.*→ run: /  /' | sort -u)" || true
  [[ -n "$verdicts" ]] && printf '%s\n' "$verdicts"
  if [[ -n "$suggestions" ]]; then
    echo "Suggested commands (context beside each '→ run:' line above):"
    printf '%s\n' "$suggestions"
  fi
  if [[ ${#pipeline_failures[@]} -eq 0 ]]; then
    if [[ "$n_fail" -gt 0 || "$n_warn" -gt 0 ]]; then
      echo "All pipelines completed; $n_fail FAIL, $n_warn WARN — marked FAIL:/WARN: in the body above."
    else
      echo "All pipelines completed successfully."
    fi
  else
    # FAIL summarises like WARN even when a pipeline died — the counts do not
    # vanish on the runs that need them most.
    [[ "$n_fail" -gt 0 || "$n_warn" -gt 0 ]] && \
      echo "$n_fail FAIL, $n_warn WARN — marked FAIL:/WARN: in the body above."
    echo "Failed pipelines:"
    local errs
    for f in "${pipeline_failures[@]}"; do
      echo "  $f"
      errs="$(section_error_lines "$f")"
      [[ -n "$errs" ]] && printf '%s\n' "$errs" | sed 's/^/    /'
      case "$f" in
        "browser-captures (prep)") echo "    → check ext/browser-captures/claude/ and Safari setup" ;;
        "chat-exports (prep)")   echo "    → populate ext/chat-exports/ with a bulk export (see PREP.sh --help)" ;;
        "code-projects (prep)")  echo "    → check ext/code-projects/ symlink setup" ;;
        *) [[ -z "$errs" ]] && echo "    → scroll up: the failing step prints its error and the path of its own log" ;;
      esac
    done
  fi
  echo "Run src/test/pre_commit.sh, then: git diff --cached src/test/pre_commit.log"
  echo "Log: $LOG_FILE"
}

# --plan runs before the log exists: it writes nothing, not even a log file.
for _arg in "$@"; do
  if [[ "$_arg" == "--plan" ]]; then print_plan; exit 0; fi
done
mkdir -p "$(dirname "$LOG_FILE")"
main "$@" 2>&1 | tee "$LOG_FILE"
