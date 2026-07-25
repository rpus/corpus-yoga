#!/usr/bin/env bash
# forge.sh (yoga forge) — the forge's merge settings, and the merge that obeys them.
#
# The settings decide how main's history is composed and live on the SERVER: no clone
# can see them, no git config holds them. rsc/forge.csv declares them; this reconciles
# the declaration with reality, and performs the one merge shape they permit.
#
# Usage:
#   yoga forge              # read-only: declared vs live, with the gh command for any drift
#   yoga forge --tsv        # the same reconciliation as rows (status/key/detail/remedy)
#   yoga forge merge <pr>   # reconcile, then squash-merge that PR
#
# `merge` passes NO message flags, deliberately. squash_merge_commit_message is
# COMMIT_MESSAGES: the body is assembled from the branch's commits, each keeping its
# `Signature: <machine>/<provider>/<session>` — the join key into the captured session
# corpus. A hand-written --body discards every one of them, which is how seven merges
# landed on 2026-07-25 carrying no signature at all while the branch commits beneath
# them were correctly stamped. The procedure was prose in README.md; prose is what got
# skipped. It is a command now.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DECLARED="$REPO_DIR/rsc/forge.csv"

# rows: STATUS \t key \t detail \t remedy — the ONE derivation, rendered by two callers
# (this script's status, and PREREQUISITES' machine report).
reconcile() {
  [[ -f "$DECLARED" ]] || { echo -e "UNVERIFIED\tforge.csv\tno rsc/forge.csv — nothing declared\t"; return; }
  command -v gh &>/dev/null || { echo -e "UNVERIFIED\tgh\tgh not found (install: brew install gh)\t"; return; }
  local live
  # quoted: {owner}/{repo} are gh's own placeholders, resolved from this checkout's
  # remote — never brace-expansion, and never a hard-coded (fork-specific) slug
  if ! live="$(cd "$REPO_DIR" && gh api "repos/{owner}/{repo}" 2>/dev/null)"; then
    echo -e "UNVERIFIED\tforge\tunreachable (offline, no GitHub remote, or: gh auth login)\t"
    return
  fi
  printf '%s' "$live" | python3 -c '
import csv, json, sys
live = json.load(sys.stdin)
slug = live.get("full_name") or "{owner}/{repo}"
def norm(v):
    return "true" if v is True else "false" if v is False else str(v)
for r in csv.DictReader(open(sys.argv[1])):
    key, want = r["setting"], r["value"]
    got = norm(live.get(key))
    if got == want:
        print("OK", key, want, "", sep="\t")
    else:
        flag = "-F" if want in ("true", "false") else "-f"   # -F types booleans, -f strings
        print("DRIFT", key, "declared " + want + ", live " + got,
              "gh api -X PATCH repos/" + slug + " " + flag + " " + key + "=" + want, sep="\t")
' "$DECLARED" 2>/dev/null || echo -e "UNVERIFIED\tforge.csv\tunreadable or malformed\t"
}

status() {
  echo "forge settings — declared: rsc/forge.csv; live: this checkout's remote"
  local st key detail remedy drift=0
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    case "$st" in
      OK)    echo "  ✓ $key: $detail" ;;
      DRIFT) echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1 ;;
      *)     echo "  – $key: $detail" ;;
    esac
  done < <(reconcile)
  return $drift
}

merge() {
  local pr="${1-}"
  [[ -n "$pr" ]] || { echo "yoga forge merge: which PR? (a number, a URL, or a branch)" >&2; exit 1; }
  status || { echo "yoga forge merge: forge settings drift — reconcile first (commands above); merging now would compose main's history by rules nobody declared" >&2; exit 1; }
  echo
  # No --subject, no --body: the forge assembles the message from the branch's commits,
  # which is where the signatures are.
  cd "$REPO_DIR" && gh pr merge "$pr" --squash
}

case "${1-}" in
  '')        status ;;
  --tsv)     reconcile ;;
  merge)     shift; merge "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "yoga forge: unknown argument: $1 (try: yoga forge --help)" >&2; exit 1 ;;
esac
