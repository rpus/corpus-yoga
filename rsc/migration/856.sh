#!/usr/bin/env bash
# rsc/migration/856.sh - a held gemini unit holds the live store's files at their own
# names and relative paths (issues/856): the transcripts at .system_generated/logs/ under the
# session, the step database at conversations/<uuid>.db; summary.json stays at the top.
# Every unit under data/input and under this room's stage moves.
set -euo pipefail
SELF='rsc/migration/856.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for root in data/input tmp/stage/input; do
  for session in "$root"/gemini/code/machine-transport/*/*/*/; do
    [[ -d "$session" ]] || continue
    session="${session%/}"
    for transcript in transcript.jsonl transcript_full.jsonl; do
      move "$session/$transcript" "$session/.system_generated/logs/$transcript"
    done
    move "$session/conversation.db" "$session/conversations/${session##*/}.db"
  done
done
