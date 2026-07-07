# steps.sh — the step vocabulary shared by the RUNME entry points (sourced,
# not executed).
#
# A RUNME body is a FLAT list of step calls — first-order style: no nesting,
# just named calls — and that ONE list is both the executor and the plan.
# With plan=1 (each RUNME's --plan flag) every step prints its name instead of
# running, so the printed plan can never drift from what executes. Conditional
# steps always appear in the plan, annotated with their condition — the plan
# shows the whole program, not the current flags. Plan output is deterministic:
# step names and condition notes only, never machine paths; --plan needs no
# inputs, writes nothing, and exits 0.
#
#   step       <name> <cmd...>                    # unconditional
#   step_if    <guard> <note> <name> <cmd...>     # runs iff guard is "1"
#   step_ok    <name> <cmd...>                    # informational: never gates
#   step_if_ok <guard> <note> <name> <cmd...>     # both of the above

step() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name"; return 0; fi
  "$@"
}

step_if() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name (only $note)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@"
}

step_ok() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name (informational; never gates)"; return 0; fi
  "$@" || true
}

step_if_ok() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "  $name (only $note; informational; never gates)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@" || true
}
