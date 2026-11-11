# shellcheck shell=bash
# corpus_shape.sh — the corpus's shape, stated ONCE: conversation markdown at any
# depth under a root (sourced by every shell consumer; python reads the layout
# through markdown_projection, the format authority).
#
# Left to each call site, the depth is decided once per caller and they disagree — one
# matching any depth, one two directory levels, one a single level. The corpus is two deep
# (data/output/markdown/<source>/<kind>/conversations/), so capture reported "no projected
# corpus" about the directory status had just counted, and told the reader to re-run a
# pipeline that had already produced it. Depth belongs to the layout, not to each caller.
CONVERSATIONS_GLOB='*/conversations/*.md'

has_conversations() {   # a root holding conversation markdown at any depth
  [[ -d "$1" ]] && [[ -n "$(find "$1" -path "$CONVERSATIONS_GLOB" -print -quit 2>/dev/null)" ]]
}

count_conversations() {
  find "$1" -path "$CONVERSATIONS_GLOB" 2>/dev/null | wc -l | tr -d ' '
}
