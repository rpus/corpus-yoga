# shellcheck shell=bash
# send.sh - a send run by its name, the shell face (sourced by bash, not executed); send.py is
# python's, and says what a send is. The one reading of CORPUS_YOGA_NO_SEND in this language,
# and the one place a send is refused, bounded and narrated (issues/1022). Sourced after
# src/main/report.sh and src/main/enact.sh, whose faces it runs through.
#
#   send <face> <name> [args...]   the send the dispatched declaration names <name>: its
#                                  command and the args, through enact's face - enact,
#                                  labour, query, quote, quiet or attempt
#   send_cleared <name>            whether the named send may run - declared and not refused -
#                                  for an act that must stop before its local steps where a
#                                  later send would be refused
#   send_runs <name>               what the named send runs, as its declaration writes it
#
# An undeclared name returns 2 and says so; refused, a send is narrated as refused and
# returns SEND_REFUSED, whatever its entry's `refused` says - a caller whose send degrades
# says the reading unverified, one whose send is the work fails the act.

SEND_REFUSED=75

# send_dispatched <declaration>: the declaration as the running code is handed it, the value of
# CORPUS_YOGA_DECLARATION - its address and its sends, the verb's own entries over its noun's,
# read now, once (issues/1036); send.py's dispatched() is its python face.
send_dispatched() {
  local root="${REPO_DIR:-${REPO_ROOT:-$STEPS_REPO}}" noun="${1%/*}"
  noun="$noun/${noun##*/}.json"
  jq -cn --arg declaration "$1" --slurpfile noun <(cat "$root/$noun" 2>/dev/null || echo '{}') --slurpfile verb "$root/$1" \
    '{declaration: $declaration, sends: (($noun[0].sends // {}) + ($verb[0].sends // {}))}'
}

# _send_entry <name>: the declared command, a tab, and what refusal does to it - from the sends
# the running code was handed at dispatch, never from the tree as it stands.
_send_entry() {
  local handed="${CORPUS_YOGA_DECLARATION:-}"
  [[ -n "$handed" ]] || handed='{}'
  if ! jq -er --arg name "$1" '.sends[$name] | select(.) | [.runs, .refused] | @tsv' <<< "$handed" 2>/dev/null; then
    echo "error: $(jq -r '.declaration // "no declaration"' <<< "$handed" 2>/dev/null || echo 'no declaration') declares no send $1" >&2
    return 2
  fi
}

send_runs() {
  local declared
  declared="$(_send_entry "$1")" || return 2
  printf '%s\n' "${declared%%$'\t'*}"
}

send_cleared() {
  local declared runs
  declared="$(_send_entry "$1")" || return 2
  runs="${declared%%$'\t'*}"
  if [[ "${CORPUS_YOGA_NO_SEND:-}" == "1" ]]; then
    narrate opening "$runs" >&2
    narrate outcome "$runs" 'did NOT' 'CORPUS_YOGA_NO_SEND=1 refuses it' >&2
    return "$SEND_REFUSED"
  fi
}

send() {
  local face="$1" name="$2" runs
  shift 2
  send_cleared "$name" || return
  runs="$(send_runs "$name")"
  local -a argv
  read -ra argv <<< "$runs"
  # a program in the venv is preferred to one on PATH, as send.py prefers one beside its interpreter
  [[ -n "${CORPUS_YOGA_VENV:-}" && -x "$CORPUS_YOGA_VENV/bin/${argv[0]}" ]] && argv[0]="$CORPUS_YOGA_VENV/bin/${argv[0]}"
  "$face" "${argv[@]}" "$@"
}
