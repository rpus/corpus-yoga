"""
render_corpus.py — place every session the run rendered
(cache/pipeline/<provider>/code/machine-transport/<machine>/<project>/<session>/conversation.md, with
facts.json beside it, src/main/agent/render.py) in the served corpus, each provider's under its own
root: data/output/markdown/<provider>/code/conversations/<ordinal>-<slug>.md. Machines dedupe: the
same session held by several machines is placed once, from its maximal copy.

The code source joins the corpus exactly as claude and gemini do: files carry
the '<ordinal>-<slug>' stem corpus_index requires, an h1 title, and
frontmatter whose uuid line is the identity conv_id reads back — so serve,
the book index, and the concept capture see sessions like any other
conversations. Ordinals are a fresh 1..N enumeration over ALL of one provider's local sessions
in created order (sessionConversation.created, the session's whole span):
presentation dressing, renumbered freely; the uuid is the identity, and a
slug collision is disambiguated by uuid8 (assign_name). reconcile_dir keeps
the write idempotent: an unchanged file keeps its mtime, a departed session's
file is pruned.


Usage:
    src/run_python_script.sh src/main/agent/render_corpus.py [--out-root <dir>]
"""
import argparse
import json
import sys
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import corpus
from markdown_projection import FACTS, RENDERED, REPO, assign_name, deposit

SELF = 'src/main/agent/render_corpus.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]


def main() -> int:
    ap = argparse.ArgumentParser(description='render session conversations into the corpus')
    ap.add_argument('--out-root', default=str(tier.DATA / 'output' / 'markdown'))
    args = ap.parse_args()

    rendered = 0
    for store in (s for s in corpus.stores() if s.pipeline == 'agent'):
        rendered += render_provider(str(store.provider), corpus.store_cache('agent', store.provider),
                                    Path(args.out_root) / str(store.provider) / 'code' / 'conversations')
    if not rendered:
        print('code: no projected sessions under the agent stores\' caches — nothing to render')
    return 0


def render_provider(provider: str, cache: Path, out: Path) -> int:
    """One provider's rendered sessions, under its store's cache, into its corpus root; returns how many placed."""
    # One file per SESSION, across machines: several machines may hold the same
    # session (cache is keyed <machine>/<project>/<session>); the maximal copy
    # renders — most turns, then latest activity — since by the prefix
    # lattice the longest log holds every shorter one.
    unrendered = [str(f.parent.relative_to(cache)) for f in sorted(cache.glob('*/*/*/conversation.json'))
                  if not ((f.parent / FACTS).is_file() and (f.parent / RENDERED).is_file())]
    if unrendered:
        # depositing without a session's rendering would prune its file
        sys.exit(f"no rendering at the cache address of {len(unrendered)} {provider} session(s) - {', '.join(unrendered)}; "
                 f"corpus-yoga pipeline run renders each")
    held: dict = {}
    for f in sorted(cache.glob(f'*/*/*/{FACTS}')):
        c = json.loads(f.read_text())
        if c.get('provider') != provider:
            print(f'FAIL: {f.relative_to(REPO)}: provider {c.get("provider")!r} under the cache of {provider!r}', file=sys.stderr)
            continue
        rival = held.get(c['session_id'])
        if rival is None or ((c['turns'], c['last_activity']) > (rival['turns'], rival['last_activity'])):
            held[c['session_id']] = {**c, 'at': f.parent}
    convs = sorted(held.values(), key=lambda c: c['created'])
    if not convs:
        return 0

    width = len(str(len(convs)))  # ordered()'s width rule — the one enumeration style
    files, seen = {}, set()
    for i, c in enumerate(convs, 1):
        name = assign_name(c['title'] or c['session_id'][:8], c['session_id'], seen)
        files[f'{i:0{width}d}-{name}.md'] = (c['at'] / RENDERED).read_text()
    deposit(out, files, f'{provider}/code: {len(files)} session(s)',
            because='its session left the store')
    return len(files)


if __name__ == '__main__':
    sys.exit(main())
