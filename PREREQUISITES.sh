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
    # Modern Safari keeps this setting where `defaults` cannot see it, and the reliable
    # probe (`do JavaScript "1+1"`) would drive Safari — off-limits for this read-only
    # reporter. Report the state only when the legacy key happens to be readable;
    # otherwise say honestly that we cannot tell from here. Capture itself fail-fasts
    # with a clear error if the setting is actually off (safari_assert_js_allowed).
    js_from_ae="$(defaults read -app Safari AllowJavaScriptFromAppleEvents 2>/dev/null || true)"
    case "$js_from_ae" in
      1) ok "Safari 'Allow JavaScript from Apple Events' is enabled" ;;
      0) info "Safari 'Allow JavaScript from Apple Events' is disabled — capture will fail-fast (Settings → Advanced → 'Show features for web developers', then Settings → Developer → enable it)" ;;
      *) info "Safari 'Allow JavaScript from Apple Events' cannot be verified read-only on this Safari version — if it is off, capture fail-fasts with a clear error naming this setting" ;;
    esac
  else
    info "--capture-from-browser unavailable: needs macOS + osascript; other pipelines unaffected"
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    ok "yoga dashboard capture possible: ANTHROPIC_API_KEY is set"
  else
    info "yoga dashboard capture unavailable: ANTHROPIC_API_KEY not set (only the paid concept/category capture needs it)"
  fi
}

check_room() {
  # The binding names this machine's room (see rsc/machines/README.md). The
  # path is built in pieces: the joined literal must not appear in committed
  # text, because the file rightly does not exist on fresh clones and the
  # committed xref counts are machine-invariant.
  local binding="$SCRIPT_DIR/rsc/machines"
  binding+="/self.txt"
  local rel="${binding#"$SCRIPT_DIR/"}"
  echo "room (the machine's own name for itself — never shared, never transported)"
  if [[ -f "$binding" ]]; then
    local room
    room="$(cat "$binding")"
    if [[ -f "$SCRIPT_DIR/rsc/machines/$room.csv" ]]; then
      ok "bound: $room"
    else
      info "bound: $room — but no rsc/machines/$room.csv declares it; declare the manifest, or fix the binding"
    fi
  else
    local declared="" f
    for f in "$SCRIPT_DIR/rsc/machines"/*.csv; do
      f="$(basename "$f" .csv)"
      if [[ "$f" != "_base" ]]; then declared+="$f "; fi
    done
    info "unbound — bind: echo <unique-room-name> > $rel  (rooms already declared: ${declared:-none})"
  fi
}

check_cli() {
  echo "yoga CLI (./yoga — table: rsc/cli/commands.csv)"
  local comp="$SCRIPT_DIR/cache/completions/_yoga"
  if [[ -f "$comp" ]]; then
    # Currency probe is read-only (`./yoga completions` without --write only
    # prints); cli.py is stdlib-only, so any Python 3 suffices — no venv needed.
    if "$SCRIPT_DIR/yoga" completions 2>/dev/null | cmp -s - "$comp"; then
      ok "zsh completion generated and current with rsc/cli/commands.csv"
    elif "$SCRIPT_DIR/yoga" completions &>/dev/null; then
      info "zsh completion stale vs rsc/cli/commands.csv — regenerate: ./yoga completions --write"
    else
      info "zsh completion generated; currency cannot be verified (running ./yoga needs Python 3)"
    fi
  else
    info "zsh completion not generated — ./yoga completions --write (derived under cache/; safe to regenerate any time)"
  fi
  if ! command -v zsh &>/dev/null; then
    info "zsh not present — tab-completion not applicable on this machine"
  elif [[ -f "$HOME/.zshrc" ]] && grep -q 'cache/completions' "$HOME/.zshrc" 2>/dev/null; then
    ok "completions fpath line present in ~/.zshrc"
  else
    info "no completions fpath line in ~/.zshrc — ./yoga completions --write prints the lines to add"
  fi
}

check_git_hook() {
  echo "pre-commit hook (the repo's commit gate; src/test/pre_commit.sh fails any run until installed)"
  local script="$SCRIPT_DIR/src/test/pre_commit.sh" hook link dir
  if ! command -v git &>/dev/null || ! hook="$(git -C "$SCRIPT_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null)"; then
    info "not a git clone — no hook to install"
    return
  fi
  [[ "$hook" = /* ]] || hook="$SCRIPT_DIR/$hook"
  if [[ -L "$hook" ]]; then
    link="$(readlink "$hook")"
    [[ "$link" = /* ]] || link="$(dirname "$hook")/$link"
    dir="$(cd "$(dirname "$link")" 2>/dev/null && pwd || true)"
    if [[ -n "$dir" && "$dir/$(basename "$link")" == "$script" ]]; then
      ok "installed: the load-bearing symlink to src/test/pre_commit.sh"
    else
      info "hook symlink points elsewhere ($(readlink "$hook")) — reinstall: ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit"
    fi
  elif [[ -e "$hook" ]]; then
    info "a pre-commit hook exists but is not the load-bearing symlink (a copy drifts silently) — replace: ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit"
  else
    info "not installed — ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit"
  fi
}

check_pipeline_inputs() {
  echo "pipeline inputs (this repo ships no data; you supply your own)"
  local n

  n="$(count_glob_dirs "$SCRIPT_DIR/input/claude/chat/browser-API"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n claude capture(s) in input/claude/chat/browser-API — will validate + project to markdown"
  else
    info "browser-captures: no claude captures in input/claude/chat/browser-API — will skip (populate via --capture-from-browser)"
  fi

  n="$(count_glob_dirs "$SCRIPT_DIR/input/gemini/chat/browser-DOM"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n gemini scrape(s) in input/gemini/chat/browser-DOM — markdown is the terminal artifact (browse via serve_markdown.sh); not validated"
  else
    info "browser-captures: no gemini scrapes in input/gemini/chat/browser-DOM — captured only via --capture-from-browser; not processed further"
  fi

  n="$(count_glob_dirs "$SCRIPT_DIR/input/claude/chat/bulk-export"/data-*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "chat-exports: $n bulk export(s) in input/claude/chat/bulk-export — will validate, extract, atomise, render"
  else
    info "chat-exports: no data-* bulk export in input/claude/chat/bulk-export — will skip (download via https://claude.ai/settings/data-privacy-controls)"
  fi

  if [[ -d "$SCRIPT_DIR/input/claude/code/machine-transport" ]]; then
    n="$(count_glob_dirs "$SCRIPT_DIR/input/claude/code/machine-transport"/*/)"
    local sessions
    sessions="$(find -L "$SCRIPT_DIR/input/claude/code/machine-transport" -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')"
    ok "code-agents: input/claude/code/machine-transport holds $n room(s), $sessions session file(s) — will convert + validate into cache/"
  else
    info "code-agents: no input/claude/code/machine-transport store — will skip (hand-make the symlink to the shared store; populate via ./yoga agent capture --all)"
  fi
  if [[ -d "$HOME/.claude/projects" ]]; then
    info "live ~/.claude/projects present — harness-owned, expires at Anthropic's will; stash it: ./yoga agent capture --all"
  fi
}

notes() {
  echo "notes"
  info "./RUNME.sh writes only to input/, cache/, output/, logs/ (all git-ignored) and the venv; nothing else on this machine"
  info "src/test/pre_commit.sh: code + schema tiers run everywhere; the data tier runs only for pipelines with local data (skipped with a notice otherwise)"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  check_room
  check_tools
  check_venv
  check_optional_modes
  check_cli
  check_git_hook
  check_pipeline_inputs
  notes

  if [[ "$missing_required" -eq 1 ]]; then
    echo "missing required tools — install the ✗ items above, then re-run"
    exit 1
  fi
  echo "ready — run ./RUNME.sh (pipelines without input data are skipped)"
}

main "$@"
