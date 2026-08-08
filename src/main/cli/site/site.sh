#!/usr/bin/env bash
# site.sh (yoga site) — the publish tree: data/output/site/<path> IS rpus.co/<path>.
#
# Usage:
#   yoga site          # status: each artifact's presence and currency, and who produces it
#   yoga site sync     # assemble the tree from rsc/site/ — page dirs copied, .dot rendered
#   yoga site render   # FREE: render index.html, the corpus page, from the corpus + captures
#
# The tree has two verbs with disjoint files: sync owns the page directories
# (copied from rsc/site/, every .dot rendered to svg+png beside its page);
# render owns index.html at the root, the corpus page present_corpus.py writes
# at its URL position (#409 — formerly yoga dashboard sync). sync never touches index.html. rsc/site/'s root FILES
# stay behind: index.html there is the presenters' template (an input, not a page) and
# README.md documents the family. Without graphviz the renders are skipped, not failed.

set -euo pipefail
SELF='src/main/cli/site/site.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
SRC="$REPO_DIR/rsc/site"
OUT="$REPO_DIR/data/output/site"
MODEL_DIR="$REPO_DIR/src/main/model"
# shellcheck source=src/main/model/corpus_shape.sh
source "$MODEL_DIR/corpus_shape.sh"   # the corpus's shape, stated once

usage() {
  cat <<'EOF'
yoga site — the rpus.co publish tree: data/output/site/ assembled from rsc/site/

  yoga site          status: each artifact's presence and currency, and who produces it
  yoga site sync     assemble the tree (page dirs copied, every .dot rendered to svg+png)
  yoga site render   FREE: render index.html (the corpus page) from the corpus + captures
EOF
}

# every page under every page dir, source-relative: the sync set and the status subjects
page_files() {  # <root>
  find "$1" -mindepth 2 -type f ! -name '.DS_Store' | sed "s|^$1/||" | sort
}

status() {
  echo "site — publish tree: data/output/site/ (rpus.co); sources: rsc/site/"
  if [[ ! -d "$OUT" ]]; then
    echo "  – tree absent → run: yoga site sync"
  else
    local f stale=0
    while IFS= read -r f; do
      if [[ ! -f "$OUT/$f" ]]; then
        echo "  – $f: absent from the tree"; stale=1
      elif ! cmp -s "$SRC/$f" "$OUT/$f"; then
        echo "  – $f: differs from rsc/site/$f"; stale=1
      fi
    done < <(page_files "$SRC")
    while IFS= read -r f; do
      local svg="$OUT/${f%.dot}.svg" png="$OUT/${f%.dot}.png"
      if [[ ! -f "$svg" || ! -f "$png" ]]; then
        echo "  – ${f%.dot}.svg/.png: not rendered"; stale=1
      elif [[ "$SRC/$f" -nt "$svg" || "$SRC/$f" -nt "$png" ]]; then
        echo "  – ${f%.dot}.svg/.png: older than $f"; stale=1
      fi
    done < <(page_files "$SRC" | grep '\.dot$' || true)
    [[ $stale -eq 0 ]] && echo "  ✓ page dirs current with rsc/site/ (renders included)"
    [[ $stale -eq 1 ]] && echo "    → run: yoga site sync"
    render_currency
  fi
  command -v dot >/dev/null || echo "  – graphviz absent: sync will skip the .dot renders → install via: brew install graphviz"
  if [[ -d "$REPO_DIR/ext/mnt/site/." ]]; then
    echo "deploy: cp -R data/output/site/ ext/mnt/site/ — the mount is present (then commit + push there)"
  elif [[ -L "$REPO_DIR/ext/mnt/site" ]]; then
    # a machine that once deployed and moved its clone — the reader most surprised by
    # "no mount", and the one who least needs the convention; say what prerequisites says
    echo "deploy: ext/mnt/site is a dangling link → $(readlink "$REPO_DIR/ext/mnt/site") — repoint it at the site repo's clone, or remove it"
  else
    echo "deploy: no ext/mnt/site mount on this machine — optional; yoga prerequisites shows the convention"
  fi
}

# The render's own currency (#409 — the render-vs-inputs half of the report the
# dashboard command carried before it dissolved; captures-vs-corpus is indexing's).
# The -newer/-nt comparisons are the one advisory clock key surviving #369's
# census, owned by this probe (#381): INFO atoms only, never a gate or a skip.
render_currency() {
  local corpus="$REPO_DIR/data/output/markdown"
  local render="$OUT/index.html"
  local d="$REPO_DIR/data/output/dashboard"
  local f render_state
  if [[ ! -f "$render" ]]; then
    echo "  – index.html absent → run: yoga site render"
    return 0
  fi
  local behind=''
  [[ -n "$(find "$corpus" -path "$CONVERSATIONS_GLOB" -newer "$render" -print -quit 2>/dev/null)" ]]     && behind='corpus'
  for f in semantic-concepts.json chat-categories.json; do
    [[ "$d/$f" -nt "$render" ]] && { [[ "$behind" == *captures* ]] || behind="${behind:+$behind and }captures"; }
  done
  render_state="${behind:+behind ($behind changed since the render)}"
  render_state="${render_state:-current}"
  echo "  ✓ index.html (the corpus page; producer: yoga site render) — $render_state"
  if [[ "$render_state" != current ]]; then
    echo "INFO: the corpus page is $render_state — free to fix:"
    echo "    → run: yoga site render   # FREE — re-render from the current corpus + captures"
  fi
}

render() {
  exec "$REPO_DIR/src/run_python_script.sh" "$MODEL_DIR/present_corpus.py" "$@"
}

sync() {
  mkdir -p "$OUT"
  local d name f eventful=0
  for d in "$SRC"/*/; do
    name="$(basename "$d")"
    # current already? every source file byte-identical and every render fresh → silence (L1)
    local dirty=0
    while IFS= read -r f; do
      [[ -f "$OUT/$f" ]] && cmp -s "$SRC/$f" "$OUT/$f" || dirty=1
    done < <(page_files "$SRC" | grep "^$name/")
    while IFS= read -r f; do
      [[ -f "$OUT/${f%.dot}.svg" && -f "$OUT/${f%.dot}.png" ]] \
        && [[ ! "$SRC/$f" -nt "$OUT/${f%.dot}.svg" && ! "$SRC/$f" -nt "$OUT/${f%.dot}.png" ]] || dirty=1
    done < <(page_files "$SRC" | grep "^$name/" | grep '\.dot$' || true)
    [[ $dirty -eq 0 ]] && continue
    eventful=1
    rm -rf "${OUT:?}/$name"
    mkdir -p "$OUT/$name"
    while IFS= read -r f; do
      mkdir -p "$OUT/$(dirname "$f")"
      cp "$SRC/$f" "$OUT/$f"
      echo "site → $f"
    done < <(page_files "$SRC" | grep "^$name/")
    while IFS= read -r f; do
      if command -v dot >/dev/null; then
        dot -Tsvg "$SRC/$f" -o "$OUT/${f%.dot}.svg"
        dot -Tpng "$SRC/$f" -o "$OUT/${f%.dot}.png"
        echo "site → ${f%.dot}.svg + .png (rendered)"
      else
        echo "site: ${f%.dot}.svg/.png skipped — graphviz absent → install via: brew install graphviz"
      fi
    done < <(page_files "$SRC" | grep "^$name/" | grep '\.dot$' || true)
  done
  if [[ $eventful -eq 1 ]]; then
    echo "DONE — effect: page dirs rebuilt; postcondition: data/output/site/ serves rsc/site/ as authored (index.html stays render's)"
  else
    echo "DONE — no effect: data/output/site/ already serves rsc/site/ as authored"
  fi
}

case "${1:-}" in
  '')          status ;;
  sync)        shift; [[ $# -eq 0 ]] || { echo "site sync takes no arguments" >&2; exit 2; }; sync ;;
  render)      shift; render "$@" ;;
  -h|--help)   usage ;;
  *)           echo "yoga site: unknown verb '${1}'" >&2; usage >&2; exit 2 ;;
esac
