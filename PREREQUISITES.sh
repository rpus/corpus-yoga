#!/usr/bin/env bash
# PREREQUISITES.sh — Report what this machine has and what ./yoga run would do.
#
# Strictly read-only: no directories created, no symlinks, no venv, no installs
# (unlike ./yoga run, which does all of those). Safe as the first command on a
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
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
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
  if [[ -x "$VENV/bin/python" ]]; then
    ok "exists ($("$VENV/bin/python" --version 2>&1))"
  else
    info "not found — ./yoga run creates it and installs src/requirements.txt"
  fi
}

# check_dependencies <header> <manifest> <extract> <probe> <subject> <remediation>
#   One reporter for every pinned-dependency manifest. Both manifests hold one item
#   per non-comment/blank line by construction, so the read/count/report is shared;
#   only what varies is passed in — <extract> (a function: `<extract> <line>` echoes
#   the item id) and <probe> (a function: `<probe> <item> <line>` exits 0 and echoes a
#   version token if satisfied, else non-zero), plus the <subject>/<remediation>
#   wording. Each manifest supplies a <name>_extract / <name>_probe pair; the test
#   can't be a mere regex because it differs — a distribution-metadata lookup vs a
#   file existence check. Absence is only ever an informational –, never a ✗.
check_dependencies() {
  local header="$1" manifest="$2" extract="$3" probe="$4" subject="$5" remediation="$6"
  echo "$header"
  if [[ ! -f "$manifest" ]]; then
    info "manifest not found (unexpected)"
    return
  fi
  local detail="" seen="|" missing="" total=0 got=0 line item tok
  while IFS= read -r line; do
    line="${line%%#*}"                            # drop comment
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue   # skip blank
    item="$("$extract" "$line")"
    total=$((total + 1))
    if tok="$("$probe" "$item" "$line")"; then
      got=$((got + 1))
      # de-duplicate version tokens (18 render assets collapse to 2 pinned packages)
      if [[ -n "$tok" ]]; then
        case "$seen" in *"|$tok|"*) ;; *) seen="$seen$tok|"; detail+="${detail:+, }$tok" ;; esac
      fi
    else
      missing+="${missing:+ }$item"
    fi
  done < "$manifest"
  if [[ "$got" -eq "$total" ]]; then
    ok "$got/$total $subject ($detail)"
  else
    info "$got/$total $subject — $remediation (missing: $missing)"
  fi
}

# The parts that differ per manifest — a matched <name>_extract / <name>_probe pair.
# extract: line → item id. probe: item present? → echo a version token, else non-zero.

# Python requirements: name is the first field minus version specifiers/extras;
# presence and version come from the installed distribution's metadata.
req_extract() { printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]].*//; s/[<>=!~;[].*//'; }
req_probe() {
  local v
  v="$("$VENV/bin/python" -c "import importlib.metadata as m; print(m.version('$1'))" 2>/dev/null)" || return 1
  printf '%s %s' "$1" "$v"
}

# Render libraries: item is the dest path (first field); presence is the cached file,
# and the pinned version comes from the line's /npm/<pkg>@<ver>/ URL.
asset_extract() { printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]].*//'; }
asset_probe() {  # $1 = dest, $2 = full line
  [[ -f "$SCRIPT_DIR/cache/serve_markdown/$1" ]] || return 1
  printf '%s' "$2" | grep -oE '/npm/[^/@]+@[^/]+' | sed 's#/npm/##' || true
}

check_optional_modes() {
  echo "optional modes"
  if [[ "$(uname)" == "Darwin" ]] && command -v osascript &>/dev/null; then
    ok "browser capture possible (yoga browser capture): macOS + osascript (Safari must be logged in to claude.ai / gemini.google.com)"
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
    info "browser capture (yoga browser capture) unavailable: needs macOS + osascript; other pipelines unaffected"
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    ok "yoga dashboard capture possible: ANTHROPIC_API_KEY is set"
  else
    info "yoga dashboard capture unavailable: ANTHROPIC_API_KEY not set (only the paid concept/category capture needs it)"
  fi
}

check_machine() {
  # The binding names this machine (rsc/machine/README.md): rooted, gitignored,
  # and so spelt whole like anything else.
  local binding="$SCRIPT_DIR/machine-name.txt"
  local rel="${binding#"$SCRIPT_DIR/"}"
  local registry="$SCRIPT_DIR/rsc/machine/machines.csv"
  echo "machine (its own name for itself — never shared, never transported)"
  local declared=""
  [[ -f "$registry" ]] && declared="$(tail -n +2 "$registry" | cut -d, -f1 | tr '\n' ' ')"
  if [[ ! -f "$binding" ]]; then
    info "unbound — declare it in rsc/machine/machines.csv first, then bind:"
    echo "    → run: echo <declared-machine-name> > $rel"
    info "declared: ${declared:-none}"
    return
  fi
  local name; name="$(cat "$binding")"
  if tail -n +2 "$registry" 2>/dev/null | cut -d, -f1 | grep -qxF "$name"; then
    ok "bound: $name"
  else
    # the same declaredness gate machine.py gives every consumer: an undeclared
    # binding would mint a phantom machine in the shared transport store
    info "bound: $name — but rsc/machine/machines.csv does not declare it (declared: ${declared:-none})"
    echo "    → run: add a '$name' row to rsc/machine/machines.csv, or fix $rel"
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
  # ASK zsh, do not grep ~/.zshrc. fpath is scanned when compinit RUNS, so a line
  # added after it is present in the file and does nothing — a grep for the string
  # would report ✓ over dead completion, certifying the exact mistake the old advice
  # invited. Presence of a string is not the fact; resolution is. An interactive
  # shell sources the rc and answers for itself.
  if ! command -v zsh &>/dev/null; then
    info "zsh not present — tab-completion not applicable on this machine"
  elif [[ "$(zsh -ic 'print -r -- ${+_comps[yoga]}' 2>/dev/null | tail -1)" == "1" ]]; then
    ok "zsh resolves the yoga completion"
  else
    info "zsh does not resolve the yoga completion (an fpath line after compinit is inert)"
    echo "    → run: ./yoga completions --install"
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

check_signature_hook() {
  # A convention, not a gate: it stamps the Signature: trailer and strips the model
  # co-author (grammar: src/test/prepare_commit_msg.sh). Absent, commits simply carry
  # no signature — never a failure, so this reports informationally even when installed.
  echo "signature hook (stamps Signature: machine/provider/session; strips the model co-author)"
  local script="$SCRIPT_DIR/src/test/prepare_commit_msg.sh" hook link dir
  if ! command -v git &>/dev/null || ! hook="$(git -C "$SCRIPT_DIR" rev-parse --git-path hooks/prepare-commit-msg 2>/dev/null)"; then
    info "not a git clone — no hook to install"
    return
  fi
  [[ "$hook" = /* ]] || hook="$SCRIPT_DIR/$hook"
  if [[ -L "$hook" ]]; then
    link="$(readlink "$hook")"
    [[ "$link" = /* ]] || link="$(dirname "$hook")/$link"
    dir="$(cd "$(dirname "$link")" 2>/dev/null && pwd || true)"
    if [[ -n "$dir" && "$dir/$(basename "$link")" == "$script" ]]; then
      ok "installed: the symlink to src/test/prepare_commit_msg.sh"
    else
      info "hook symlink points elsewhere ($(readlink "$hook")) — reinstall: ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg"
    fi
  elif [[ -e "$hook" ]]; then
    info "a prepare-commit-msg hook exists but is not the symlink — replace: ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg"
  else
    info "not installed — ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg"
  fi
}

check_forge() {
  # The forge's merge settings decide how main's history is composed, yet they live
  # on the server: no clone can see them and no git config holds them. rsc/forge.csv
  # is the declaration; this is the only thing that reconciles it with reality.
  # Network- and auth-dependent, so it NEVER fails the run — unverifiable is
  # reported, never vetoed (the deterministic gate must stay offline-reproducible,
  # which is why this check lives here and not in yoga check).
  echo "forge settings (declared: rsc/forge.csv; server-side, so unverifiable offline)"
  local declared="$SCRIPT_DIR/rsc/forge.csv"
  if [[ ! -f "$declared" ]]; then
    info "no rsc/forge.csv — nothing declared to reconcile"
    return
  fi
  if ! command -v gh &>/dev/null; then
    info "gh not found — settings unverified (install: brew install gh)"
    return
  fi
  local live
  # quoted: {owner}/{repo} are gh's own placeholders, resolved from this checkout's
  # remote — never brace-expansion, and never a hard-coded (fork-specific) slug
  if ! live="$(cd "$SCRIPT_DIR" && gh api "repos/{owner}/{repo}" 2>/dev/null)"; then
    info "forge unreachable — settings unverified (offline, no GitHub remote, or: gh auth login)"
    return
  fi
  # Each drifting row carries its OWN remedy, filled in: the repo's slug from the live
  # response, and the single setting at issue. A finding that points at a command rail
  # elsewhere is a button with its reason torn off — the atom is reason + run.
  local out
  out="$(printf '%s' "$live" | python3 -c '
import csv, json, sys
live = json.load(sys.stdin)
slug = live.get("full_name") or "{owner}/{repo}"
def norm(v):
    return "true" if v is True else "false" if v is False else str(v)
for r in csv.DictReader(open(sys.argv[1])):
    key, want = r["setting"], r["value"]
    got = norm(live.get(key))
    if got == want:
        print("OK", key, want, "", sep="\t")
    else:
        flag = "-F" if want in ("true", "false") else "-f"   # -F types booleans, -f strings
        print("DRIFT", key, "declared " + want + ", live " + got,
              "gh api -X PATCH repos/" + slug + " " + flag + " " + key + "=" + want, sep="\t")
' "$declared" 2>/dev/null)" || { info "could not compare — rsc/forge.csv unreadable or malformed"; return; }
  local status key detail remedy
  while IFS=$'\t' read -r status key detail remedy; do
    [[ -z "$status" ]] && continue
    if [[ "$status" == "OK" ]]; then
      ok "$key: $detail"
    else
      info "$key: $detail"
      echo "    → run: $remedy"
    fi
  done <<< "$out"
}

check_pipeline_inputs() {
  echo "pipeline inputs (this repo ships no data; you supply your own)"
  local n

  n="$(count_glob_dirs "$SCRIPT_DIR/input/claude/chat/browser-API"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n claude capture(s) in input/claude/chat/browser-API — will validate + project to markdown"
  else
    info "browser-captures: no claude captures in input/claude/chat/browser-API — will skip (populate via: yoga browser capture)"
  fi

  n="$(count_glob_dirs "$SCRIPT_DIR/input/gemini/chat/browser-DOM"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n gemini scrape(s) in input/gemini/chat/browser-DOM — markdown is the terminal artifact (browse via ./yoga server start); not validated"
  else
    info "browser-captures: no gemini scrapes in input/gemini/chat/browser-DOM — captured only via: yoga browser capture --DOM (gemini is DOM-only); not processed further"
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
    ok "code-agents: input/claude/code/machine-transport holds $n machine(s), $sessions session file(s) — will convert + validate into cache/"
  else
    info "code-agents: no input/claude/code/machine-transport store — will skip (hand-make the symlink to the shared store; populate via ./yoga agent capture --all)"
  fi
  if [[ -d "$HOME/.claude/projects" ]]; then
    info "live ~/.claude/projects present — harness-owned, expires at Anthropic's will; stash it: ./yoga agent capture --all"
  fi
}

notes() {
  echo "notes"
  info "./yoga run writes only to input/, cache/, output/, logs/ (all git-ignored) and the venv; nothing else on this machine"
  info "./yoga check: code + schema tiers run everywhere; the data tier runs only for pipelines with local data (skipped with a notice otherwise)"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  check_machine
  check_tools
  check_venv
  check_dependencies \
    "python requirements (yoga run — manifest: src/requirements.txt)" \
    "$SCRIPT_DIR/src/requirements.txt" \
    req_extract req_probe \
    "requirements installed" \
    "pip install -r src/requirements.txt, or automatically on the next ./yoga run"
  check_dependencies \
    "markdown viewer render libs (yoga server — manifest: src/main/model/serve_assets.txt)" \
    "$SCRIPT_DIR/src/main/model/serve_assets.txt" \
    asset_extract asset_probe \
    "render assets present in cache/serve_markdown" \
    "./yoga server ensure-assets, or automatically on the next ./yoga server start"
  check_optional_modes
  check_cli
  check_git_hook
  check_signature_hook
  check_forge
  check_pipeline_inputs
  notes

  if [[ "$missing_required" -eq 1 ]]; then
    echo "missing required tools — install the ✗ items above, then re-run"
    exit 1
  fi
  echo "ready — ./yoga run (pipelines without input data are skipped)"
}

main "$@"
