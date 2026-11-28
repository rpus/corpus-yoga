#!/usr/bin/env bash
# site.sh (corpus-yoga site) — the publish tree: data/output/site/<path> IS rpus.co/<path>.
#
# Usage:
#   corpus-yoga site          # status: each artifact's presence and currency, and who produces it
#   corpus-yoga site build    # write the tree: every page of rsc/site/, and index.html, the corpus page
#   corpus-yoga site sync     # make rpus.co serve the tree: pull rpus.co, copy into ext/mnt/site, commit, push
#
# build writes the whole tree: each page rsc/site/<name>.html copied to
# data/output/site/<name>.html as authored (issues/650), and index.html at the root, the
# corpus page present_corpus.py writes at its URL position (issues/409) from
# rsc/site/index.template.html, the one file under rsc/site/ that is not a page.
# README.md documents the family.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"
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
MAIN_DIR="$REPO_DIR/src/main"
# shellcheck source=src/main/corpus_shape.sh
source "$MAIN_DIR/corpus_shape.sh"   # the corpus's shape, stated once
# shellcheck source=src/main/cli/site/landing.sh
source "$SCRIPT_DIR/landing.sh"   # what publish would land, read against rpus.co as it stands (issues/1020)

usage() {
  cat <<'EOF'
corpus-yoga site — the rpus.co publish tree: data/output/site/ assembled from rsc/site/

  corpus-yoga site          status: each artifact's presence and currency, and who produces it
  corpus-yoga site build    write the tree: every page of rsc/site/, and index.html (the corpus page) from the corpus,
                            the judged index and the categories
  corpus-yoga site sync     pull rpus.co, copy the tree into ext/mnt/site, commit and push there (what it would land is the bare status's)
EOF
}

# every page: a .html at rsc/site/'s root other than the template - the assembled set and
# the status subjects, each published at the same name
page_files() {  # <root>
  find "$1" -maxdepth 1 -type f -name '*.html' ! -name 'index.template.html' | sed "s|^$1/||" | sort
}

status() {
  # the rows (issues/759): the publish tree against its sources, the corpus page, the deploy
  # mount - which status.py types and says as one shape
  {
    if [[ ! -d "$OUT" ]]; then
      printf 'pages\tabsent\t%s\n' "$(phrase "absent - the rpus.co publish layer, optional")"
    else
      local f
      while IFS= read -r f; do
        if [[ ! -f "$OUT/$f" ]]; then
          printf 'page\t%s\t%s\n' "$f" "$(phrase "absent from the tree")"
        elif ! cmp -s "$SRC/$f" "$OUT/$f"; then
          printf 'page\t%s\t%s\n' "$f" "$(phrase "differs from rsc/site/{file}" file="$f")"
        fi
      done < <(page_files "$SRC")
    fi
    # The corpus page is stated always, an absent tree included. The page declares the inputs it
    # was built from (its title: the corpus it folds), read back by status.py. No clock keys.
    local page="$OUT/index.html" declared
    has_conversations "$DATA_DIR/output/markdown" || printf 'corpus\tunprojected\n'
    if [[ ! -f "$page" ]]; then
      printf 'index\tABSENT\n'
    else
      declared="$(sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p' "$page" | head -1)"
      printf 'index\t%s\n' "${declared:-$(phrase "title absent")}"
    fi
    if [[ -d "$REPO_DIR/ext/mnt/site/." ]]; then
      printf 'deploy\t%s\n' "$(phrase "the mount ext/mnt/site is present, rpus.co's clone")"
      clone_fetch "$REPO_DIR/ext/mnt/site"
      clone_position "$REPO_DIR/ext/mnt/site"
      landing "$REPO_DIR/ext/mnt/site" "$OUT"
    elif [[ -L "$REPO_DIR/ext/mnt/site" ]]; then
      # a machine that once deployed and moved its clone — the reader most surprised by
      # "no mount", and the one who least needs the convention; say what status says
      printf 'deploy\t%s\n' "$(phrase "ext/mnt/site is a dangling link to {target} - repoint it at the site repo's clone, or remove it" target="$(readlink "$REPO_DIR/ext/mnt/site")")"
    else
      printf 'deploy\t%s\n' "$(phrase "no ext/mnt/site mount on this machine - optional")"
    fi
  } | "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/site/status.py"
}

# The act (issues/881): what it would land is the bare status's; this copies, commits and pushes.
sync() {
  local mount="$REPO_DIR/ext/mnt/site"
  if [[ ! -d "$mount/.git" ]]; then
    effect "$(act site sync): NOT DONE - $(phrase "ext/mnt/site is not a git clone; corpus-yoga status reports the mount")"
    return 1
  fi
  if [[ ! -d "$OUT" ]]; then
    effect "$(act site sync): NOT DONE - $(phrase "no publish tree at data/output/site/")"
    return 1
  fi
  # the branch rpus.co serves, whatever the clone has checked out (issues/1026): a clone that
  # records none, or stands on another, is refused before any copy or commit, by name
  local served off
  served="$(clone_served "$mount")"
  if [[ -z "$served" ]]; then
    effect "$(act site sync): NOT DONE - $(phrase "the clone records no branch rpus.co serves - corpus-yoga site names the remedy")"
    return 1
  fi
  off="$(off_served "$mount")"
  if [[ -n "$off" ]]; then
    effect "$(act site sync): NOT DONE - $(phrase "the clone stands on {branch}, not {local}, the branch rpus.co serves - corpus-yoga site names the switch" branch="$off" local="${served#*/}")"
    return 1
  fi
  # rpus.co as it stands first (issues/1020): the clone brought level by a fast-forward, so that
  # the copy lands on what rpus.co holds; where the send is refused, the landing is read as last
  # fetched and the push below refuses whatever would land
  local levelled=0
  level_clone "$mount" || levelled=$?
  if [[ "$levelled" -ne 0 && "$levelled" -ne "$SEND_REFUSED" ]]; then
    effect "$(act site sync): NOT DONE - $(phrase "the clone could not be brought level with rpus.co by a fast-forward - corpus-yoga site says where they part")"
    return 1
  fi
  local rows ahead
  rows="$(landing "$mount" "$OUT")"
  # commits the clone holds and rpus.co does not are pushed whatever the files say
  ahead="$(git -C "$mount" rev-list --count "$served..HEAD" 2>/dev/null || echo 0)"
  if [[ -z "$rows" && "$ahead" == 0 ]]; then
    effect "$(act site sync): DONE - $(phrase "no effect; rpus.co's clone already holds the publish tree as assembled")"
    return 0
  fi
  if [[ -n "$rows" ]]; then
    echo "did land:"
    printf '%s\n' "$rows" | while IFS=$'\t' read -r _ rel _; do [[ -n "$rel" ]] && echo "  $rel"; done
  fi
  send_cleared push || return 1
  enact cp -R "$OUT/" "$mount/" || return 1
  enact git -C "$mount" add -A || return 1
  if [[ -n "$(git -C "$mount" status --porcelain)" ]]; then
    enact git -C "$mount" commit -m "publish" || return 1
  else
    echo "  $(phrase "nothing to commit - the clone already held the tree")"
  fi
  (cd "$mount" && send enact push "HEAD:${served#*/}") || return 1
  effect "$(act site sync): DONE - $(phrase "rpus.co serves the publish tree on Netlify's next build")"
}


build() {
  mkdir -p "$OUT"
  local d f name placed=0 departed=0
  # A page that left rsc/site/ halts the build, the publish tree left as it is: the copy to
  # rpus.co is a union that never deletes, so the page stays there, and this is the one act
  # that can still see it go. index.html is the corpus page, never a departed page.
  for d in "$OUT"/*/; do
    [[ -d "$d" ]] || continue
    echo "site: $(phrase "{name}/ is a directory, where the publish tree holds pages at its root - it stays on rpus.co, which the copy never deletes from" name="$(basename "$d")")"
    departed=1
  done
  for f in "$OUT"/*.html; do
    [[ -f "$f" ]] || continue
    name="$(basename "$f")"
    [[ "$name" == index.html ]] && continue
    if [[ ! -f "$SRC/$name" ]]; then
      echo "site: $(phrase "{name} left rsc/site/ - it stays on rpus.co, which the copy never deletes from" name="$name")"
      departed=1
    fi
  done
  if [[ $departed -eq 1 ]]; then
    effect "$(act site build): NOT DONE - $(phrase "a page left rsc/site/ and stays on rpus.co; the lines above name it, and data/output/site/ is left as it was")"
    return 1
  fi
  while IFS= read -r f; do
    # current already? byte-identical → silence (L1)
    [[ -f "$OUT/$f" ]] && cmp -s "$SRC/$f" "$OUT/$f" && continue
    cp "$SRC/$f" "$OUT/$f"
    echo "site: $(phrase "placed {file}" file="$f")"
    placed=$((placed + 1))
  done < <(page_files "$SRC")
  # the corpus page, which says the verdict for the whole tree, the pages placed with it
  exec "$REPO_DIR/src/run_python_script.sh" "$MAIN_DIR/present_corpus.py" --placed "$placed"
}

case "${1:-}" in
  '')          status ;;
  build)       shift; parse_argv site build "$@"; build ;;
  sync)        shift; parse_argv site sync "$@"; sync "$@" ;;
  -h|--help)   usage ;;
  *)           echo "corpus-yoga site: unknown verb '${1}'" >&2; usage >&2; exit 2 ;;
esac
