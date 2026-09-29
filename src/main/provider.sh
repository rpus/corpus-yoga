# shellcheck shell=bash
# provider.sh — the shell face of src/main/provider.py's signature() (#704): the Signature
# triad the commit hook stamps and every verb's log opens with. Sourced, never run.
#
#   provider_signature <repo-root>   # prints <machine>/<provider>/<session>, or <machine>
#
# The derivation runs the venv's python through src/run_python_script.sh (#478); where that
# cannot run - no venv on this machine - the machine alone is claimed from machine-name.txt,
# held to the charset a machine label may carry, or 'unbound' where there is none: the
# header attests only what the environment positively provides.
provider_signature() {
  local repo="$1" triad
  triad="$("$repo/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import provider; print(provider.signature())' "$repo/src/main" 2>/dev/null)" \
    || triad="$(tr -cd 'A-Za-z0-9_-' < "$repo/machine-name.txt" 2>/dev/null)"
  echo "${triad:-unbound}"
}
