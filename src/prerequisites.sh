#!/usr/bin/env bash
# src/prerequisites.sh — Report what this machine has and what yoga pipeline run would do.
#
# Strictly read-only: no directories created, no symlinks, no venv, no installs
# (unlike yoga pipeline run, which does all of those). Safe as the first command on a
# fresh clone.
#
# Exit status: non-zero only if a required tool (jq, Python 3) is missing.
#
# Usage:
#   ./src/prerequisites.sh              # what still needs attention (– and ✗); all-green sections hidden
#   ./src/prerequisites.sh --show-all   # the full report, including satisfied (✓) items
#
# Legend: ✓ present   – informational / optional   ✗ required but missing

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${VENV:=$HOME/venvs/general}"

SHOW_ALL=0
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --show-all) SHOW_ALL=1; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) shift ;;
    esac
  done
}

missing_required=0

# Failures-only by default: ✓ (satisfied) lines are withheld unless --show-all, and a
# section header prints lazily — only when its first shown line (– or ✗) appears — so an
# all-satisfied section vanishes entirely. The bare `yoga` invocation shows this report,
# so its default is the short "what still needs attention" list.
_hdr=""
sec()    { _hdr="$*"; }
_flush() { if [[ -n "$_hdr" ]]; then echo "$_hdr"; _hdr=""; fi; }
ok()     { if (( SHOW_ALL )); then _flush; echo "  ✓ $*"; fi; }
info()   { _flush; echo "  – $*"; }
bad()    { _flush; echo "  ✗ $*"; missing_required=1; }

count_glob_dirs() {
  local n=0 d
  for d in "$@"; do
    [[ -d "$d" ]] && n=$((n + 1))
  done
  echo "$n"
}

check_tools() {
  sec "tools"
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
  # Informational, never a ✗: absent, the gate skips its type check and still gates
  # deterministically. pyright is Pylance's own engine and reads the same
  # pyrightconfig.json the editor does — one declaration, three readers.
  if command -v pyright &>/dev/null; then
    ok "pyright ($(pyright --version 2>/dev/null | head -1 | awk '{print $2}')) — yoga test run type-checks src/ against pyrightconfig.json"
  else
    info "pyright not found — yoga test run skips its type check; install into \$VENV via: pip install pyright"
  fi
  # Informational, never a ✗: the gate skips its shellcheck pass when the tool is absent,
  # so a clone without it still gates deterministically — it simply lints nothing, and
  # this is the one place that says so.
  if command -v shellcheck &>/dev/null; then
    ok "shellcheck ($(shellcheck --version | awk '/^version:/ {print $2}')) — yoga test run lints every src/**/*.sh"
  else
    info "shellcheck not found — yoga test run skips its shell lint; install via: brew install shellcheck"
  fi
  ok "bash $BASH_VERSION (3.2+ suffices; scripts avoid 4.x features)"
}

check_venv() {
  sec "venv ($VENV — override via VENV=...)"
  if [[ -x "$VENV/bin/python" ]]; then
    ok "exists ($("$VENV/bin/python" --version 2>&1))"
  else
    info "not found — yoga pipeline run creates it and installs src/requirements.txt"
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
  sec "$header"
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
  [[ -f "$REPO_ROOT/tmp/cache/serve_markdown/$1" ]] || return 1
  printf '%s' "$2" | grep -oE '/npm/[^/@]+@[^/]+' | sed 's#/npm/##' || true
}

check_optional_modes() {
  sec "optional modes"
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
  local binding="$REPO_ROOT/machine-name.txt"
  local rel="${binding#"$REPO_ROOT/"}"
  local registry="$REPO_ROOT/rsc/machine/machines.csv"
  sec "machine (its own name for itself — never shared, never transported)"
  # The pre-move location, built in pieces — for the very reason the rooted
  # binding no longer needs to be. This path must exist on NO clean clone, so a
  # committed literal naming it would be a dangling reference, and would resolve
  # one way on a machine that migrated and another on one that had not. Reported
  # first: on an un-migrated machine it is the answer to every other line here.
  # Transitional — delete this check once no machine carries the residue.
  # Split above 'machines', not above 'self.txt': the DIRECTORY vanishes on
  # migration too, so a literal naming it resolves on an un-migrated machine and
  # dangles on a migrated one — machine-dependent by the same rule. (The first
  # draft of this check split one component too low and xref said so.) A fragment
  # beginning '/' is never read as a repo path, so this names nothing that can go.
  local legacy="$REPO_ROOT/rsc"; legacy+="/machines/self.txt"
  if [[ -f "$legacy" ]]; then
    local lrel="${legacy#"$REPO_ROOT/"}"
    info "legacy binding at $lrel — the binding moved to $rel (2026-07-17); migrate it:"
    echo "    → run: mv $lrel $rel && rmdir $(dirname "$lrel")"
  fi
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
  sec "yoga CLI (tables: rsc/cli/)"
  # `yoga completions` (bare) is itself the read-only status — written/current/stale
  # and wired-or-not — so defer to that one voice rather than re-deriving here.
  # cli.py is stdlib-only, so any Python 3 suffices — no venv needed.
  local comp_status
  if comp_status="$("$REPO_ROOT/yoga" completions 2>/dev/null)"; then
    case "$comp_status" in
      *current*) ok   "zsh completions generated and current with rsc/cli/" ;;
      *STALE*)   info "zsh completions stale vs rsc/cli/ → refresh: ./yoga completions install-latest (then restart terminal)" ;;
      *)         info "zsh completions not generated → run: ./yoga completions install-latest (then restart terminal)" ;;
    esac
  else
    info "zsh completion currency cannot be verified (running ./yoga needs Python 3)"
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
    info "zsh does not resolve the yoga completions"
    echo "    → run: ./yoga completions install-latest (then restart terminal)"
  fi
}

check_git_hook() {
  # The one voice for this fact: run.sh used to probe its own installation
  # too, and say so in its own words. Two probes, one fact — and its copy was
  # downgraded to advice on the very branches where nothing was vetting at all.
  sec "pre-commit hook (the repo's commit gate; until installed, nothing vets a commit)"
  local script="$REPO_ROOT/src/test/run.sh" hook link dir
  if ! command -v git &>/dev/null || ! hook="$(git -C "$REPO_ROOT" rev-parse --git-path hooks/pre-commit 2>/dev/null)"; then
    info "not a git clone — no hook to install"
    return
  fi
  [[ "$hook" = /* ]] || hook="$REPO_ROOT/$hook"
  if [[ -L "$hook" ]]; then
    link="$(readlink "$hook")"
    [[ "$link" = /* ]] || link="$(dirname "$hook")/$link"
    dir="$(cd "$(dirname "$link")" 2>/dev/null && pwd || true)"
    if [[ -n "$dir" && "$dir/$(basename "$link")" == "$script" ]]; then
      ok "installed: the load-bearing symlink to src/test/run.sh"
    else
      info "hook symlink points elsewhere ($(readlink "$hook")) — reinstall: yoga test install-hook"
    fi
  elif [[ -e "$hook" ]]; then
    info "a pre-commit hook exists but is not the load-bearing symlink (a copy drifts silently) — replace: yoga test install-hook"
  else
    info "not installed — yoga test install-hook"
  fi
}

check_signature_hook() {
  # A convention, not a gate: it stamps the Signature: trailer and strips the model
  # co-author (grammar: src/test/prepare_commit_msg.sh). Absent, commits simply carry
  # no signature — never a failure, so this reports informationally even when installed.
  sec "signature hook (stamps Signature: machine/provider/session; strips the model co-author)"
  local script="$REPO_ROOT/src/test/prepare_commit_msg.sh" hook link dir
  if ! command -v git &>/dev/null || ! hook="$(git -C "$REPO_ROOT" rev-parse --git-path hooks/prepare-commit-msg 2>/dev/null)"; then
    info "not a git clone — no hook to install"
    return
  fi
  [[ "$hook" = /* ]] || hook="$REPO_ROOT/$hook"
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
  # The forge's merge settings decide how main's history is composed, yet they live on
  # the server: no clone can see them and no git config holds them. rsc/forge.csv is the
  # declaration; `yoga forge` is the ONE thing that reconciles it with reality, and this
  # renders its rows in the machine report's voice — the reconciliation is derived once,
  # not once per reader. Network- and auth-dependent, so it NEVER fails the run:
  # unverifiable is reported, never vetoed (the deterministic gate stays offline-
  # reproducible, which is why this lives here and not in yoga test run).
  sec "forge settings (declared: rsc/forge.csv; server-side, so unverifiable offline)"
  local status key detail remedy
  while IFS=$'\t' read -r status key detail remedy; do
    [[ -z "$status" ]] && continue
    case "$status" in
      OK)    ok   "$key: $detail" ;;
      DRIFT) info "$key: $detail"; echo "    → run: $remedy" ;;
      *)     info "$key: $detail" ;;
    esac
  done < <("$REPO_ROOT/src/main/cli/forge.sh" --tsv 2>/dev/null)
}

check_pipeline_inputs() {
  sec "pipeline inputs (this repo ships no data; you supply your own)"
  local n

  n="$(count_glob_dirs "$REPO_ROOT/data/input/claude/chat/browser-API"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n claude capture(s) in data/input/claude/chat/browser-API — will validate + project to markdown"
  else
    info "browser-captures: no claude captures in data/input/claude/chat/browser-API — will skip (populate via: yoga browser capture)"
  fi

  n="$(count_glob_dirs "$REPO_ROOT/data/input/gemini/chat/browser-DOM"/*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "browser-captures: $n gemini scrape(s) in data/input/gemini/chat/browser-DOM — markdown is the terminal artifact (browse via yoga server start); not validated"
  else
    info "browser-captures: no gemini scrapes in data/input/gemini/chat/browser-DOM — captured only via: yoga browser capture --provider gemini (DOM is its only mechanism); not processed further"
  fi

  n="$(count_glob_dirs "$REPO_ROOT/data/input/claude/chat/bulk-export"/data-*/)"
  if [[ "$n" -gt 0 ]]; then
    ok "chat-exports: $n bulk export(s) in data/input/claude/chat/bulk-export — will validate, extract, atomise, render"
  else
    info "chat-exports: no data-* bulk export in data/input/claude/chat/bulk-export — will skip (download via https://claude.ai/settings/data-privacy-controls)"
  fi

  if [[ -d "$REPO_ROOT/data/input/claude/code/machine-transport" ]]; then
    n="$(count_glob_dirs "$REPO_ROOT/data/input/claude/code/machine-transport"/*/)"
    local sessions
    sessions="$(find -L "$REPO_ROOT/data/input/claude/code/machine-transport" -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')"
    ok "code-agents: data/input/claude/code/machine-transport holds $n machine(s), $sessions session file(s) — will convert + validate into tmp/cache/"
  else
    info "code-agents: no data/input/claude/code/machine-transport store — will skip (hand-make the symlink to the shared store; populate via yoga agent capture --all)"
  fi
  if [[ -d "$HOME/.claude/projects" ]]; then
    info "live ~/.claude/projects present — harness-owned, expires at Anthropic's will; stash it: yoga agent capture --all"
  fi
}

notes() {
  # Commentary, not status — only in the full report.
  (( SHOW_ALL )) || return 0
  sec "notes"
  info "yoga pipeline run writes only to data/input/, tmp/cache/, data/output/, tmp/logs/ (all git-ignored) and the venv; nothing else on this machine"
  info "yoga test run: code + schema tiers run everywhere; the data tier runs only for pipelines with local data (skipped with a notice otherwise)"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  check_machine
  check_tools
  check_venv
  check_dependencies \
    "python requirements (yoga pipeline run — manifest: src/requirements.txt)" \
    "$REPO_ROOT/src/requirements.txt" \
    req_extract req_probe \
    "requirements installed" \
    "pip install -r src/requirements.txt, or automatically on the next yoga pipeline run"
  check_dependencies \
    "markdown viewer render libs (yoga server — manifest: src/main/model/serve_assets.txt)" \
    "$REPO_ROOT/src/main/model/serve_assets.txt" \
    asset_extract asset_probe \
    "render assets present in tmp/cache/serve_markdown" \
    "yoga server ensure-assets, or automatically on the next yoga server start"
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
  if (( SHOW_ALL )); then
    echo "ready — yoga pipeline run (pipelines without input data are skipped)"
  else
    # Default is failures-only; if we reach here nothing above needed attention.
    echo "ready — yoga pipeline run · full report: yoga prerequisites --show-all · commands: yoga -h"
  fi
}

main "$@"
