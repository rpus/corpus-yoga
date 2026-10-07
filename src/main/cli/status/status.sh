#!/usr/bin/env bash
# src/main/cli/status/status.sh — what this machine has, and what it still needs.
#
# The BARE noun is strictly read-only: no directories created, no symlinks, no venv, no
# installs. Safe as the first command on a fresh clone, which is the whole point of it.
#
# `sync` is the effecting verb, and prints the remedies the report holds rather than the
# report. It is --apply-gated because it writes outside the repo, and it runs only what is
# the repo's to run: the mint of its venv, and each remedy its declaration names - the
# parsers, the live stores' mounts, the hooks. A brew install is not ours to perform; the
# machine binding is a decision, not a derivation.
#
# Exit status: non-zero only if a required tool (jq, Python 3) is missing.
#
# Usage:
#   src/main/cli/status/status.sh              # what still needs attention; a section with nothing to say is not shown
#   src/main/cli/status/status.sh --show-all   # the full report, what is satisfied included
#
# A row is keyed by what it is about, its value what stands; the commands that act on it stand beside it.
# corpus-yoga pipeline run writes only data/input/, tmp/cache/, data/output/, tmp/logs/ and the venv.

set -euo pipefail
SELF='src/main/cli/status/status.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"
: "${CORPUS_YOGA_VENV:=$HOME/venvs/general}"
# shellcheck source=src/main/send.sh
source "$REPO_ROOT/src/main/send.sh"   # assert_may_send — the shell face of CORPUS_YOGA_NO_SEND (#29)
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_ROOT/src/main/cli/parse_argv.sh"

SHOW_ALL=0
SYNC=0
APPLY=0
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      sync)       SYNC=1; shift ;;
      --apply)    APPLY=1; shift ;;
      --show-all) SHOW_ALL=1; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "status: NOT DONE - $1 is no word it takes; the words are --show-all, or sync [--apply]" >&2; exit 2 ;;
    esac
  done
}

# Failures-only by default: ✓ (satisfied) lines are withheld unless --show-all, and a
# section header prints lazily — only when its first shown line (– or ✗) appears — so an
# all-satisfied section vanishes entirely: the default is the short "what still needs
# attention" list.
# The report's rows (#753, #763, #771): section \t kind \t subject \t what stands
# [\t command \t what it does]..., collected as the checks run and said once, as one
# shape, by report.py. A row is keyed by what it is about - a tool, a hook, a pipeline and
# its provider - never by its kind, and a subject may nest: `a / b` stands beneath `a`, so
# a row's last part names the property its value is of (`jq / installed`, `no - ...`) or
# is the thing itself by its address. A command is a column of its own, never a clause of
# the text, and stands beside the row's last part, in the mapping that holds it. A section
# is named and no more: what a section is, the help says.
#   sec   <name>
#   ok    <subject> <what stands>                            # only in the full report
#   info  <subject> <what stands>                            # how things stand: it takes no command
#   todo  <subject> <what stands> [<command> <what it does>]...
#   bad   <subject> <what stands> <command> <what it does> [...]   # required, and absent
#   graft <section> <noun> <pointer>                         # what a noun's own status says there (#777)
# What a noun's status says is taken from that status, never probed a second way: a graft
# row names the noun and the spot of its facts, and report.py loads them - whole in the
# full report, and otherwise what holds a remedy.
_hdr=""
_rows=()
sec()    { _hdr="$1"; }
_row() {
  local row="$_hdr"$'\t'"$1"$'\t'"$2"$'\t'"$3"; shift 3
  while [[ $# -gt 0 ]]; do row+=$'\t'"$1"$'\t'"${2-}"; shift; [[ $# -eq 0 ]] || shift; done
  _rows+=("$row")
}
ok()     { if (( SHOW_ALL )); then _row ok "$1" "$2"; fi; }
info()   { [[ $# -eq 2 ]] || { echo "status: info takes a subject and what stands - a row with a command is a todo or a bad" >&2; exit 2; }; _row note "$1" "$2"; }
# todo is a row the reader acts on, and only it and `bad` carry commands; a command is the
# report's data, so `sync` reads what to run from the report itself (#777), not from a tag.
todo()   { _row todo "$@"; }
bad()    { _row missing "$@"; }
graft()  { _rows+=("corpus-yoga $1"$'\t'"graft"$'\t'"$1"$'\t'"$2"); }   # <noun> <pointer>: the section is the command, its content what stands at the pointer

# The rows said through report.py: the report (`report`), or the remedies it
# holds as rows of their own - command \t what it does \t where it stands (`remedies`).
# Under the venv's python where it exists, under python3 before the venv is minted, and as
# the bare rows where neither runs (a row above says so).
_say() {
  local mode="$1" python
  if [[ -x "$CORPUS_YOGA_VENV/bin/python" ]]; then python="$CORPUS_YOGA_VENV/bin/python"
  elif command -v python3 &>/dev/null; then python="$(command -v python3)"
  else
    [[ "$mode" == report ]] || return 0
    local r
    for r in ${_rows[@]+"${_rows[@]}"}; do echo "$r"; done
    return 0
  fi
  local rows_file
  rows_file="$(mktemp "${TMPDIR:-/tmp}/status.XXXXXX")"
  printf '%s\n' ${_rows[@]+"${_rows[@]}"} > "$rows_file"
  CORPUS_YOGA_VENV="$CORPUS_YOGA_VENV" "$python" "$REPO_ROOT/src/main/cli/status/report.py" "$mode" "$rows_file" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$SHOW_ALL"
  rm -f "$rows_file"
}
# The sync, spelt as the reader can run it at the moment the row is read: through the
# launcher once the venv exists (the launcher refuses without one), else by its script.
sync_remedy() {
  if [[ -x "$CORPUS_YOGA_VENV/bin/python" ]]; then echo "corpus-yoga status sync --apply"
  else echo "./src/main/cli/status/status.sh sync --apply"; fi
}

count_glob_dirs() {
  local n=0 d
  for d in "$@"; do
    [[ -d "$d" ]] && n=$((n + 1))
  done
  echo "$n"
}

check_tools() {
  sec "tools"
  if command -v jq &>/dev/null; then
    ok jq "$(jq --version 2>/dev/null)"
  else
    bad "jq / installed" "no - no pipeline runs without it" "brew install jq" "installs it"
  fi
  if command -v python3 &>/dev/null; then
    ok python3 "$(python3 --version 2>&1) - it mints the venv; everything else runs the venv's python (#478)"
  else
    bad "python3 / installed" "no - nothing runs without it, the CLI included" "brew install python" "installs it"
  fi
  # Informational, never a ✗: absent, the gate skips its type check and still gates
  # deterministically. pyright is Pylance's own engine and reads the same
  # pyrightconfig.json the editor does — one declaration, three readers. It is a python
  # package, so the venv this repo builds carries it; shellcheck below is not, which is
  # why one arrives with `corpus-yoga pipeline run` and the other needs brew.
  # Where the GATE looks, in the same order: $CORPUS_YOGA_VENV/bin first, then PATH. Asking
  # `command -v` alone reported "not found" on any shell without the venv activated —
  # while the venv held it and corpus-yoga test run used it — so the report contradicted both
  # the gate and its own requirements line a few rows below.
  local pyright_bin=""
  if [[ -x "$CORPUS_YOGA_VENV/bin/pyright" ]]; then
    pyright_bin="$CORPUS_YOGA_VENV/bin/pyright"
  elif command -v pyright &>/dev/null; then
    pyright_bin="$(command -v pyright)"
  fi
  if [[ -n "$pyright_bin" ]]; then
    ok pyright "$("$pyright_bin" --version 2>/dev/null | head -1 | awk '{print $2}')"
  else
    todo "pyright / installed" "no - corpus-yoga test run skips its type check; it is in src/requirements.txt" "$(sync_remedy)" "installs the requirements"
  fi
  # Informational, never a ✗: the gate skips its shellcheck pass when the tool is absent,
  # so a clone without it still gates deterministically — it simply lints nothing, and
  # this is the one place that says so.
  if command -v shellcheck &>/dev/null; then
    ok shellcheck "$(shellcheck --version | awk '/^version:/ {print $2}')"
  else
    todo "shellcheck / installed" "no - corpus-yoga test run skips its shell lint" "brew install shellcheck" "installs it"
  fi
  # Informational, never a ✗: the gate's mcp.reproducible check (corpus-yoga mcp reproduce)
  # runs upstream's generator in a node container, and skips when no docker daemon
  # answers - a clone without one still gates deterministically. Two states short of
  # ready, told apart because their remedies differ: no docker at all, or docker
  # installed with its daemon not running.
  if command -v docker &>/dev/null; then
    local docker_server
    if docker_server="$(docker info --format '{{.ServerVersion}}' 2>/dev/null)" && [[ -n "$docker_server" ]]; then
      ok "docker / daemon" "$docker_server"
    else
      todo "docker / daemon" "not running - corpus-yoga test run skips mcp.reproducible and corpus-yoga mcp reproduce refuses" "open -a Docker" "starts Docker Desktop"
    fi
  else
    todo "docker / installed" "no - corpus-yoga test run skips mcp.reproducible and corpus-yoga mcp reproduce refuses" "brew install --cask docker" "installs it"
  fi
  # The generated parsers are the grammar noun's to say (#777): its status is grafted
  # after the tools. Here, the tool that generates them: antlr4 (antlr4-tools, a python
  # package the venv carries) running the tool jar on the machine's java.
  if [[ -x "$CORPUS_YOGA_VENV/bin/antlr4" ]]; then
    if command -v java &>/dev/null; then
      ok "antlr4 and java" "antlr4-tools, java $(java -version 2>&1 | head -1 | sed -E 's/^[^"]*"([^"]*)".*/\1/')"
    else
      todo "java / installed" "no - antlr4 has no runtime to run its tool on; corpus-yoga grammar sync refuses and corpus-yoga test run cannot hold the parsers current" "brew install openjdk" "installs it"
    fi
  else
    todo "antlr4 / installed" "no - corpus-yoga grammar sync refuses and corpus-yoga test run cannot hold the parsers current; it is in src/requirements.txt" "$(sync_remedy)" "installs the requirements"
  fi
  ok bash "$BASH_VERSION (3.2+ suffices)"
}

check_venv() {
  sec "venv"
  if [[ -x "$CORPUS_YOGA_VENV/bin/python" ]]; then
    ok "$CORPUS_YOGA_VENV / minted" "$("$CORPUS_YOGA_VENV/bin/python" --version 2>&1); CORPUS_YOGA_VENV= names another"
  else
    todo "$CORPUS_YOGA_VENV / minted" "no - nothing python runs, corpus-yoga included (#478); CORPUS_YOGA_VENV= names another" "$(sync_remedy)" "mints it and installs src/requirements.txt"
  fi
}

# check_dependencies <header> <manifest> <extract> <probe> <subject> <remediation>
#   One reporter for every pinned-dependency manifest. Both manifests hold one item
#   per non-comment/blank line by construction, so the read/count/report is shared;
#   only what varies is passed in — <extract> (a function: `<extract> <line>` echoes
#   the item id) and <probe> (a function: `<probe> <item> <line>` exits 0 and echoes a
#   version token if satisfied, else non-zero), plus the <subject>/<remediation>
#   wording. Each manifest supplies a <name>_extract / <name>_probe pair; the test
#   can't be a mere regex because it differs — a distribution-metadata lookup vs a
#   file existence check. Absence is only ever an informational –, never a ✗.
check_dependencies() {
  local header="$1" manifest="$2" extract="$3" probe="$4" subject="$5" remediation="$6"
  sec "$header"
  if [[ ! -f "$manifest" ]]; then
    info manifest "not found (unexpected) - nothing can say what this machine is missing"
    return
  fi
  local detail="" seen="|" missing="" total=0 got=0 line item tok
  while IFS= read -r line; do
    line="${line%%#*}"                            # drop comment
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue   # skip blank
    item="$("$extract" "$line")"
    total=$((total + 1))
    if tok="$("$probe" "$item" "$line")"; then
      got=$((got + 1))
      # de-duplicate version tokens (18 render assets collapse to 2 pinned packages)
      if [[ -n "$tok" ]]; then
        case "$seen" in *"|$tok|"*) ;; *) seen="$seen$tok|"; detail+="${detail:+, }$tok" ;; esac
      fi
    else
      missing+="${missing:+ }$item"
    fi
  done < "$manifest"
  if [[ "$got" -eq "$total" ]]; then
    ok "$subject" "$got/$total ($detail)"
  else
    info "$subject" "$got/$total - $remediation; missing $missing"
  fi
}

# The parts that differ per manifest — a matched <name>_extract / <name>_probe pair.
# extract: line → item id. probe: item present? → echo a version token, else non-zero.

# Python requirements: name is the first field minus version specifiers/extras;
# presence and version come from the installed distribution's metadata.
req_extract() { printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]].*//; s/[<>=!~;[].*//'; }
req_probe() {
  local v
  v="$("$CORPUS_YOGA_VENV/bin/python" -c "import importlib.metadata as m; print(m.version('$1'))" 2>/dev/null)" || return 1
  printf '%s %s' "$1" "$v"
}

# Render libraries: item is the dest path (first field); presence is the cached file,
# and the pinned version comes from the line's /npm/<pkg>@<ver>/ URL.

check_optional_modes() {
  sec "optional modes"
  if [[ "$(uname)" == "Darwin" ]] && command -v osascript &>/dev/null; then
    ok "browser capture" "possible"
    # Modern Safari keeps this setting where `defaults` cannot see it, and the reliable
    # probe (`do JavaScript "1+1"`) would drive Safari — off-limits for this read-only
    # reporter. Report the state only when the legacy key happens to be readable;
    # otherwise say honestly that we cannot tell from here. Capture itself fail-fasts
    # with a clear error if the setting is actually off (safari_assert_js_allowed).
    js_from_ae="$(defaults read -app Safari AllowJavaScriptFromAppleEvents 2>/dev/null || true)"
    case "$js_from_ae" in
      1) ok "Safari's Allow JavaScript from Apple Events" "enabled" ;;
      0) info "Safari's Allow JavaScript from Apple Events" "disabled" ;;
      *) ok "Safari's Allow JavaScript from Apple Events" "not verifiable read-only" ;;
    esac
  else
    info "browser capture" "unavailable"
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    ok "indexing capture" "possible"
  else
    info "indexing capture" "unavailable - ANTHROPIC_API_KEY is not set"
  fi
}

check_environment() {
  # The variables this repository reads carry its name (#703); one exported under an old
  # name is machine-local state no code reads any more, and is said so once here.
  local old
  for old in YOGA_NO_SEND YOGA_JOBS YOGA_GATE_TIMINGS; do
    [[ -n "${!old-}" ]] || continue
    todo "environment / $old" "exported, and no code reads it - CORPUS_YOGA_${old#YOGA_} is the name" "unset $old" "drops it from this shell"
  done
  if [[ -n "${VENV-}" && -z "${CORPUS_YOGA_VENV-}" ]]; then
    info "environment / VENV" "exported, and corpus-yoga no longer reads it - CORPUS_YOGA_VENV names the venv; the default stands"
  fi
}

check_machine() {
  # The binding names this machine (rsc/machine/README.md): rooted, gitignored,
  # and so spelt whole like anything else.
  local binding="$REPO_ROOT/machine-name.txt"
  local rel="${binding#"$REPO_ROOT/"}"
  local registry="$REPO_ROOT/rsc/machine/machines.csv"
  sec "machine"
  check_environment
  # The pre-move location, built in pieces — for the same reason the rooted
  # binding is not. This path must exist on NO clean clone, so a
  # committed literal naming it would be a dangling reference, and would resolve
  # one way on a machine that migrated and another on one that had not. Reported
  # first: on an un-migrated machine it is the answer to every other line here.
  # Transitional — delete this check once no machine carries the residue.
  # Split above 'machines', not above 'self.txt': the DIRECTORY vanishes on
  # migration too, so a literal naming it resolves on an un-migrated machine and
  # dangles on a migrated one — machine-dependent by the same rule. A fragment
  # beginning '/' is never read as a repo path, so this names nothing that can go.
  local legacy="$REPO_ROOT/rsc"; legacy+="/machines/self.txt"
  if [[ -f "$legacy" ]]; then
    local lrel="${legacy#"$REPO_ROOT/"}"
    todo "legacy binding / at" "$lrel - the binding moved to $rel (2026-07-17)" "mv $lrel $rel && rmdir $(dirname "$lrel")" "migrates it"
  fi
  local declared=""
  [[ -f "$registry" ]] && declared="$(tail -n +2 "$registry" | cut -d, -f1 | tr '\n' ' ')"
  if [[ ! -f "$binding" ]]; then
    todo "binding" "absent" "echo <declared-machine-name> > $rel" "binds it, to a name rsc/machine/machines.csv declares"
    declared="${declared% }"
    ok declared "${declared:-none}"
    return
  fi
  local name; name="$(cat "$binding")"
  if tail -n +2 "$registry" 2>/dev/null | cut -d, -f1 | grep -qxF "$name"; then
    ok "binding" "$name"
  else
    # the same declaredness gate machine.py gives every consumer: an undeclared
    # binding would mint a phantom machine in the shared transport store
    info "binding" "$name, undeclared in rsc/machine/machines.csv"
  fi
}

check_git_identity() {
  # The one git config committing requires. Machine-local and remediable, so a
  # species — the report warns before git's own first-commit refusal would. Report
  # only, never a sync act: a global identity is not this repo's to choose (the
  # ext/mnt/site ruling — report where the value cannot be known), unlike the venv
  # two lines below, whose contents ARE the repo's declaration.
  sec "git"
  if ! command -v git &>/dev/null; then
    todo "git / installed" "no - nothing here works without it" "brew install git" "installs it"
    return
  fi
  ok "git / installed" "$(git --version | awk '{print $3}')"
  local n e
  n="$(git -C "$REPO_ROOT" config user.name 2>/dev/null || true)"
  e="$(git -C "$REPO_ROOT" config user.email 2>/dev/null || true)"
  if [[ -n "$n" && -n "$e" ]]; then
    # --show-scope (git 2.26+) names the scope AS the flag stem — the affordance
    # --show-origin nearly served (a file path is a coordinate; the flag is the get)
    local s1 s2 scope=""
    s1="$(git -C "$REPO_ROOT" config --show-scope user.name 2>/dev/null | awk '{print $1; exit}' || true)"
    s2="$(git -C "$REPO_ROOT" config --show-scope user.email 2>/dev/null | awk '{print $1; exit}' || true)"
    if [[ -n "$s1" && "$s1" == "$s2" ]]; then scope=" (--$s1)"
    elif [[ -n "$s1$s2" ]]; then scope=" (name: --$s1, email: --$s2)"; fi
    ok "identity / set" "$n <$e>$scope"
  else
    todo "identity / set" "no - the first commit refuses" "git config --global user.name '<name>'" "names the committer" "git config --global user.email '<email>'" "gives the address"
  fi
}

check_forge() {
  # The forge's merge settings decide how main's history is composed, yet they live on
  # the server: no clone can see them and no git config holds them. src/main/cli/forge/forge.csv is the
  # declaration; `corpus-yoga forge` is the ONE thing that reconciles it with reality, and this
  # renders its rows in the machine report's voice — the reconciliation is derived once,
  # not once per reader. Network- and auth-dependent, so it NEVER fails the run:
  # unverifiable is reported, never vetoed (the deterministic gate stays offline-
  # reproducible, which is why this lives here and not in corpus-yoga test run).
  sec "forge settings"
  local status key detail remedy
  while IFS=$'\t' read -r status key detail remedy; do
    [[ -z "$status" ]] && continue
    case "$status" in
      OK)    ok   "$key" "$detail" ;;
      DRIFT) todo "$key / live" "$detail" "$remedy" "sets it as declared" ;;
      MOVED) todo "$key / names" "$detail" "$remedy" "names the repository as the forge answers for it" ;;
      *)     info "$key" "$detail" ;;
    esac
  # Sourced in the subshell this substitution already is: `reconcile` is the derivation
  # wanted, and only it runs. The subshell also keeps the two files' namespaces apart —
  # both define a `sync`, and forge.sh's must not become this script's.
  done < <(source "$REPO_ROOT/src/main/cli/forge/forge.sh"; reconcile 2>/dev/null)
}

check_pipeline_inputs() {
  # What each pipeline holds, by pipeline, provider and kind, as the store's own reading
  # counts it (src/main/corpus.py held): one count of one store (#771).
  sec "pipeline inputs"
  if [[ -x "$CORPUS_YOGA_VENV/bin/python" ]]; then
    local pipeline provider kind count
    while IFS=$'\t' read -r pipeline provider kind count _ _; do     # the store's address and its noun are the explanation's
      [[ -n "$pipeline" ]] || continue
      ok "$pipeline / $provider / $kind" "$count held"
    done < <("$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/corpus.py" held 2>/dev/null)
  else
    info held "read by the venv's python - the rows follow the mint"
  fi

  # Each provider's live store, the harness's own, and the mount the census and capture
  # read it through (#628, #636).
  sec "live stores"
  # Per declared provider (rsc/provider/providers.csv): the code-transport store this
  # machine holds, and the live harness mount the census and capture read (#628),
  # ext/mnt/agent/<provider> (#636).
  local p_name p_live p_mount p_served p_rows
  # The registry is read by the venv's python (#478); before the mint, the rows follow it.
  if [[ -x "$CORPUS_YOGA_VENV/bin/python" ]]; then
    # provider, live store, the mount as provider.mount() derives it, and whether the agent
    # verb serves the provider - a harness adapter present (src/main/cli/agent/transport.py):
    # each the rule's one home, none restated here.
    p_rows="$("$REPO_ROOT/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2]); import provider, transport; print("\n".join(r["provider"] + "\x1f" + r["live_store"] + "\x1f" + (str(provider.mount(r).relative_to(provider.REPO)) if provider.mount(r) else "") + "\x1f" + ("served" if transport.adapter(r["provider"]) else "") for r in provider.providers()))' "$REPO_ROOT/src/main" "$REPO_ROOT/src/main/cli/agent")" || return 1
  else
    info providers "rsc/provider/providers.csv is read by the venv's python - the per-provider rows follow the mint"
    p_rows=''
  fi
  while IFS=$'\x1f' read -r p_name p_live p_mount p_served; do
    [[ -n "$p_name" && -n "$p_live" && -n "$p_mount" ]] || continue
    [[ -d "${p_live/#\~/$HOME}" ]] || continue
    # A capture names the act that does what it says: the provider's own extent of the
    # capture verb where an adapter serves it, and the missing adapter where none does.
    if [[ "$p_served" == served ]]; then
      ok "$p_name / $p_live" "present"
    else
      info "$p_name / $p_live" "present, and no harness adapter serves $p_name"
    fi
    local target; target="$(readlink "$REPO_ROOT/$p_mount" 2>/dev/null || true)"
    if [[ ! -e "$REPO_ROOT/$p_mount" && -z "$target" ]]; then
      todo "$p_name / $p_mount" "absent" "corpus-yoga agent mount --apply" "mounts it"
    elif [[ -n "$target" && "${target/#\~/$HOME}" != "${p_live/#\~/$HOME}" && "$(cd "$REPO_ROOT/$p_mount" 2>/dev/null && pwd -P)" != "$(cd "${p_live/#\~/$HOME}" 2>/dev/null && pwd -P)" ]]; then
      todo "$p_name / $p_mount" "linked elsewhere - to $target" "corpus-yoga agent mount --apply" "points it at $p_live"
    else
      ok "$p_name / $p_mount" "linked"
    fi
  done <<< "$p_rows"

  sec "deploy"
  # The deploy mount differs from the live-session mount in the one way that matters:
  # its TARGET is unknowable here (the site repo's clone lives wherever the human put
  # it), so sync --apply cannot create it and absence is not a todo — deploying is
  # optional per machine. Present it is verified and named; absent it is stated as the
  # optional affordance it is, with the hand-make convention the README declares.
  if [[ -L "$REPO_ROOT/ext/mnt/site" || -d "$REPO_ROOT/ext/mnt/site" ]]; then
    if [[ -d "$REPO_ROOT/ext/mnt/site/." ]]; then
      ok "ext/mnt/site" "linked"
    else
      todo "ext/mnt/site" "dangling - to $(readlink "$REPO_ROOT/ext/mnt/site" 2>/dev/null)" "rm ext/mnt/site" "removes it; ln -s <site-repo-clone> ext/mnt/site makes one that stands"
    fi
  else
    ok "ext/mnt/site" "absent"
  fi
}

check_migration() {
  # The moves a rename owes this machine's data/output, tmp/cache and ext/mnt, carried by
  # the scripts under rsc/migration (#661): each run bare states its pending steps and
  # takes none; the reader runs the named script once with --apply.
  sec "migration"
  local script steps line step
  for script in "$REPO_ROOT"/rsc/migration/[0-9]*.sh; do
    [[ -e "$script" ]] || continue
    local rel="${script#"$REPO_ROOT"/}"
    local lines=()
    if steps="$("$script" 2>&1)"; then
      while IFS= read -r line; do lines+=("$line"); done <<< "$steps"
      if [[ -n "$steps" ]]; then
        todo "$rel / steps" "pending" "$rel --apply" "takes them"
        step=0; for line in "${lines[@]}"; do step=$((step + 1)); info "$rel / step $step" "$line"; done
      else
        ok "$rel / steps" "none pending"
      fi
    else
      while IFS= read -r line; do lines+=("$line"); done <<< "$steps"
      todo "$rel / steps" "halted - resolve by hand what it names" "$rel --apply" "then takes them"
      step=0; for line in "${lines[@]}"; do step=$((step + 1)); info "$rel / says $step" "$line"; done
    fi
  done
}

# What the report holds to act on, and of it what is sync's own to run (#777). The report
# is run for its rows; its remedies - the checks' and the grafted nouns' alike - come back
# as data, and sync runs each whose command its declaration names (sync.json's `x`), and
# the mint, which is sync itself. NOT a brew install (not ours to perform) and NOT the
# machine binding (a decision, not a derivation): those are listed, each the reader's.
_remedies=""
_held() { report >/dev/null; _remedies="$(_say remedies)"; }

sync() {
  local command does where declared own mine="" a
  own="$(sync_remedy)"
  declared="$(jq -r '.x[]' "$REPO_ROOT/src/main/cli/status/sync.json")"
  _held
  echo "corpus-yoga status sync — what this machine still needs:"
  if [[ -z "$_remedies" ]]; then
    echo "  nothing — every prerequisite is satisfied"
    return 0
  fi
  while IFS=$'\t' read -r command does where; do
    [[ -n "$command" ]] || continue
    echo "  – $where: $command - $does"
    if [[ "$command" == "$own" ]] || grep -qxF -- "${command#./}" <<< "$declared"; then
      grep -qxF -- "$command" <<< "$mine" || mine+="$command"$'\n'
    fi
  done <<< "$_remedies"
  echo
  if [[ -z "$mine" ]]; then
    echo "none of these is mine to run — each is the reader's"
    return 0
  fi
  if [[ "$APPLY" != 1 ]]; then
    echo "--apply would run:"
    while IFS= read -r a; do [[ -z "$a" ]] || echo "  $a"; done <<< "$mine"
    return 0
  fi
  while IFS= read -r a; do
    [[ -n "$a" ]] || continue
    echo "→ $a"
    if [[ "$a" == "$own" ]]; then
      # Installing IS the work here: refuse loudly rather than half-fix the machine (#29).
      assert_may_send "pip install from PyPI (corpus-yoga status sync --apply)" || exit 1
      [[ -x "$CORPUS_YOGA_VENV/bin/python" ]] || python3 -m venv "$CORPUS_YOGA_VENV"
      "$CORPUS_YOGA_VENV/bin/pip" install -q --upgrade pip
      "$CORPUS_YOGA_VENV/bin/pip" install -q -r "$REPO_ROOT/src/requirements.txt"
      echo "  venv: $("$CORPUS_YOGA_VENV/bin/python" --version 2>&1), src/requirements.txt installed"
    else
      # a declared invocation is `corpus-yoga <command> ...`, bare words: run this tree's
      # shellcheck disable=SC2086
      "$REPO_ROOT/corpus-yoga" ${a#*corpus-yoga }
    fi
  done <<< "$mine"
  echo
  echo "what remains — re-derived, not assumed:"
  _held
  if [[ -z "$_remedies" ]]; then echo "  nothing"; else
    while IFS=$'\t' read -r command does where; do [[ -z "$command" ]] || echo "  – $where: $command - $does"; done <<< "$_remedies"
  fi
}

report() {
  _rows=()
  check_machine
  check_tools
  graft grammar ""
  check_venv
  check_dependencies \
    "python requirements" \
    "$REPO_ROOT/src/requirements.txt" \
    req_extract req_probe \
    "requirements installed" \
    "corpus-yoga status sync --apply, or automatically on the next corpus-yoga pipeline run"
  graft server "/server/render assets"
  check_optional_modes
  graft completions "/completions"
  check_git_identity
  graft test "/test/pre-commit hook"
  graft test "/test/signature hook"
  check_forge
  graft forge "/branches"
  graft forge "/remote-tracking refs"
  check_pipeline_inputs
  graft pipeline "/staged"
  graft store "/duplicates"
  check_migration

  # A report is information: it exits 0 unless it could not BE produced. Severity
  # lives in the rows; refusal lives at the acts (forge merge refuses on the gate
  # row at merge time; a pipeline fails loudly on a missing tool at run time) —
  # severity and consumability decouple by LOCATION, not by a role or a bit.
  # Ruled 2026-07-31 (#141): the old exit-1-on-✗ made a pipelines-only machine
  # scriptably blocked by a hook it will never trigger.
  _say report
}

main() {
  # The sync verb's argv is the declaration's to answer (#474); the command-level
  # flags (--show-all) stay parse_args's, which cli.py's command help already covers.
  # parse_argv renders under the venv's python (#478), so it answers only where the venv
  # stands; before the mint, parse_args below takes sync and --apply itself (#757)
  if [[ "${1-}" == sync && -x "$CORPUS_YOGA_VENV/bin/python" ]]; then parse_argv status sync "${@:2}"; fi
  parse_args "$@"
  if [[ "$SYNC" == 1 ]]; then sync; else report; fi
}

main "$@"
