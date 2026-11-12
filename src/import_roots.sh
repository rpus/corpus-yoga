# shellcheck shell=bash
# import_roots.sh - python's import roots for a launcher (sourced, not executed): the roots
# pyrightconfig.json declares, the one list the editor, the type checker and the running code
# read (issues/1038). Read with the interpreter about to run - no tool python itself lacks, so
# that the machine report runs before anything else is installed - once per repository: a
# python it starts inherits them.

# python_cache <repo>: python's bytecode kept under <repo>/tmp/cache/python, never beside
# the sources (issues/1052), so that a module moved or removed leaves nothing under src.
python_cache() {
  export PYTHONPYCACHEPREFIX="$1/tmp/cache/python"
}

# import_roots <repo> <python>: PYTHONPATH exported as <repo>'s declared roots, and the
# bytecode's place with it - every python a launcher starts passes here.
import_roots() {
  python_cache "$1"
  [[ "${CORPUS_YOGA_IMPORT_ROOTS:-}" == "$1" && -n "${PYTHONPATH:-}" ]] && return 0
  PYTHONPATH="$("$2" -c 'import json, sys; print(":".join(sys.argv[1] + "/" + root for root in json.load(open(sys.argv[1] + "/pyrightconfig.json"))["extraPaths"]))' "$1")" || return
  export PYTHONPATH CORPUS_YOGA_IMPORT_ROOTS="$1"
}
