#!/usr/bin/env bash
# site.sh (corpus-yoga site) — the publish tree: data/output/site/<path> IS rpus.co/<path>.
#
# Usage:
#   corpus-yoga site          # status: each artifact's presence and currency, and who produces it
#   corpus-yoga site sync     # assemble the tree from rsc/site/ - every page copied beside index.html
#   corpus-yoga site publish            # make rpus.co serve the tree: copy into ext/mnt/site, commit, push;
#                                       # the dry run states what changes in the corpus page, table by table
#   corpus-yoga site render   # FREE: render index.html, the corpus page, from the corpus + captures
#
# The tree has two verbs with disjoint files: sync owns every page, a file
# rsc/site/<name>.html copied to data/output/site/<name>.html as authored (issues/650);
# render owns index.html at the root, the corpus page present_corpus.py writes
# at its URL position (issues/409 - formerly corpus-yoga dashboard sync) from
# rsc/site/index.template.html, the one file under rsc/site/ that is not a page.
# sync never touches index.html; README.md documents the family.

set -euo pipefail
SELF='src/main/cli/site/site.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"
# shellcheck source=src/main/report.sh
source "$REPO_DIR/src/main/report.sh"   # effect - what an act reports after its lines (issues/876)
SRC="$REPO_DIR/rsc/site"
OUT="$DATA_DIR/output/site"
MODEL_DIR="$REPO_DIR/src/main/model"
# shellcheck source=src/main/model/corpus_shape.sh
source "$MODEL_DIR/corpus_shape.sh"   # the corpus's shape, stated once

usage() {
  cat <<'EOF'
corpus-yoga site — the rpus.co publish tree: data/output/site/ assembled from rsc/site/

  corpus-yoga site          status: each artifact's presence and currency, and who produces it
  corpus-yoga site sync     assemble the tree (every page copied beside index.html)
  corpus-yoga site publish  copy the tree into ext/mnt/site, commit and push there (what it would land is the bare status's;
                            the dry run states what changes in the corpus page, table by table)
  corpus-yoga site render   FREE: render index.html (the corpus page) from the corpus + captures
EOF
}

# every page: a .html at rsc/site/'s root other than the template - the sync set and
# the status subjects, each published at the same name
page_files() {  # <root>
  find "$1" -maxdepth 1 -type f -name '*.html' ! -name 'index.template.html' | sed "s|^$1/||" | sort
}

status() {
  # the rows (issues/759): the publish tree against its sources, the corpus page, the deploy
  # mount - which status.py types and says as one shape
  {
    if [[ ! -d "$OUT" ]]; then
      # The pages are the rpus.co publish layer - deploy-side, optional; the
      # quickstart teaches only the render. Prescribing sync here made every
      # pipeline run nag a verb the front door never taught.
      printf 'pages\t%s\n' "$(phrase "absent - the rpus.co publish layer, optional; corpus-yoga site sync assembles them")"
    else
      local f
      # the run syncs before this probe (issues/494): a stale tree here is rsc/site/ edited
      # outside a run
      while IFS= read -r f; do
        if [[ ! -f "$OUT/$f" ]]; then
          printf 'page\t%s\t%s\n' "$f" "$(phrase "absent from the tree")"
        elif ! cmp -s "$SRC/$f" "$OUT/$f"; then
          printf 'page\t%s\t%s\n' "$f" "$(phrase "differs from rsc/site/{file}" file="$f")"
        fi
      done < <(page_files "$SRC")
    fi
    # The corpus page is its own layer (render's, the quickstart's subject):
    # stated ALWAYS — an absent tree must not silence the one site verb the
    # front door teaches. The page declares the inputs it was rendered from (its
    # title: the corpus it folds), so a lag in the paid layer reads as what it is,
    # stated - indexing's status carries the paid prescription. No clock keys (issues/409, issues/494).
    local render="$OUT/index.html" declared
    if [[ ! -f "$render" ]]; then
      printf 'index\tABSENT\n'
    else
      declared="$(sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p' "$render" | head -1)"
      printf 'index\t%s\n' "${declared:-$(phrase "title absent")}"
    fi
    if [[ -d "$REPO_DIR/ext/mnt/site/." ]]; then
      printf 'deploy\t%s\n' "$(phrase "the mount ext/mnt/site is present, rpus.co's clone")"
      landing
    elif [[ -L "$REPO_DIR/ext/mnt/site" ]]; then
      # a machine that once deployed and moved its clone — the reader most surprised by
      # "no mount", and the one who least needs the convention; say what status says
      printf 'deploy\t%s\n' "$(phrase "ext/mnt/site is a dangling link to {target} - repoint it at the site repo's clone, or remove it" target="$(readlink "$REPO_DIR/ext/mnt/site")")"
    else
      printf 'deploy\t%s\n' "$(phrase "no ext/mnt/site mount on this machine - optional; corpus-yoga status shows the convention")"
    fi
  } | "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/site/status.py"
}

render() {
  exec "$REPO_DIR/src/run_python_script.sh" "$MODEL_DIR/present_corpus.py" "$@"
}

# what publish would land, as rows for the status (issues/881): each new or changed file of the
# publish tree against rpus.co's clone (deletions are not mirrored - the site repo
# curates its own removals), and for the corpus page what changes in the page's own terms
# (issues/652, src/main/model/compare_pages.py), since a line diff of two renders misstates it.
landing() {
  local mount="$REPO_DIR/ext/mnt/site" f rel
  [[ -d "$mount/.git" && -d "$OUT" ]] || return 0
  while IFS= read -r f; do
    rel="${f#"$OUT"/}"
    if [[ ! -f "$mount/$rel" ]]; then
      printf 'land\t%s\t%s\n' "$rel" "$(phrase "new on rpus.co")"
    elif ! cmp -s "$f" "$mount/$rel"; then
      if [[ "$rel" == index.html ]]; then
        # one row per line of the comparison: each a fact of the page, which the status
        # nests beneath the file, never one sentence
        "$REPO_DIR/src/run_python_script.sh" "$MODEL_DIR/compare_pages.py" "$mount/$rel" "$f" | while IFS= read -r line; do
          [[ -n "$line" ]] && printf 'land\t%s\t%s\n' "$rel" "$line"
        done
      else
        printf 'land\t%s\t%s\n' "$rel" "$(phrase "changed")"
      fi
    fi
  done < <(find "$OUT" -type f | sort)
  [[ -n "$(git -C "$mount" status --porcelain)" ]] && printf 'land\t%s\t%s\n' "(the clone's own uncommitted changes)" "$(phrase "committed with the copy")"
  return 0
}

# The act (issues/881): what it would land is the bare status's; this copies, commits and pushes.
publish() {
  local mount="$REPO_DIR/ext/mnt/site"
  if [[ ! -d "$mount/.git" ]]; then
    effect "site publish: NOT DONE - $(phrase "ext/mnt/site is not a git clone; corpus-yoga status reports the mount")"
    return 1
  fi
  if [[ ! -d "$OUT" ]]; then
    effect "site publish: NOT DONE - $(phrase "no publish tree at data/output/site/")" "corpus-yoga site sync" "$(phrase "assembles it")"
    return 1
  fi
  local rows
  rows="$(landing)"
  if [[ -z "$rows" ]]; then
    effect "site publish: DONE - $(phrase "no effect; rpus.co's clone already holds the publish tree as assembled")"
    return 0
  fi
  echo "did land:"
  printf '%s\n' "$rows" | while IFS=$'\t' read -r _ rel _; do [[ -n "$rel" ]] && echo "  $rel"; done
  assert_may_send "git -C ext/mnt/site push (site publish)" || return 1
  enact cp -R "$OUT/" "$mount/" || return 1
  enact git -C "$mount" add -A || return 1
  if [[ -n "$(git -C "$mount" status --porcelain)" ]]; then
    enact git -C "$mount" commit -m "publish" || return 1
  else
    echo "  $(phrase "nothing to commit - the clone already held the tree")"
  fi
  enact git -C "$mount" push || return 1
  effect "site publish: DONE - $(phrase "rpus.co serves the publish tree on Netlify's next build")"
}


sync() {
  mkdir -p "$OUT"
  local d f name eventful=0
  # reconcile: what left rsc/site/ leaves the publish tree with it (L7: this tree is
  # sync's own) - a page whose source is gone, and any directory, since the pages sit
  # at the root since issues/650 (the page directories of 2026-08 to 2026-09-15 among them).
  # index.html is spared: it is render's.
  for d in "$OUT"/*/; do
    [[ -d "$d" ]] || continue
    name="$(basename "$d")"
    rm -rf "${OUT:?}/$name"
    echo "site: $(phrase "pruned {name}/ - the publish tree holds pages at its root, not directories" name="$name")"
    eventful=1
  done
  for f in "$OUT"/*.html; do
    [[ -f "$f" ]] || continue
    name="$(basename "$f")"
    [[ "$name" == index.html ]] && continue
    if [[ ! -f "$SRC/$name" ]]; then
      rm -f "$f"
      echo "site: $(phrase "pruned {name} - its source left rsc/site/" name="$name")"
      eventful=1
    fi
  done
  while IFS= read -r f; do
    # current already? byte-identical → silence (L1)
    [[ -f "$OUT/$f" ]] && cmp -s "$SRC/$f" "$OUT/$f" && continue
    cp "$SRC/$f" "$OUT/$f"
    echo "site: $(phrase "placed {file}" file="$f")"
    eventful=1
  done < <(page_files "$SRC")
  if [[ $eventful -eq 1 ]]; then
    effect "site sync: DONE - $(phrase "pages placed; data/output/site/ serves rsc/site/ as authored (index.html stays render's)")"
  else
    effect "site sync: DONE - $(phrase "no effect; data/output/site/ already serves rsc/site/ as authored")"
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
