#!/usr/bin/env bash
# src/RUNME.sh (yoga run) — process what data/input/ already holds; never acquire.
# Three pipelines (browser-captures, chat-exports, code-agents) each validate their
# inputs against all schema versions, then extract, project, and present.
# Acquisition lives elsewhere: yoga browser|agent|dashboard capture.
#
# Usage:
#   ./src/RUNME.sh [--plan] [--only <pipeline>] [--compare-scrape]
#     --plan            print the ordered step plan; run nothing
#     --only <p>        one pipeline: browser-captures | chat-exports | code-agents
#     --compare-scrape  also compare the claude projection against a fresh DOM scrape
#
# Inputs live under data/input/<provider>/<channel>/<capture>/ (any entry may be a
# hand-made symlink); --plan names each pipeline's exact steps. After: yoga check.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=src/main/steps.sh
source "$REPO_ROOT/src/main/steps.sh"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  compare_scrape=""
  only=""
  plan=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --plan) plan="1";                                               shift ;;
      --compare-scrape) compare_scrape="--compare-scrape";            shift ;;
      --only)
        case "${2-}" in
          browser-captures|chat-exports|code-agents) only="$2"; shift 2 ;;
          *) echo "error: --only takes browser-captures | chat-exports | code-agents (got: ${2-})"; exit 1 ;;
        esac ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 [--plan] [--only <pipeline>] [--compare-scrape]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

# Does this pipeline run? True when unfiltered or when --only names it.
should_run() { [[ -z "$only" || "$only" == "$1" ]]; }

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
  pip install -q -r "$REPO_ROOT/src/requirements.txt"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ────────────────────────────────────────────────────────────"
  local rc=0
  "$REPO_ROOT/src/main/${name}/PREP.sh" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  local rc=0
  "$REPO_ROOT/src/main/$name/RUNME.sh" "--${name}" "$@" || rc=$?
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
# WITHIN each group. An atom is a reason line plus its INDENTED CONTINUATION: every
# following line indented four or more, of which "→ run:" is one kind. It used to be
# the reason plus "→ run:" lines alone, which meant an atom could not have a body —
# a producer that put its detail on a second line lost the detail AND, because any
# unmatched line closed the atom, the remedy beneath it. Silently: nothing reported
# that the tail had eaten half a finding. Kept together (the body already pairs them;
# the tail must never tear them into a reason-list and a separate command-rail — a
# pile of buttons, pressed in some order, for reasons not stated). The grouping is safe
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
    /^    / || /→ run:/ {
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

LOG_FILE="$REPO_ROOT/tmp/logs/RUNME/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"

# The whole-corpus tail: the root-level REDUCE, run once after every pipeline —
# for operations whose input spans them all (the pipelines' own run_tails fold
# one pipeline's corpus; this folds the union). First member: indexing sync,
# whose locators span claude chat, code sessions, and gemini — and whose
# staleness was previously invisible to run (found 2026-07-22: the real
# index.md still cited a retired verb name). Same command-backed step
# discipline as the pipeline tails: the plan speaks `indexing sync`, and the
# gate holds it to command AND verb (help.csv step=corpus).
#
# Membership: L9 — Currency (rsc/CALCULUS.md), which subsumes the CLOSURE and
# NECESSITY tests this comment used to carry (the PR #18 review, reading-room;
# elevated to law by issue #19). indexing sync is here because its cell says
# run (machine-local, mechanical, CLOSURE holds); dashboard sync is NOT,
# because its captures are paid and out-of-run — CLOSURE fails, and a step
# here would render fresh-LOOKING pages over silently lagging semantics.
run_corpus_tail() {
  step indexing "$REPO_ROOT/src/run_python_script.sh" \
    "$REPO_ROOT/src/main/model/build_index.py" sync
  # Bare noun DELIBERATELY (not the dropped-verb bug class the plan gate
  # guards): dashboard's read-only status IS its L9 mechanism, probed here so
  # its INFO currency atoms (re-render is free; captures lag the corpus) reach
  # the tail via hoisting. step_ok: a currency nudge informs, never gates.
  step_ok dashboard "$REPO_ROOT/src/main/chat-exports/dashboard.sh"
}

# The pipelines' own --plan output is the one authority on their step order
# (each prints exactly the step list it executes — see src/main/steps.sh);
# only this script's own frame (tooling, preps, tail) is narrated here, beside
# the main() that performs it.
print_plan() {
  # The plan of THIS invocation: --only filters to its pipeline, and the
  # capture-sweep line resolves against the flags given instead of staying
  # a conditional annotation — appending --plan to any parametrised call
  # previews exactly that call.
  echo "src/RUNME.sh — the ordered plan${only:+ (--only $only)} (conditional steps annotated; nothing executed):"
  echo "  tooling: require jq; find python3; create venv at \$VENV if absent; pip install src/requirements.txt"
  if should_run browser-captures; then
    "$REPO_ROOT/src/main/browser-captures/RUNME.sh" --plan | sed 's/^/  /'
  fi
  if should_run chat-exports; then
    echo "  chat-exports/PREP.sh"
    "$REPO_ROOT/src/main/chat-exports/RUNME.sh" --plan | sed 's/^/  /'
  fi
  if should_run code-agents; then
    echo "  code-agents/PREP.sh"
    "$REPO_ROOT/src/main/code-agents/RUNME.sh" --plan | sed 's/^/  /'
  fi
  echo "  then once, over the whole corpus:"
  # shellcheck disable=SC2030,SC2031  # plan=1 deliberately CONFINED to the subshell
  ( plan=1; run_corpus_tail ) | sed 's/^/  /'
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

  if should_run browser-captures; then
    run_pipeline_safe  browser-captures "$REPO_ROOT/data/input/claude/chat/browser-API" ${compare_scrape:+"$compare_scrape"}
  fi

  if should_run chat-exports; then
    prep_pipeline_safe chat-exports
    run_pipeline_safe  chat-exports "$REPO_ROOT/data/input/claude/chat/bulk-export"
  fi

  if should_run code-agents; then
    prep_pipeline_safe code-agents
    run_pipeline_safe  code-agents "$REPO_ROOT/data/input/claude/code/machine-transport"
  fi

  # the whole-corpus reduce: over whatever is projected — idempotent, so a
  # --only run re-indexing the unchanged rest is silence, not distortion
  if ! run_corpus_tail 2>&1 | tee -a "$LOG_FILE"; then
    pipeline_failures+=("indexing (corpus tail)")
  fi

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
        "chat-exports (prep)")   echo "    → populate data/input/claude/chat/bulk-export/ with a bulk export (see src/main/chat-exports/PREP.sh --help)" ;;
        "code-agents (prep)")  echo "    → check data/input/claude/code/machine-transport/ (the store) and ext/claude-code-projects/ (transport's source) symlinks" ;;
        *) [[ -z "$errs" ]] && echo "    → scroll up: the failing step prints its error and the path of its own log" ;;
      esac
    done
  fi
  echo "Run src/test/pre_commit.sh, then: git diff rsc/test/pre_commit.log"
  echo "Log: $LOG_FILE"
}

# --plan runs before the log exists: it writes nothing, not even a log file.
# Args are parsed FIRST so the plan previews this exact invocation (--only
# filters it; the capture flags resolve their conditional lines).
parse_args "$@"
# shellcheck disable=SC2031  # this reads parse_args' plan; print_plan's subshell plan=1 is deliberately confined
if [[ -n "$plan" ]]; then print_plan; exit 0; fi
mkdir -p "$(dirname "$LOG_FILE")"
main "$@" 2>&1 | tee "$LOG_FILE"
