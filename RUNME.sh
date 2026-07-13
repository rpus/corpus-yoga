#!/usr/bin/env bash
# RUNME.sh — Process all Claude data exports.
#
# Runs three pipelines against their sibling input directories:
#
#   chat-exports     input/chat-exports/      claude.ai bulk exports, conversations.json etc. (you unzip downloads here)
#   code-agents      input/code-agents/       Claude Code CLI sessions, from the repo-owned store (<room>/<project>/;
#                                           populated by `yoga agent capture --all` — the pipeline never reads
#                                           the harness-owned ~/.claude/projects)
#   browser-captures input/browser-captures/  Per-conversation captures (written by --capture-from-browser):
#                                           claude/ live API JSON (validated + projected to markdown);
#                                           gemini/ DOM-scraped markdown (terminal artifact — no API, nothing to validate)
#
# Any input/ entry may instead be a hand-made symlink, to keep the data outside the clone.
#
# Each pipeline validates its inputs against all schema versions, then (for chat-exports)
# extracts files and renders a dashboard (reading the durable output/dashboard/ captures).
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

# Every FAIL:/WARN:/INFO: ATOM, hoisted whole and GROUPED by severity — the
# FAIL group, then WARN, then INFO — with the original log-BODY ORDER preserved
# WITHIN each group. An atom is a reason line plus the "→ run:" command(s)
# directly beneath it, kept together (the body already pairs them; the tail must
# never tear them into a reason-list and a separate command-rail — a pile of
# buttons, pressed in some order, for reasons not stated). The grouping is safe
# and purely ADDITIVE: the body is the source of truth (full context, true step
# order), and messages are emitted in step order, so we rely on the script's step
# authorship for cross-message sanity — the tail only hoists and sorts by
# severity, destroying nothing. A reason with no command still shows; a "→ run:"
# joins the reason above it (in_atom), never a flat pile. Leading whitespace is
# normalised. (A FAIL in a pipeline that COMPLETED never enters
# section_error_lines — that quoting is keyed on death — so the tail hoists it here.)
hoist_atoms() {
  awk '
    /^[[:space:]]*FAIL:/ { s=$0; sub(/^[[:space:]]+/,"",s); fail=fail "  " s "\n"; b="F"; in_atom=1; next }
    /^[[:space:]]*WARN:/ { s=$0; sub(/^[[:space:]]+/,"",s); warn=warn "  " s "\n"; b="W"; in_atom=1; next }
    /^[[:space:]]*INFO:/ { s=$0; sub(/^[[:space:]]+/,"",s); info=info "  " s "\n"; b="I"; in_atom=1; next }
    /→ run:/ {
      if (in_atom) { s=$0; sub(/^[[:space:]]+/,"",s); r="    " s "\n";
                     if (b=="F") fail=fail r; else if (b=="W") warn=warn r; else info=info r }
      next
    }
    { in_atom=0 }
    END { printf "%s%s%s", fail, warn, info }   # FAIL group, then WARN, then INFO
  ' "$LOG_FILE" 2>/dev/null || true
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
  echo "  code-agents/PREP.sh"
  "$SCRIPT_DIR/src/main/code-agents/RUNME.sh" --plan | sed 's/^/  /'
  echo "  tail: the FAIL/WARN/INFO atoms (each reason with its '→ run:' command beneath), grouped by severity with body order preserved within each; failed pipelines with their error:/FAIL: lines quoted; pre_commit reminder; log path"
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
  run_pipeline_safe  browser-captures "$SCRIPT_DIR/input/browser-captures/claude" ${new_claude_scrape:+"$new_claude_scrape"}

  prep_pipeline_safe chat-exports
  run_pipeline_safe  chat-exports "$SCRIPT_DIR/input/chat-exports"

  prep_pipeline_safe code-agents
  run_pipeline_safe  code-agents "$SCRIPT_DIR/input/code-agents"

  echo "── done $(date -u '+%Y-%m-%dT%H:%M:%SZ') ───────────────────────────────────────────"
  # The tail carries SUMMARIES only — the body already marks each fact at its
  # source (FAIL: something that needs acting on, remedy beside it; WARN: a
  # fact worth eyes that gates nothing; INFO: a computed conclusion) and is
  # grep-able by those sigils. Here: the FAIL/WARN/INFO ATOMS — each reason with
  # its "→ run:" command(s) beneath it, in source order (hoist_atoms; a FAIL
  # inside a pipeline that COMPLETED reaches the tail too, not only a died
  # pipeline's section_error_lines), and — when a pipeline died — its error:/FAIL:
  # lines quoted under its name, so a failure is never just "scroll up". The log
  # is safe to read mid-tee: those lines are long flushed.
  local n_fail n_warn n_info atoms
  n_fail="$(grep -cE '^[[:space:]]*FAIL:' "$LOG_FILE" 2>/dev/null || true)"
  n_warn="$(grep -cE '^[[:space:]]*WARN:' "$LOG_FILE" 2>/dev/null || true)"
  n_info="$(grep -cE '^[[:space:]]*INFO:' "$LOG_FILE" 2>/dev/null || true)"
  atoms="$(hoist_atoms)"   # non-empty iff some FAIL/WARN/INFO occurred
  if [[ ${#pipeline_failures[@]} -eq 0 ]]; then
    if [[ -n "$atoms" ]]; then
      echo "All pipelines completed; $n_fail FAIL, $n_warn WARN, $n_info INFO — grouped by severity, each reason with its command (body order within each):"
      printf '%s\n' "$atoms"
    else
      echo "All pipelines completed successfully."
    fi
  else
    # FAIL summarises like WARN even when a pipeline died — the counts do not
    # vanish on the runs that need them most.
    if [[ -n "$atoms" ]]; then
      echo "$n_fail FAIL, $n_warn WARN, $n_info INFO — grouped by severity, each reason with its command (body order within each):"
      printf '%s\n' "$atoms"
    fi
    echo "Failed pipelines:"
    local errs
    for f in "${pipeline_failures[@]}"; do
      echo "  $f"
      errs="$(section_error_lines "$f")"
      [[ -n "$errs" ]] && printf '%s\n' "$errs" | sed 's/^/    /'
      case "$f" in
        "browser-captures (prep)") echo "    → check input/browser-captures/claude/ and Safari setup" ;;
        "chat-exports (prep)")   echo "    → populate input/chat-exports/ with a bulk export (see src/main/chat-exports/PREP.sh --help)" ;;
        "code-agents (prep)")  echo "    → check input/code-agents/ (the store) and input/code-projects/ (transport's source) symlinks" ;;
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
