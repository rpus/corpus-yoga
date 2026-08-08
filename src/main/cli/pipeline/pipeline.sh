#!/usr/bin/env bash
# src/main/cli/pipeline/pipeline.sh (yoga pipeline) — the pipelines, and the run over data/input/ that never
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
# The pipeline LIST is derived, not declared: a pipeline is a subdirectory of
# src/main/pipeline/, so adding one is adding a directory; the positional is
# validated against what exists. Each directory's pipeline.json declares its facts
# (schemas, input root, globs), typed by the pipeline.schema.json beside them.
#
# Inputs live under data/input/<provider>/<channel>/<capture>/ (any entry may be a
# hand-made symlink); --plan names each pipeline's exact steps. After: yoga test run.

set -euo pipefail
SELF='src/main/cli/pipeline/pipeline.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/steps.sh
source "$REPO_ROOT/src/main/steps.sh"
# shellcheck source=src/main/send.sh
source "$REPO_ROOT/src/main/send.sh"   # may_send — the shell face of YOGA_NO_SEND (#29)
: "${VENV:=$HOME/venvs/general}"

# The pipelines: the subdirectories of src/main/pipeline/. Membership is placement —
# no run.sh sniff, so a member missing its run phase still LISTS here and fails the
# gate's structure.pipeline_implements_run check, instead of silently leaving the list.
pipelines() {
  local d
  for d in "$REPO_ROOT"/src/main/pipeline/*/; do
    [[ -d "$d" ]] || continue
    basename "$d"
  done
}

# The declared input root, repo-relative: pipeline.json is the one committed authority
# for this path — read here, never restated.
input_of() {
  jq -r .input "$REPO_ROOT/src/main/pipeline/$1/pipeline.json"
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
  echo "pipelines (src/main/pipeline/<name>/; processing only — acquisition is yoga browser|agent|dashboard capture):"
  local name phases nested v
  for name in $(pipelines); do
    phases=""
    prep_step "$name" >/dev/null 2>&1 && phases+="prep "
    [[ -f "$REPO_ROOT/src/main/pipeline/$name/run.sh" ]] && phases+="run "
    if [[ -f "$REPO_ROOT/src/main/pipeline/$name/validate.sh" ]]; then
      phases+="validate"
    else
      # A phase may be NESTED. browser-captures validates per provider, because only claude
      # has an API with a schema (apiConversation) and gemini is DOM-only with nothing to
      # validate against — so its validate.sh lives at browser-captures/claude/. Reporting
      # "no validate" there would be false, and `yoga test run` already carries a hand-written
      # exception for the same file (check_required_files), which is the tell.
      nested=""
      for v in "$REPO_ROOT/src/main/pipeline/$name"/*/validate.sh; do
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
      # A POSITIONAL names the pipeline. One way to say one thing:
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
    "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/test/dev/gen_changelog_matrix.py" \
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
  # pip reaches PyPI on every run (the upgrade check alone is a send), so refusal skips
  # it with a note and the run proceeds on the venv as-is — a fresh venv then fails at
  # its first import, visibly, with this line just above it in the log (#29).
  if ! may_send; then
    echo "YOGA_NO_SEND=1: skipping pip install — the venv serves as-is"
    return 0
  fi
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
  echo "${script%.sh} $REPO_ROOT/src/main/pipeline/$1/$script"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ──────────────────────────────────────────────────────────"
  local rc=0 op impl pair
  # The failure has to be caught on prep_call, not on `read`: a herestring always supplies
  # a newline, so `read` succeeds on empty input and would hand `step` two empty arguments.
  pair="$(prep_call "$name")" || { echo "no prep step for $name"; return 0; }
  read -r op impl <<< "$pair"
  step "$op" "$impl" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  local rc=0
  "$REPO_ROOT/src/main/pipeline/$name/run.sh" "--${name}" "$@" || rc=$?
  echo ""
  return $rc
}

# A pipeline that exits non-zero has gated on SOMETHING; if it never said so in the
# vocabulary the table counts, the run cannot state why it failed and the row reads
# `0 FAIL … failed`. That gap is the step's defect — and the section still HOLDS the
# finding: a crash's last logged line names it (a python traceback ends on the
# exception). The runner quotes those last words into the FAIL: atom, verbatim, so
# the table counts it and the tail quotes it as usual — observation, not invention;
# exit-status failures become FAIL:ures like any other (#337).
run_pipeline_safe() {
  local name="$1"; shift
  if ! run_pipeline "$name" "$@"; then
    pipeline_failures+=("$name")
    if ! section_has_fail "$name"; then
      local last
      last="$(section_last_words "$name")"
      echo "FAIL: $name exited non-zero without stating a finding — its last words: ${last:-(no output)}"
    fi
  fi
}

# The last non-empty line of one section of the log, whitespace-stripped — the
# step's own last words, flushed through the tee by the time its runner returns
# (the same guarantee section_has_fail already relies on).
section_last_words() {
  awk -v want="$1" '
    /^── / { in_section = ($2 == want); next }
    in_section && NF { last = $0 }
    END { if (last != "") { sub(/^[[:space:]]*/, "", last); print last } }
  ' "$LOG_FILE" 2>/dev/null
}

# Does this section already carry a FAIL: atom? Read from its banner to the end of what
# has been logged so far — the section is complete by the time its runner has returned.
#
# `── prep: <name> ──` is OUTSIDE this: a prep banner closes the match, so a FAIL: printed
# by a prep step would not be found here (and atom_table would count it under whichever
# pipeline preceded it). No prep step emits atoms today — this is a recorded decision, not
# an oversight, and the day one does, both readers need the prep section as its own row.
section_has_fail() {
  awk -v want="$1" '
    /^── / { in_section = ($2 == want); next }
    in_section && /^[[:space:]]*FAIL:/ { found = 1 }
    END { exit found ? 0 : 1 }
  ' "$LOG_FILE" 2>/dev/null
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

# The tail is a TABLE: one row per STAGE of the run — the three pipelines, each prep, and
# the corpus reduce — counting the atoms that occurred inside it, beside its verdict. A
# stage is a phase of the RUN, not a paragraph of the log: `browser-captures` is what you
# type after `yoga pipeline run` to do that stage alone, and the banner is merely how the
# log marks where it began. Two facts about one
# pipeline, on one line, so they cannot disagree unnoticed — a row saying `failed` with
# no FAIL is a defect of the step, and the table is where it becomes visible.
#
# Nothing is hoisted. An atom's context IS the section it sits in, and reprinting it
# elsewhere loses that context while duplicating the text: a reader who wants the detail
# greps the sigil, or diffs two logs. The body stays the one place a finding is stated.
#
# Sections are the `── name ───` banners the runners print; the corpus tail's atoms fall
# after the last banner and are counted under `corpus`.
atom_table() {
  local failed_csv="$1"
  awk -v failed="$failed_csv" '
    function flush(  verdict) {
      if (section == "") return
      verdict = (index("," failed ",", "," section ",") > 0) ? "failed" : "ok"
      # line = where the banner for this stage sits in this log: the anchor that turns
      # a count back into the lines that produced it, with no grep to compose.
      # Rows are held, not printed, because the stage column is as wide as the widest
      # NAME and that is unknown until the last one is read — a width chosen by eye
      # overflows the day a stage is added, shifting every column after it.
      rows[++n_rows] = sprintf("%s\t%d\t%d\t%d\t%s\t%d", section, n_fail, n_warn, n_info, verdict, banner_line)
      if (length(section) > width) width = length(section)
    }
    /^── prep: / { next }                       # prep is narrated under its pipeline
    /^── / {
      flush(); n_fail = n_warn = n_info = 0
      section = $2; banner_line = NR
      if (section == "done") { section = ""; next }
      next
    }
    /^[[:space:]]*FAIL:/ { n_fail++; next }
    /^[[:space:]]*WARN:/ { n_warn++; next }
    /^[[:space:]]*INFO:/ { n_info++; next }
    END {
      flush()
      if (width < length("stage")) width = length("stage")
      printf "  %-*s %5s %5s %5s   %-7s %6s\n", width, "stage", "FAIL", "WARN", "INFO", "verdict", "line"
      for (r = 1; r <= n_rows; r++) {
        split(rows[r], f, "\t")
        printf "  %-*s %5d %5d %5d   %-7s %6d\n", width, f[1], f[2], f[3], f[4], f[5], f[6]
      }
    }
  ' "$LOG_FILE" 2>/dev/null || true
}

prep_pipeline_safe() {
  local name="$1"; shift
  if ! prep_pipeline "$name" "$@"; then
    pipeline_failures+=("$name (prep)")
  fi
}

LOG_FILE="$REPO_ROOT/tmp/logs/pipeline/run/$(date -u '+%Y-%m-%dT%H%M%SZ').log"

# The whole-corpus tail: the root-level REDUCE, run once after every pipeline —
# for operations whose input spans them all (the pipelines' own run_tails fold
# one pipeline's corpus; this folds the union). First member: indexing sync,
# whose locators span claude chat, code sessions, and gemini — and whose
# staleness is invisible to a run that does not fold it — index.md goes on citing
# whatever it cited when it was last built. Same command-backed step
# discipline as the pipeline tails: the plan speaks `indexing sync`, and the
# gate holds it to command AND verb (a declared step=corpus).
#
# Membership: L9 — Currency (rsc/CALCULUS.md), which carries the CLOSURE and
# NECESSITY tests. indexing sync is here because its cell says
# run (machine-local, mechanical, CLOSURE holds); dashboard sync is NOT,
# because its captures are paid and out-of-run — CLOSURE fails, and a step
# here would render fresh-LOOKING pages over silently lagging semantics.
run_corpus_tail() {
  # Its own banner, so its atoms are attributed to it rather than to whichever pipeline
  # ran last — the table reads sections, and a reduce over everything is a section.
  # Not under --plan: the plan lists STEPS, and a banner is a log boundary, not a step —
  # the line above it ("then once, over the whole corpus") already says the same thing.
  [[ "${plan:-0}" == "1" ]] || echo "── corpus ────────────────────────────────────────────────────────────────"
  step indexing "$REPO_ROOT/src/run_python_script.sh" \
    "$REPO_ROOT/src/main/cli/indexing/indexing.py" sync
  # Bare noun DELIBERATELY (not the dropped-verb bug class the plan gate
  # guards): dashboard's read-only status IS its L9 mechanism, probed here so
  # its INFO currency atoms (re-render is free; captures lag the corpus) reach
  # the tail via hoisting. step_ok: a currency nudge informs, never gates.
  step_ok dashboard "$REPO_ROOT/src/main/pipeline/chat-exports/dashboard_status.sh"
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
    "$REPO_ROOT/src/main/pipeline/browser-captures/run.sh" --plan | sed 's/^/  /'
  fi
  if should_run chat-exports; then
    # printed by the same wrapper that runs it, so the plan cannot drift from the call
    ( plan=1; pair="$(prep_call chat-exports)" && read -r op impl <<< "$pair" && step "$op" "$impl" ) | sed 's/^/  /'
    "$REPO_ROOT/src/main/pipeline/chat-exports/run.sh" --plan | sed 's/^/  /'
  fi
  if should_run code-agents; then
    # printed by the same wrapper that runs it, so the plan cannot drift from the call
    ( plan=1; pair="$(prep_call code-agents)" && read -r op impl <<< "$pair" && step "$op" "$impl" ) | sed 's/^/  /'
    "$REPO_ROOT/src/main/pipeline/code-agents/run.sh" --plan | sed 's/^/  /'
  fi
  echo "  then once, over the whole corpus:"
  # shellcheck disable=SC2030,SC2031  # plan=1 deliberately CONFINED to the subshell
  ( plan=1; run_corpus_tail ) | sed 's/^/  /'
  echo "  tail: one row per stage — FAIL/WARN/INFO counts, the verdict it exited with, and where it begins in the log; failed pipelines with their error:/FAIL: lines quoted; the outputs line; log path"
}

main() {
  parse_args "$@"
  # The header anchors the log's evidence (#365): the room this machine is bound
  # to (or its stated absence — a worktree carries no binding), the commit the
  # tree stood at, and clean/dirty with the count. Every claim below dereferences
  # against this line instead of against archaeology.
  local room ref dirty
  room="$(cat "$REPO_ROOT/machine-name.txt" 2>/dev/null || echo '(unbound)')"
  ref="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null)"
  ref="${ref:-(detached)} @ $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '(no git)')"
  dirty="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | grep -c . || true)"
  [[ "$dirty" -eq 0 ]] && dirty="clean" || dirty="dirty ($dirty)"
  echo "$(basename "$0") $* — $(date -u '+%Y-%m-%dT%H:%M:%SZ') · room: $room · $ref, $dirty"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  # One item: the pipeline's own singular flag — browser-captures takes --browser-capture,
  # chat-exports --chat-export, code-agents --code-agent. Derived by dropping the plural's
  # 's' rather than listed, so a fourth pipeline needs no edit here. The corpus tail is not
  # run: it reduces over everything, and this invocation is about one datum.
  if [[ -n "$item" ]]; then
    "$REPO_ROOT/src/main/pipeline/$only/run.sh" "--${only%s}" "$item"
    return $?
  fi

  local -a pipeline_failures=()

  # Each pipeline runs over its DECLARED input root (pipeline.json's input), so the
  # path the wrapper passes and the path the pipeline documents cannot disagree.
  if should_run browser-captures; then
    run_pipeline_safe  browser-captures "$REPO_ROOT/$(input_of browser-captures)"
  fi

  if should_run chat-exports; then
    prep_pipeline_safe chat-exports
    run_pipeline_safe  chat-exports "$REPO_ROOT/$(input_of chat-exports)"
  fi

  if should_run code-agents; then
    prep_pipeline_safe code-agents
    run_pipeline_safe  code-agents "$REPO_ROOT/$(input_of code-agents)"
  fi

  # the whole-corpus reduce: over whatever is projected — idempotent, so a
  # --only run re-indexing the unchanged rest is silence, not distortion
  if ! run_corpus_tail 2>&1 | tee -a "$LOG_FILE"; then
    pipeline_failures+=("indexing (corpus tail)")
  fi

  echo "── done $(date -u '+%Y-%m-%dT%H:%M:%SZ') ───────────────────────────────────────────"
  # The tail is a TABLE and nothing else: one row per section, its atom counts beside the
  # verdict it exited with. The body already states every finding where it happened, with
  # the context of its section around it — reprinting those lines here would duplicate the
  # text and lose the context, which is what hoisting them did. A reader who wants detail
  # greps the sigil or diffs two logs; a reader who wants the shape of the run reads four
  # columns. The row is also where the two notions of failure meet, so `0 FAIL … failed`
  # is legible as the step defect it is rather than split across two paragraphs.
  # bash 3.2 expands an EMPTY array under `set -u` as unbound, so the guard is not
  # decoration: without it a clean run dies here, before printing its own summary.
  local failed_csv="" one
  if [[ ${#pipeline_failures[@]} -gt 0 ]]; then
    for one in "${pipeline_failures[@]}"; do failed_csv="${failed_csv:+$failed_csv,}${one%% *}"; done
  fi
  atom_table "$failed_csv"
  echo "  (each pipeline stage runs alone as: yoga pipeline run <stage>; corpus is the reduce over all)"
  echo "  (line = where that stage begins in this log; each finding is stated there, in place)"
  if [[ ${#pipeline_failures[@]} -eq 0 ]]; then
    echo "usr gate: PASS — all pipelines completed"
  else
    echo "usr gate: FAIL — failed pipelines:"
    local errs
    for f in "${pipeline_failures[@]}"; do
      echo "  $f"
      errs="$(section_error_lines "$f")"
      [[ -n "$errs" ]] && printf '%s\n' "$errs" | sed 's/^/    /'
      case "$f" in
        "chat-exports (prep)")   echo "    → populate data/input/claude/chat/bulk-export/ with a bulk export (see src/main/pipeline/chat-exports/require_export.sh --help)" ;;
        "code-agents (prep)")  echo "    → check data/input/claude/code/machine-transport/ (the store) and ext/mnt/claude-code-projects/ (transport's source) symlinks" ;;
        *) [[ -z "$errs" ]] && echo "    → scroll up: the failing step prints its error and the path of its own log" ;;
      esac
    done
  fi
  # The usr-actor's next acts, and nothing else: the run's outputs, and reading them
  # served. The data-tier coupling this line once narrated (pipelines move what the
  # dev gate's data tier reads) is enforced where it bites — the dev gate's own
  # artifact-staleness check, at the next commit, in the dev-actor's hands (#342).
  echo "outputs: data/output/markdown/index.md · read served: yoga server start --daemon (http://localhost:8182)"
  echo "Log: $LOG_FILE"
  # The verdict must leave this function: callers chain on $?.
  return $(( ${#pipeline_failures[@]} > 0 ))
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
# `set -o pipefail` makes the pipeline's status the first non-zero in it, so main's
# verdict survives the tee rather than being replaced by tee's own success.
main "$@" 2>&1 | tee "$LOG_FILE"
