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

# narrate item <text> [<offset>] | opening <command> | outcome <command> <did|did NOT> <words> | read <command> <answer>:
# one event of a record as a list item at the narration depth, facts.narration's shell face
# (issues/805) - the faces of enact.sh say through it. opening prints the item's head alone,
# before the command runs; outcome the lines beneath it, after.
narrate() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
mode, rest = sys.argv[2], sys.argv[3:]
if mode == "item": said = facts.lines([rest[0]], facts.depth() + (int(rest[1]) if len(rest) > 1 else 0))
elif mode == "opening": said = facts.narration({rest[0]: {"did": "done"}})[:1]
elif mode == "outcome": said = facts.narration({rest[0]: {rest[1]: rest[2]}})[1:]
elif mode == "read": said = facts.narration({rest[0]: rest[1].splitlines() if "\n" in rest[1] else rest[1]})
else: raise SystemExit(f"narrate: {mode} is no mode")
print("\n".join(said))' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}

# say <phrase> [<place>=<value>]...: a phrase said as an event of the record, a list item at
# the narration depth.
say() { narrate item "$(phrase "$@")"; }

# opening <key> [<offset>] and pair <key> <value> [<offset>]: a mapping's key line, and one pair,
# at the narration depth plus the offset; a value of {} is the empty mapping - facts.opening's and facts.lines's shell faces, for a verb that prints its mapping
# progressively.
opening() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
print(facts.opening(sys.argv[2], facts.depth() + int(sys.argv[3]) if len(sys.argv) > 3 else facts.depth()))' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}

pair() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
value = {} if sys.argv[3] == "{}" else sys.argv[3]   # the one literal that is a shape, not a word: an empty mapping
print("\n".join(facts.lines({sys.argv[2]: value}, facts.depth() + int(sys.argv[4]) if len(sys.argv) > 4 else facts.depth())))' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}

effect() {
  "${REPO_DIR:-$REPO_ROOT}/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import facts
extra = dict(zip(sys.argv[3::2], sys.argv[4::2]))
facts.report(None, sys.argv[2], extra or None)' "${REPO_DIR:-$REPO_ROOT}/src/main" "$@"
}
