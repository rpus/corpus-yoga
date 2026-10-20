# shellcheck shell=bash
# report.sh - what an act reports after its lines (issues/801, issues/896), for the bash verbs:
# effect <line> [<command> <does>]... hands the act's effect line, and each command the act
# names beside the room's to-do, to the launcher, which replies with next: and the effect
# (src/main/reply.py); where no launcher asked - an inner invocation, a step of another
# verb - the effect line is printed as the last line. Through src/main/facts.py, so that
# no bash verb prints a tail of its own. Sourced after the script's root is known as
# REPO_DIR or REPO_ROOT.
# phrase <phrase> [<place>=<value>]...: a phrase a status says, quoted as its noun's
# declaration holds it, its places filled - facts.phrase's shell twin (issues/909, issues/935).
phrase() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
places = dict(part.split("=", 1) for part in sys.argv[3:])
print(facts.phrase(sys.argv[2], **places))' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}

effect() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
extra = dict(zip(sys.argv[3::2], sys.argv[4::2]))
facts.report(None, sys.argv[2], extra or None)' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}
