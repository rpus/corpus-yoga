# shellcheck shell=bash
# steps.sh — the step vocabulary shared by the pipeline runners (sourced by bash,
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
# the truth at the name level: a step whose script grows a verb becomes a
# different call under an unchanged name. Machine paths are still never printed, so plan
# output stays deterministic; --plan needs no inputs, writes nothing, exits 0.
#
#   step       <name> <cmd...>                    # unconditional
#   step_if    <guard> <note> <name> <cmd...>     # runs iff guard is "1"
#   step_ok    <name> <cmd...>                    # informational: never gates
#   step_if_ok <guard> <note> <name> <cmd...>     # both of the above

STEPS_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# the step's argv minus anything path-shaped: the verbs and flags that are part of the
# program, without the machine paths that would break plan determinism. Called with the
# arguments ONLY — never the command: a command that is not path-shaped survives the
# filter and lands in the plan as an argument of itself (`ensure_session_dir mkdir -p`,
# `prune_departed_gen prune_departed_projects`) (#45).
plan_args() {
  local arg out=''
  for arg in "$@"; do [[ "$arg" == */* ]] || out+=" $arg"; done
  echo "$out"
}

# The repo-relative file a step is implemented in — the third thing every plan line must
# name (#45). Every path here is repo-relative, so the plan stays deterministic: only
# ABSOLUTE paths were ever the risk, and dropping the argument threw away the location
# instead of stripping the machine part of it.
#
# Four shapes, none of them curated:
#   run_python_script.sh <script.py>  the wrapper is not the operation — the script is
#   a path                            the command IS the file
#   a shell function                  bash knows where it was defined (extdebug)
#   a builtin, inline                 the operation has no file of its own: the runner's
plan_impl() {
  local caller="$1" cmd="$2"; shift 2
  local arg
  if [[ "$cmd" == */run_python_script.sh ]]; then
    for arg in "$@"; do [[ "$arg" == *.py ]] && { cmd="$arg"; break; }; done
  fi
  if [[ "$cmd" == */* ]]; then
    echo "${cmd#"$STEPS_REPO/"}"
    return
  fi
  local loc
  loc="$(shopt -s extdebug; declare -F "$cmd" 2>/dev/null)" || loc=''
  if [[ -n "$loc" ]]; then
    loc="${loc##* }"
    echo "${loc#"$STEPS_REPO/"}"
    return
  fi
  echo "${caller#"$STEPS_REPO/"}"
}

# name · args · where it lives. A step that is also a yoga command is printed AS that
# command, which is how the line says it is typeable: no legend, no marker column —
# the reader types what they see.
plan_line() {
  local caller="$1" name="$2"; shift 2
  local cmd="$1"; shift
  local args impl
  args="$(plan_args "$@")"
  impl="$(plan_impl "$caller" "$cmd" "$@")"
  local label="$name"
  if [[ -f "$STEPS_REPO/src/main/cli/$name/$name.json" ]] || [[ -f "$STEPS_REPO/src/main/cli/$name.json" ]]; then
    label="yoga $name"
  fi
  printf '  %-58s %s' "$label$args" "$impl"
}

step() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then plan_line "${BASH_SOURCE[1]}" "$name" "$@"; echo; return 0; fi
  "$@"
}

step_if() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "$(plan_line "${BASH_SOURCE[1]}" "$name" "$@") (only $note)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@"
}

step_ok() {
  local name="$1"; shift
  if [[ "${plan:-0}" == "1" ]]; then echo "$(plan_line "${BASH_SOURCE[1]}" "$name" "$@") (informational; never gates)"; return 0; fi
  "$@" || true
}

step_if_ok() {
  local guard="$1" note="$2" name="$3"; shift 3
  if [[ "${plan:-0}" == "1" ]]; then echo "$(plan_line "${BASH_SOURCE[1]}" "$name" "$@") (only $note; informational; never gates)"; return 0; fi
  if [[ "$guard" != "1" ]]; then return 0; fi
  "$@" || true
}

# ── The per-datum fan (#360) ──────────────────────────────────────────────────
# Independent per-datum work runs YOGA_JOBS-wide, each datum's whole output
# buffered and emitted in ITEM ORDER — the dev gate's _call_many discipline for
# the usr gate: the fan is invisible in the artifact, bytes equal the serial
# loop's. bash 3.2 has no job pool (wait -n), so the fan runs in WAVES of the
# width — stragglers idle some cores between waves, still ~width x serial.
YOGA_JOBS="${YOGA_JOBS:-$( (sysctl -n hw.ncpu || nproc || echo 4) 2>/dev/null | head -1 )}"

# fan_run <fn> <item>... — run fn once per item, waves of YOGA_JOBS. Leaves each
# item's output in $FAN_DIR/<i>.out and status in $FAN_DIR/<i>.rc (item order);
# sets FAN_N. A caller that needs per-item post-processing reads the files
# itself and ends with fan_done; one that streams uses fan_emit.
fan_run() {
  local fn="$1"; shift
  FAN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/fan.XXXXXX")"
  FAN_N=0
  local wave=0 item
  for item in "$@"; do
    # set +e inside the worker: the rc file must be written whatever fn did;
    # FAN_I lets a worker deposit sidecars (counters) beside its own buffers.
    # shellcheck disable=SC2034  # FAN_I is read inside fn by dynamic scope (the sidecar index)
    ( set +e; FAN_I="$FAN_N"; "$fn" "$item" >"$FAN_DIR/$FAN_N.out" 2>&1
      echo $? >"$FAN_DIR/$FAN_N.rc" ) &
    FAN_N=$((FAN_N + 1))
    wave=$((wave + 1))
    if [[ "$wave" -ge "$YOGA_JOBS" ]]; then wait; wave=0; fi
  done
  wait
}

# fan_emit — the streaming face: cat every buffered output in item order, then
# clean up; returns 1 iff any item did.
fan_emit() {
  local i=0 rc=0 irc
  while [[ "$i" -lt "$FAN_N" ]]; do
    cat "$FAN_DIR/$i.out"
    irc="$(cat "$FAN_DIR/$i.rc" 2>/dev/null || echo 1)"
    [[ "$irc" -eq 0 ]] || rc=1
    i=$((i + 1))
  done
  fan_done
  return "$rc"
}

fan_done() { rm -rf "$FAN_DIR"; unset FAN_DIR FAN_N; }
