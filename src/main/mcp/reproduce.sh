#!/usr/bin/env bash
# Reproduce the mcp snapshot: is rsc/reference/mcp/<lineage>/schema.json what
# upstream's own generator makes of the schema.ts beside it?
#
# Upstream (modelcontextprotocol/modelcontextprotocol) writes schema.ts by hand and
# generates schema.json from it - scripts/generate-schemas.ts runs the npm package
# typescript-json-schema over the .ts and relabels its draft-07 output as 2020-12 -
# and keeps the two in step with the same script's --check mode, which regenerates
# from the .ts and compares with the committed .json. This script runs THAT check
# over OUR committed copies and relays its verdict. It restates nothing of the
# generator: no command line, no flags, no substitutions - those are upstream's,
# fetched at the pinned commit, so a change upstream makes to its generator reaches
# this script through the pin alone.
#
# Steps, in the order the code takes them:
#   1. the pin: the lineage and upstream commit from the schema.json row of
#      rsc/reference/mcp/provenance.csv, the repository from reference.json
#   2. fetch upstream at that commit into a temporary directory - a shallow, sparse
#      git checkout of what the check reads (package.json, package-lock.json,
#      .nvmrc, tsconfig.json, scripts/generate-schemas.ts, schema/)
#   3. copy the committed schema.ts over the clone's, so the generation runs on the
#      repo's bytes
#   4. docker run node at the version upstream's .nvmrc names: npm ci from upstream's
#      lock file, then `npx tsx scripts/generate-schemas.ts` - upstream's generation
#      as upstream runs it, which rewrites every lineage's schema.json in the clone
#   5. diff the committed schema.json against the regenerated one: the diff, if any,
#      then one verdict line; exit 0 when the bytes are identical, 1 otherwise
#
# Reading the output: the generator prints one line per lineage in upstream's
# schema/ directory (it generates them all); only the pinned lineage's file is
# compared. The comparison is byte-level (`diff`), stricter than upstream's own
# --check, which trims surrounding whitespace before comparing. A diff reads
# `<` for the committed file, `>` for what the generator made of the committed
# schema.ts.
#
# Usage:
#   corpus-yoga mcp reproduce            # the diff if any, then the verdict; exit 0 iff identical
#   src/main/mcp/reproduce.sh            # the same, run directly
#
# Effects (declared in src/main/cli/mcp/reproduce.json): a git fetch from upstream
# and a docker run (image pull, npm registry) - both sends; the temporary directory is removed on exit; nothing under the repo
# is written. YOGA_NO_SEND=1 refuses the run (src/main/send.sh, assert_may_send).
# Needs git, docker with its daemon running, and python3 (to read the provenance
# rows).

set -euo pipefail

SELF='src/main/mcp/reproduce.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"

PROJECT="$REPO_DIR/rsc/reference/mcp"

assert_may_send "fetching upstream and running its generator in a container"

# The pin: provenance.csv's schema.json row names the lineage and the upstream commit;
# reference.json names the upstream repository.
read -r LINEAGE PIN < <(python3 -c '
import csv, sys
for row in csv.DictReader(open(sys.argv[1], newline="")):
    if row["file"] == "schema.json":
        print(row["lineage"], row["pin"]); break
' "$PROJECT/provenance.csv")
UPSTREAM="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["upstream"])' "$PROJECT/reference.json")"

echo "reproduce: $UPSTREAM @ $PIN, lineage $LINEAGE"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# A git hook exports GIT_DIR, GIT_INDEX_FILE and their kin, which would aim every git
# command below at the repository being committed rather than at the clone in $WORK.
unset "${!GIT_@}"

# Upstream at the pinned commit: only what the check reads.
git -C "$WORK" init -q
git -C "$WORK" remote add origin "$UPSTREAM"
git -C "$WORK" sparse-checkout set --no-cone \
  '/package.json' '/package-lock.json' '/.nvmrc' '/tsconfig.json' '/scripts/generate-schemas.ts' '/schema/'
git -C "$WORK" fetch -q --depth 1 origin "$PIN"
git -C "$WORK" checkout -q FETCH_HEAD

# The committed schema.ts stands in for upstream's, so the generation is over our bytes.
cp "$PROJECT/$LINEAGE/schema.ts" "$WORK/schema/$LINEAGE/schema.ts"
NODE="$(tr -d 'v[:space:]' < "$WORK/.nvmrc")"

echo "reproduce: docker run node:$NODE - npm ci, then npx tsx scripts/generate-schemas.ts"
docker run --rm -v "$WORK:/work" -w /work "node:$NODE" \
  sh -c 'npm ci --ignore-scripts --no-audit --no-fund --loglevel=error && npx tsx scripts/generate-schemas.ts'

COMMITTED="$PROJECT/$LINEAGE/schema.json"
GENERATED="$WORK/schema/$LINEAGE/schema.json"
STATUS=0
diff "$COMMITTED" "$GENERATED" || STATUS=1
if [[ $STATUS -eq 0 ]]; then
  echo "reproduce: rsc/reference/mcp/$LINEAGE/schema.json is byte-identical to what upstream's generator makes of schema.ts - reproduced"
else
  echo "reproduce: NOT reproduced - the diff above is committed (<) against generated (>)"
fi
exit $STATUS
