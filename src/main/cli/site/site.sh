#!/usr/bin/env bash
# site.sh (corpus-yoga site) — the publish tree: data/output/site/<path> IS rpus.co/<path>.
#
# Usage:
#   corpus-yoga site          # status: each artifact's presence and currency, and who produces it
#   corpus-yoga site sync     # assemble the tree from rsc/site/ - every page copied beside index.html
#   corpus-yoga site publish [--apply]  # make rpus.co serve the tree: copy into ext/mnt/site, commit, push
#   corpus-yoga site render   # FREE: render index.html, the corpus page, from the corpus + captures
#
# The tree has two verbs with disjoint files: sync owns every page, a file
# rsc/site/<name>.html copied to data/output/site/<name>.html as authored (#650);
# render owns index.html at the root, the corpus page present_corpus.py writes
# at its URL position (#409 - formerly corpus-yoga dashboard sync) from
# rsc/site/index.template.html, the one file under rsc/site/ that is not a page.
# sync never touches index.html; README.md documents the family.

set -euo pipefail
SELF='src/main/cli/site/site.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"
SRC="$REPO_DIR/rsc/site"
OUT="$REPO_DIR/data/output/site"
MODEL_DIR="$REPO_DIR/src/main/model"
# shellcheck source=src/main/model/corpus_shape.sh
source "$MODEL_DIR/corpus_shape.sh"   # the corpus's shape, stated once

usage() {
  cat <<'EOF'
corpus-yoga site — the rpus.co publish tree: data/output/site/ assembled from rsc/site/

  corpus-yoga site          status: each artifact's presence and currency, and who produces it
  corpus-yoga site sync     assemble the tree (every page copied beside index.html)
  corpus-yoga site publish  copy the tree into ext/mnt/site, commit and push there (dry unless --apply)
  corpus-yoga site render   FREE: render index.html (the corpus page) from the corpus + captures
EOF
}

# every page: a .html at rsc/site/'s root other than the template - the sync set and
# the status subjects, each published at the same name
page_files() {  # <root>
  find "$1" -maxdepth 1 -type f -name '*.html' ! -name 'index.template.html' | sed "s|^$1/||" | sort
}

status() {
  echo "site — publish tree: data/output/site/ (rpus.co); sources: rsc/site/"
  if [[ ! -d "$OUT" ]]; then
    # The pages are the rpus.co publish layer - deploy-side, optional; the
    # quickstart teaches only the render. Prescribing sync here made every
    # pipeline run nag a verb the front door never taught.
    echo "  – pages absent (the rpus.co publish layer) — optional: corpus-yoga site sync assembles them"
  else
    local f stale=0
    while IFS= read -r f; do
      if [[ ! -f "$OUT/$f" ]]; then
        echo "  – $f: absent from the tree"; stale=1
      elif ! cmp -s "$SRC/$f" "$OUT/$f"; then
        echo "  – $f: differs from rsc/site/$f"; stale=1
      fi
    done < <(page_files "$SRC")
    # the run syncs before this probe (#494): a stale tree here is rsc/site/ edited
    # outside a run
    [[ $stale -eq 0 ]] && echo "  ✓ pages current with rsc/site/"
  fi
  # The corpus page is its own layer (render's, the quickstart's subject):
  # stated ALWAYS — an absent tree must not silence the one site verb the
  # front door teaches.
  render_currency
  if [[ -d "$REPO_DIR/ext/mnt/site/." ]]; then
    echo "deploy: cp -R data/output/site/ ext/mnt/site/ — the mount is present (then commit + push there)"
  elif [[ -L "$REPO_DIR/ext/mnt/site" ]]; then
    # a machine that once deployed and moved its clone — the reader most surprised by
    # "no mount", and the one who least needs the convention; say what prerequisites says
    echo "deploy: ext/mnt/site is a dangling link → $(readlink "$REPO_DIR/ext/mnt/site") — repoint it at the site repo's clone, or remove it"
  else
    echo "deploy: no ext/mnt/site mount on this machine — optional; corpus-yoga prerequisites shows the convention"
  fi
}

# The page's standing (#409, #494): the run renders it before this probe runs, so
# "behind" on the free axis is unreachable by construction; the page declares
# the inputs it was rendered from (its title: the corpus it folds; its export
# tooltip: the captures' coverage), so a lag in the paid layer reads as what it
# is, stated - indexing's status carries the paid prescription. No clock keys.
render_currency() {
  local render="$OUT/index.html"
  if [[ ! -f "$render" ]]; then
    echo "FAIL: index.html absent - the corpus page is unbuilt; corpus-yoga pipeline run renders it (or: corpus-yoga site render)"
    return 0
  fi
  local declared
  declared="$(sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p' "$render" | head -1)"
  echo "  ✓ index.html (the corpus page; producer: corpus-yoga site render) — ${declared:-title absent}"
}

render() {
  exec "$REPO_DIR/src/run_python_script.sh" "$MODEL_DIR/present_corpus.py" "$@"
}

publish() {
  local apply=""
  [[ "${1-}" == "--apply" ]] && apply=1
  local mount="$REPO_DIR/ext/mnt/site"
  if [[ ! -d "$mount/.git" ]]; then
    echo "site publish: NOT DONE — ext/mnt/site is not a git clone; corpus-yoga prerequisites reports the mount"
    return 1
  fi
  if [[ ! -d "$OUT" ]]; then
    echo "site publish: NOT DONE — no publish tree at data/output/site/; corpus-yoga site sync assembles it"
    return 1
  fi
  # what differs: new or changed files the copy would land (deletions are not
  # mirrored - the site repo curates its own removals)
  local delta=0 f rel
  while IFS= read -r f; do
    rel="${f#"$OUT"/}"
    if [[ ! -f "$mount/$rel" ]] || ! cmp -s "$f" "$mount/$rel"; then
      echo "  would land: $rel"
      delta=1
    fi
  done < <(find "$OUT" -type f | sort)
  if [[ "$delta" == 0 && -z "$(git -C "$mount" status --porcelain)" ]]; then
    echo "site publish: no effect — rpus.co's clone already holds the publish tree as assembled"
    return 0
  fi
  if [[ -z "$apply" ]]; then
    [[ -n "$(git -C "$mount" status --porcelain)" ]] && echo "  (the clone also holds uncommitted changes of its own — --apply commits them with the copy)"
    echo "site publish: dry run — the copy, commit and push above await --apply"
    return 0
  fi
  assert_may_send "git -C ext/mnt/site push (site publish --apply)" || return 1
  enact cp -R "$OUT/" "$mount/" || return 1
  enact git -C "$mount" add -A || return 1
  if [[ -n "$(git -C "$mount" status --porcelain)" ]]; then
    enact git -C "$mount" commit -m "publish" || return 1
  else
    echo "  nothing to commit — the clone already held the tree"
  fi
  enact git -C "$mount" push || return 1
  echo "site publish: DONE — rpus.co serves the publish tree on Netlify's next build"
}


sync() {
  mkdir -p "$OUT"
  local d f name eventful=0
  # reconcile: what left rsc/site/ leaves the publish tree with it (L7: this tree is
  # sync's own) - a page whose source is gone, and any directory, since the pages sit
  # at the root since #650 (the page directories of 2026-08 to 2026-09-15 among them).
  # index.html is spared: it is render's.
  for d in "$OUT"/*/; do
    [[ -d "$d" ]] || continue
    name="$(basename "$d")"
    rm -rf "${OUT:?}/$name"
    echo "site: pruned $name/ — the publish tree holds pages at its root, not directories"
    eventful=1
  done
  for f in "$OUT"/*.html; do
    [[ -f "$f" ]] || continue
    name="$(basename "$f")"
    [[ "$name" == index.html ]] && continue
    if [[ ! -f "$SRC/$name" ]]; then
      rm -f "$f"
      echo "site: pruned $name — its source left rsc/site/"
      eventful=1
    fi
  done
  while IFS= read -r f; do
    # current already? byte-identical → silence (L1)
    [[ -f "$OUT/$f" ]] && cmp -s "$SRC/$f" "$OUT/$f" && continue
    cp "$SRC/$f" "$OUT/$f"
    echo "site → $f"
    eventful=1
  done < <(page_files "$SRC")
  if [[ $eventful -eq 1 ]]; then
    echo "DONE — effect: pages placed; postcondition: data/output/site/ serves rsc/site/ as authored (index.html stays render's)"
  else
    echo "DONE — no effect: data/output/site/ already serves rsc/site/ as authored"
  fi
}

case "${1:-}" in
  '')          status ;;
  sync)        shift; parse_argv site sync "$@"; sync ;;
  publish)   shift; parse_argv site publish "$@"; publish "$@" ;;
  render)      shift; parse_argv site render "$@"; render "$@" ;;
  -h|--help)   usage ;;
  *)           echo "corpus-yoga site: unknown verb '${1}'" >&2; usage >&2; exit 2 ;;
esac
