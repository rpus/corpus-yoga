# shellcheck shell=bash
# steps.sh — the step vocabulary shared by the pipeline runners (sourced,
# not executed — hence a shell directive rather than a shebang).
#
# A runner's body is a FLAT list of step calls — first-order style: no nesting,
# just named calls — and that ONE list is both the executor and the plan.
# With plan=1 (each runner's --plan flag) every step prints its name instead of
# running, so the printed plan can never drift from what executes. Conditional
# steps always appear in the plan, annotated with their condition — the plan
# shows the whole program, not the current flags. Each step prints its name
# plus its non-path arguments (verbs, flags): an argument is part of the
# program, and a plan that hides argv can lie at the verb level while telling
# the truth at the name level (found 2026-07-22: memories.py had
# silently become a bare status call when its script grew a sync verb — the
# plan looked unchanged). Machine paths are still never printed, so plan
# output stays deterministic; --plan needs no inputs, writes nothing, exits 0.
#
#   step       <name> <cmd...>                    # unconditional
#   step_if    <guard> <note> <name> <cmd...>     # runs iff guard is "1"
#   step_ok    <name> <cmd...>                    # informational: never gates
#   step_if_ok <guard> <note> <name> <cmd...>     # both of the above

# the step's argv minus anything path-shaped: the verbs and flags that are part
# of the program, without the machine paths that would break plan determinism
plan_args() {
  local arg out=''
  for arg in "$@"; do [[ "$arg" == */* ]] || out+=" $arg"; done
  echo "$out"
}

step() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name$(plan_args "$@")"; return 0; fi
  "$@"
}

step_if() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name$(plan_args "$@") (only $note)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@"
}

step_ok() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name$(plan_args "$@") (informational; never gates)"; return 0; fi
  "$@" || true
}

step_if_ok() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name$(plan_args "$@") (only $note; informational; never gates)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@" || true
}
