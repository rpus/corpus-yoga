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

# Sourced file: SELF and _self_dir here overwrite the sourcing script's —
# safe only because every sourcer's own guard has already run by its source line.
SELF='src/main/steps.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEPS_REPO="${_self_dir%/"${SELF%/*}"}"
[[ "${STEPS_REPO}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

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

# name · args · where it lives. A step that is also a corpus-yoga command is printed AS that
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
    label="corpus-yoga $name"
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

# ── Next-free dispatch (#395) ─────────────────────────────────────────────────
# Independent tasks are enumerated capacity-blind and handed serially to the
# next free worker; each task's whole output is buffered and emitted in
# ENUMERATION ORDER — the dev gate's _call_many discipline for the usr gate:
# the dispatch is invisible in the artifact, bytes equal the serial loop's.
# The pool is a FIFO of worker tokens (bash 3.2 has no wait -n): the dispatcher
# blocks on the FIFO until a worker frees, so no task ever waits on a barrier.
# YOGA_JOBS lives HERE and nowhere else — enumerators and workers never know it.
YOGA_JOBS="${YOGA_JOBS:-$( (sysctl -n hw.ncpu || nproc || echo 4) 2>/dev/null | head -1 )}"

# dispatch <fn> <task>... — run fn once per task on the next free worker.
# Leaves each task's output in $DISPATCH_DIR/<i>.out and status in
# $DISPATCH_DIR/<i>.rc (enumeration order); sets DISPATCH_N. A caller that
# needs per-task post-processing reads the files itself and ends with
# dispatch_done; one that streams uses dispatch_emit.
dispatch() {
  local fn="$1"; shift
  DISPATCH_DIR="$(mktemp -d "${TMPDIR:-/tmp}/dispatch.XXXXXX")"
  DISPATCH_N=0
  mkfifo "$DISPATCH_DIR/token"
  exec 9<>"$DISPATCH_DIR/token"
  local slot=0
  while [[ "$slot" -lt "$YOGA_JOBS" ]]; do printf '\n' >&9; slot=$((slot + 1)); done
  local task
  for task in "$@"; do
    read -r -u 9 _   # blocks until a worker slot frees — next-free dispatch
    # set +e inside the worker: the rc file must be written whatever fn did;
    # DISPATCH_I lets a worker deposit sidecars (counters) beside its own buffers.
    # shellcheck disable=SC2034  # DISPATCH_I is read inside fn by dynamic scope (the sidecar index)
    ( set +e; DISPATCH_I="$DISPATCH_N"; "$fn" "$task" >"$DISPATCH_DIR/$DISPATCH_N.out" 2>&1
      echo $? >"$DISPATCH_DIR/$DISPATCH_N.rc"
      printf '\n' >&9 ) &
    DISPATCH_N=$((DISPATCH_N + 1))
  done
  wait
  exec 9>&-
}

# dispatch_emit — the streaming face: cat every buffered output in enumeration
# order, then clean up; returns 1 iff any task did.
dispatch_emit() {
  local i=0 rc=0 irc
  while [[ "$i" -lt "$DISPATCH_N" ]]; do
    cat "$DISPATCH_DIR/$i.out"
    irc="$(cat "$DISPATCH_DIR/$i.rc" 2>/dev/null || echo 1)"
    [[ "$irc" -eq 0 ]] || rc=1
    i=$((i + 1))
  done
  dispatch_done
  return "$rc"
}

dispatch_done() { rm -rf "$DISPATCH_DIR"; unset DISPATCH_DIR DISPATCH_N; }
