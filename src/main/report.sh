# shellcheck shell=bash
# report.sh - what an act reports after its lines (#801, #875), for the bash verbs:
# tail_of <verdict> [<command> <does>]... prints next: - the room's to-do re-read after the
# effect, each extra command beside it, corpus-yoga status last - then the verdict as the
# last line, through src/main/facts.py, so that no bash verb prints a tail of its own.
# Sourced after the script's root is known as REPO_DIR or REPO_ROOT.
tail_of() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import corpus, facts
extra = dict(zip(sys.argv[3::2], sys.argv[4::2]))
facts.report(None, {**corpus.room_next(), **extra}, sys.argv[2])' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}
