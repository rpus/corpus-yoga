# shellcheck shell=bash
# send.sh — the shell face of the send switch (sourced by bash, not executed).
#
# The ONE fact has two faces, one per language: src/main/send.py for python, this file for
# bash — each the only reader of YOGA_NO_SEND in its language, both named by
# effects.send_switch_read_once. Two DECLARED readings, one per language, is not the
# accidental pair that check exists to prevent: bash cannot import a python module, and
# before this file existed no shell command could honour the switch at all (the yoga forge
# census, PR #113).
#
# The two ways of honouring refusal, mirroring send.py:
#   may_send          the send only enriches a report — the caller degrades to UNVERIFIED,
#                     exactly as it already renders an unreachable remote
#   assert_may_send   the send IS the work — refusal prints the one sentence and fails
#
# The refusal sentence is composed here, once, word-for-word send.py's SendRefused — so no
# call site can word it differently and every reader meets one phrasing.

may_send() {
  [[ "${YOGA_NO_SEND:-}" != "1" ]]
}

assert_may_send() {
  may_send || { echo "YOGA_NO_SEND=1 refuses this send: $1" >&2; return 1; }
}
