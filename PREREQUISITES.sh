#!/usr/bin/env bash
# PREREQUISITES.sh — Report what this machine has and what ./RUNME.sh would do.
#
# Strictly read-only: no directories created, no symlinks, no venv, no installs
# (unlike ./RUNME.sh, which does all of those). Safe as the first command on a
# fresh clone.
#
# Exit status: non-zero only if a required tool (jq, Python 3) is missing.
#
# Usage:
#   ./PREREQUISITES.sh
#
# Legend: ✓ present   – informational / optional   ✗ required but missing

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

missing_required=0

ok()   { echo "  ✓ $*"; }
info() { echo "  – $*"; }
bad()  { echo "  ✗ $*"; missing_required=1; }

count_glob_dirs() {
  local n=0 d
  for d in "$@"; do
    [[ -d "$d" ]] && n=$((n + 1))
  done
  echo "$n"
}

check_tools() {
  echo "tools"
  if command -v jq &>/dev/null; then
    ok "jq ($(jq --version 2>/dev/null))"
  else
    bad "jq not found — install via: brew install jq"
  fi
  if command -v python3 &>/dev/null; then
    ok "python3 ($(python3 --version 2>&1))"
  else
    bad "Python 3 not found — install via: brew install python"
  fi
  info "bash $BASH_VERSION (3.2+ suffices; scripts avoid 4.x features)"
}

check_venv() {
  echo "venv ($VENV — override via VENV=...)"
  if [[ -f "$VENV/bin/python" ]]; then
    ok "exists ($("$VENV/bin/python" --version 2>&1))"
    if "$VENV/bin/python" -c 'import jsonschema, referencing' &>/dev/null; then
      ok "jsonschema + referencing importable"
    else
      info "jsonschema/referencing missing — ./RUNME.sh installs them (pip install -r src/requirements.txt)"
    fi
  else
    info "not found — ./RUNME.sh creates it and installs src/requirements.txt"
  fi
}

check_optional_modes() {
  echo "optional modes"
  if [[ "$(uname)" == "Darwin" ]] && command -v osascript &>/dev/null; then
    ok "--capture-from-browser possible: macOS + osascript (Safari must be logged in to claude.ai / gemini.google.com)"
    if [[ "$(defaults read -app Safari AllowJavaScriptFromAppleEvents 2>/dev/null)" == "1" ]]; then
      ok "Safari 'Allow JavaScript from Apple Events' is enabled"
    else
      info "Safari 'Allow JavaScript from Apple Events' appears disabled — capture will refuse to run (Settings → Advanced → 'Show features for web developers', then Developer → enable it)"
    fi
  else
    info "--capture-from-browser unavailable: needs macOS + osascript; other pipelines unaffected"
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    ok "--pay-for-inference possible: ANTHROPIC_API_KEY is set"
  else
    info "--pay-for-inference unavailable: ANTHROPIC_API_KEY not set (only table inference needs it)"
  fi
}

check_pipeline_inputs() {
  echo "pipeline inputs (this repo ships no data; you supply your own)"
  local n

  n="$(count_glob_dirs "$SCRIPT_DIR/ext/browser-captures/claude"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n claude capture(s) in ext/browser-captures/claude — will validate + project to markdown"
  else
    info "browser-captures: no claude captures in ext/browser-captures/claude — will skip (populate via --capture-from-browser)"
  fi

  n="$(count_glob_dirs "$SCRIPT_DIR/ext/browser-captures/gemini"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n gemini scrape(s) in ext/browser-captures/gemini — markdown is the terminal artifact (browse via serve_markdown.sh); not validated"
  else
    info "browser-captures: no gemini scrapes in ext/browser-captures/gemini — captured only via --capture-from-browser; not processed further"
  fi

  n="$(count_glob_dirs "$SCRIPT_DIR/ext/chat-exports"/data-*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "chat-exports: $n bulk export(s) in ext/chat-exports — will validate, extract, atomise, render"
  else
    info "chat-exports: no data-* bulk export in ext/chat-exports — will skip (download via https://claude.ai/settings/data-privacy-controls)"
  fi

  if [[ -d "$HOME/.claude/projects" ]]; then
    n="$(count_glob_dirs "$HOME/.claude/projects"/-Users-*/)"
    local sessions
    sessions="$(find "$HOME/.claude/projects" -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')"
    ok "code-projects: ~/.claude/projects has $n project(s), $sessions session file(s) — will convert + validate into gen/"
  else
    info "code-projects: ~/.claude/projects not found — will skip (created by using the Claude Code CLI)"
  fi
}

notes() {
  echo "notes"
  info "./RUNME.sh writes only to ext/, gen/, logs/ (all git-ignored) and the venv; nothing else on this machine"
  info "src/test/pre_commit.sh: code + schema tiers run everywhere; the data tier runs only for pipelines with local data (skipped with a notice otherwise)"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  check_tools
  check_venv
  check_optional_modes
  check_pipeline_inputs
  notes

  if [[ "$missing_required" -eq 1 ]]; then
    echo "missing required tools — install the ✗ items above, then re-run"
    exit 1
  fi
  echo "ready — run ./RUNME.sh (pipelines without input data are skipped)"
}

main "$@"
