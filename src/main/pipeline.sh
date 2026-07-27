#!/usr/bin/env bash
# src/main/pipeline.sh (yoga pipeline) — the pipelines, and the run over data/input/ that never
# acquires. Each pipeline validates its inputs against all schema versions, then extracts,
# projects and presents. Acquisition lives elsewhere: yoga browser|agent|dashboard capture.
#
# Usage:
#   yoga pipeline                          # the pipelines this repo has (bare: status)
#   yoga pipeline --names                  # their names alone, one per line
#   yoga pipeline run [<pipeline>] [<item>]  # run what bare lists, one of them by name, or
#                                            # one input item of that one
#     --plan            print the ordered step plan; run nothing
#   yoga pipeline sync [<pipeline>]        # re-render each datum's matrix.md from the
#                                          # vN.log files beside it
#
# The pipeline LIST is derived, not declared: a directory under src/main/ holding a
# run.sh is a pipeline. It was written out in five places before, so adding one meant
# remembering all five; now the positional is validated against what exists.
#
# Inputs live under data/input/<provider>/<channel>/<capture>/ (any entry may be a
# hand-made symlink); --plan names each pipeline's exact steps. After: yoga test run.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=src/main/steps.sh
source "$REPO_ROOT/src/main/steps.sh"
: "${VENV:=$HOME/venvs/general}"

# The pipelines: a directory under src/main/ that implements the run phase. Derived, so
# adding a pipeline is adding a directory rather than editing five lists.
pipelines() {
  local d
  for d in "$REPO_ROOT"/src/main/*/; do
    if [[ -f "$d/run.sh" ]]; then basename "$d"; fi
  done
  # `[[ … ]] && basename` would leave the LAST directory's test as the function's status, so
  # a final non-pipeline directory (src/main/cli, src/main/model) returned 1 — and under
  # `set -e` that killed `yoga pipeline --names` before its `exit 0` could run. A listing
  # that succeeds must say so.
  return 0
}

# The bare noun lists the pipelines; `run` runs what it lists. One glob feeds both, so the
# verb's domain IS the noun's output — `yoga pipeline run` with no name runs exactly the
# names bare printed, and cannot drift from them.
#
# --names prints them alone, one per line, for a reader that is a program:
#   for p in $(yoga pipeline --names); do yoga pipeline run "$p"; done
# is the same work as `yoga pipeline run`, spelled out. The decorated status is for people;
# neither is derived from the other's text.
status() {
  echo "pipelines (src/main/<name>/ implementing run; processing only — acquisition is yoga browser|agent|dashboard capture):"
  local name phases nested v
  for name in $(pipelines); do
    phases=""
    prep_step "$name" >/dev/null 2>&1 && phases+="prep "
    [[ -f "$REPO_ROOT/src/main/$name/run.sh" ]] && phases+="run "
    if [[ -f "$REPO_ROOT/src/main/$name/validate.sh" ]]; then
      phases+="validate"
    else
      # A phase may be NESTED. browser-captures validates per provider, because only claude
      # has an API with a schema (apiConversation) and gemini is DOM-only with nothing to
      # validate against — so its validate.sh lives at browser-captures/claude/. Reporting
      # "no validate" there would be false, and `yoga test run` already carries a hand-written
      # exception for the same file (check_required_files), which is the tell.
      nested=""
      for v in "$REPO_ROOT/src/main/$name"/*/validate.sh; do
        [[ -f "$v" ]] || continue
        v="${v%/validate.sh}"; nested+="${nested:+,}$(basename "$v")"
      done
      [[ -n "$nested" ]] && phases+="validate($nested)"
    fi
    printf '  %-18s %s\n' "$name" "${phases:-—}"   # name FIRST: `yoga pipeline | awk '{print $1}'` works
  done
  echo "  → local input state: yoga prerequisites · each pipeline's steps: yoga pipeline run --plan"
}

parse_args() {
  only=""
  item=""
  plan=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --plan) plan="1";                                               shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      -*) echo "Unknown argument: $1"; echo "Usage: $0 run [<pipeline>] [--plan]"; echo "Pass --help for more information."; exit 1 ;;
      # A POSITIONAL names the pipeline, where --only used to. One way to say one thing:
      # the noun-verb-object the surface already reads as, validated against the pipelines
      # that exist rather than against a list someone maintains.
      *)
        # A SECOND positional is the one item to process, which every pipeline's run.sh
        # already takes under its singular flag. Without it the pipeline runs over its
        # whole input root, which is the only other thing a run can be about.
        if [[ -n "$only" ]]; then
          if [[ -n "$item" ]]; then
            echo "error: one item at a time (already have $item, then $1)" >&2; exit 1
          fi
          item="$1"; shift; continue
        fi
        # No pipe to grep: under `set -o pipefail`, grep -q exits at the first match and
        # the producer dies of SIGPIPE, so a SUCCESSFUL match reads as a failed pipeline.
        local known="" candidate
        for candidate in $(pipelines); do [[ "$candidate" == "$1" ]] && known=1; done
        if [[ -z "$known" ]]; then
          echo "error: no pipeline $1 — this repo has: $(pipelines | tr '\n' ' ')" >&2; exit 1
        fi
        only="$1"; shift ;;
    esac
  done
}

# sync REGENERATES (the verb's one meaning): each datum's matrix.md is re-rendered from
# the vN.log files beside it, so the summary agrees with the logs it summarises.
sync_matrices() {
  parse_args "$@"
  [[ -z "$item" ]] || { echo "yoga pipeline sync: takes a pipeline, not an item ($item)" >&2; exit 1; }
  local p
  for p in $(pipelines); do
    should_run "$p" || continue
    "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/test/gen_changelog_matrix.py" \
      --pipeline "$p" --write
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

# Which pipelines have a prep step, and what each is called. DECLARED, not globbed for a
# shared filename: the prep scripts do different things — chat-exports requires an input,
# code-agents links a directory — and browser-captures' is a CAPTURE, the `yoga browser`
# target, which a pipeline run must never perform. Globbing one name listed a prep phase
# for browser-captures that `run` has never executed, which is a status line stating
# something untrue about what the command does.
prep_step() {
  case "$1" in
    chat-exports) echo require_export.sh ;;
    code-agents)  echo link_projects.sh ;;
    *)            return 1 ;;
  esac
}

# The prep step as `step` takes it: the operation, then the file that IS the command
# (plan_impl's second shape). Read by the run and by the plan, so the line printed is the
# call made — the property `step` exists to give every other phase.
prep_call() {
  local script
  script="$(prep_step "$1")" || return 1
  echo "${script%.sh} $REPO_ROOT/src/main/$1/$script"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ──────────────────────────────────────────────────────────"
  local rc=0 op impl
  read -r op impl <<< "$(prep_call "$name")" || { echo "no prep step for $name"; return 0; }
  step "$op" "$impl" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  local rc=0
  "$REPO_ROOT/src/main/$name/run.sh" "--${name}" "$@" || rc=$?
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

LOG_FILE="$REPO_ROOT/tmp/logs/pipeline/run/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"

# The whole-corpus tail: the root-level REDUCE, run once after every pipeline —
# for operations whose input spans them all (the pipelines' own run_tails fold
# one pipeline's corpus; this folds the union). First member: indexing sync,
# whose locators span claude chat, code sessions, and gemini — and whose
# staleness was previously invisible to run (found 2026-07-22: the real
# index.md still cited a retired verb name). Same command-backed step
# discipline as the pipeline tails: the plan speaks `indexing sync`, and the
# gate holds it to command AND verb (a declared step=corpus).
#
# Membership: L9 — Currency (rsc/CALCULUS.md), which subsumes the CLOSURE and
# NECESSITY tests this comment used to carry (the PR #18 review, reading-room;
# elevated to law by issue #19). indexing sync is here because its cell says
# run (machine-local, mechanical, CLOSURE holds); dashboard sync is NOT,
# because its captures are paid and out-of-run — CLOSURE fails, and a step
# here would render fresh-LOOKING pages over silently lagging semantics.
run_corpus_tail() {
  step indexing "$REPO_ROOT/src/run_python_script.sh" \
    "$REPO_ROOT/src/main/model/indexing.py" sync
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
  echo "yoga pipeline run${only:+ $only} — the ordered plan (conditional steps annotated; nothing executed):"
  echo "  tooling: require jq; find python3; create venv at \$VENV if absent; pip install src/requirements.txt"
  if should_run browser-captures; then
    "$REPO_ROOT/src/main/browser-captures/run.sh" --plan | sed 's/^/  /'
  fi
  if should_run chat-exports; then
    # printed by the same wrapper that runs it, so the plan cannot drift from the call
    ( plan=1; read -r op impl <<< "$(prep_call chat-exports)"; step "$op" "$impl" ) | sed 's/^/  /'
    "$REPO_ROOT/src/main/chat-exports/run.sh" --plan | sed 's/^/  /'
  fi
  if should_run code-agents; then
    # printed by the same wrapper that runs it, so the plan cannot drift from the call
    ( plan=1; read -r op impl <<< "$(prep_call code-agents)"; step "$op" "$impl" ) | sed 's/^/  /'
    "$REPO_ROOT/src/main/code-agents/run.sh" --plan | sed 's/^/  /'
  fi
  echo "  then once, over the whole corpus:"
  # shellcheck disable=SC2030,SC2031  # plan=1 deliberately CONFINED to the subshell
  ( plan=1; run_corpus_tail ) | sed 's/^/  /'
  echo "  tail: the FAIL/WARN/INFO atoms (each reason with its '→ run:' command beneath), grouped by severity with body order preserved within each; failed pipelines with their error:/FAIL: lines quoted; the yoga test run reminder; log path"
}

main() {
  parse_args "$@"
  echo "$(basename "$0") $* — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  # One item: the pipeline's own singular flag — browser-captures takes --browser-capture,
  # chat-exports --chat-export, code-agents --code-agent. Derived by dropping the plural's
  # 's' rather than listed, so a fourth pipeline needs no edit here. The corpus tail is not
  # run: it reduces over everything, and this invocation is about one datum.
  if [[ -n "$item" ]]; then
    "$REPO_ROOT/src/main/$only/run.sh" "--${only%s}" "$item"
    return $?
  fi

  local -a pipeline_failures=()

  if should_run browser-captures; then
    run_pipeline_safe  browser-captures "$REPO_ROOT/data/input/claude/chat/browser-API"
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
      echo "All pipelines completed; $n_fail FAIL, $n_warn WARN, $n_info INFO:"
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
        "chat-exports (prep)")   echo "    → populate data/input/claude/chat/bulk-export/ with a bulk export (see src/main/chat-exports/require_export.sh --help)" ;;
        "code-agents (prep)")  echo "    → check data/input/claude/code/machine-transport/ (the store) and ext/claude-code-projects/ (transport's source) symlinks" ;;
        *) [[ -z "$errs" ]] && echo "    → scroll up: the failing step prints its error and the path of its own log" ;;
      esac
    done
  fi
  echo "Run yoga test run, then: git diff rsc/test/run.log"
  echo "Log: $LOG_FILE"
}

# The noun's own dispatch. Bare is STATUS — read-only, writes nothing, runs no pipeline —
# which is the convention every other command already keeps and which `run` broke by acting
# on a bare invocation. `run` is the verb that acts.
case "${1-}" in
  '')        status; exit 0 ;;
  --names)   pipelines; exit 0 ;;
  run)       shift ;;
  sync)      shift; sync_matrices "$@"; exit $? ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  # The pipeline runners call this file's siblings with their own --<name> flag; a bare
  # a bare --plan reaching here without `run` is a caller from before the verb existed,
  # and is accepted rather than failed: the flag says what was meant.
  --plan) ;;
  *) echo "yoga pipeline: unknown verb ${1} — takes: run (bare: status)" >&2; exit 1 ;;
esac

# --plan runs before the log exists: it writes nothing, not even a log file.
# Args are parsed FIRST so the plan previews this exact invocation (the positional
# filters it; the capture flags resolve their conditional lines).
parse_args "$@"
# shellcheck disable=SC2031  # this reads parse_args' plan; print_plan's subshell plan=1 is deliberately confined
if [[ -n "$plan" ]]; then print_plan; exit 0; fi
mkdir -p "$(dirname "$LOG_FILE")"
main "$@" 2>&1 | tee "$LOG_FILE"
