#!/usr/bin/env python
"""
render_corpus.py — render every projected session conversation
(tmp/cache/code-transport/<provider>/<machine>/<project>/<session>/conversation.json, the
sessionConversation data) into the served corpus, each provider's under its own root:
data/output/markdown/<provider>/code/conversations/<ordinal>-<slug>.md. Machines dedupe: the same
session held by several machines renders once, from its maximal copy.

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

A session with no projected talk renders honestly: title, provenance
bullets, no turns.

Usage:
    src/run_python_script.sh src/main/pipeline/code-transport/render_corpus.py [--out-root <dir>]
"""
import argparse
import json
import sys
from pathlib import Path

SELF = 'src/main/pipeline/code-transport/render_corpus.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main — the format authority
from markdown_projection import MD033_PRAGMA, REPO, assign_name, deposit  # noqa: E402


def render_session(conv):
    """sessionConversation dict -> corpus markdown. Mirrors render() in
    markdown_projection.py: frontmatter provenance dressing, h1 title, a
    plain-bullet preamble (sessions have no URL to link), role-labelled turn
    headings each carrying its durable anchor: the message uuid where the provider's
    record has one, else the role and count, as a gemini chat's turns are anchored."""
    label = {'human': 'Human', 'assistant': conv['provider'].capitalize()}
    count = {'human': 0, 'assistant': 0}
    out = ['---',
           'source: code-session',
           f"project: {conv['project']}",
           f"uuid: {conv['session_id']}",
           f"turns: {len(conv['messages'])}",
           f"last_activity: {conv['last_activity']}",
           '---', '',
           f"# {conv['title'] or 'Session ' + conv['session_id'][:8]}", '',
           MD033_PRAGMA, '',
           f"- {conv['harness']} session `{conv['session_id']}`",
           f"- Project `{conv['project']}`",
           '']
    for m in conv['messages']:
        count[m['role']] += 1
        anchor = m.get('uuid') or f"{label[m['role']].lower()}-{count[m['role']]}"
        out += [f"## {label[m['role']]} ({count[m['role']]}) <a id=\"{anchor}\"></a>",
                '', m['content'], '', '---', '']
    return '\n'.join(out).rstrip() + '\n'


def main() -> int:
    ap = argparse.ArgumentParser(description='render session conversations into the corpus')
    ap.add_argument('--out-root', default=str(REPO / 'data' / 'output' / 'markdown'))
    args = ap.parse_args()

    cache = REPO / 'tmp' / 'cache' / 'code-transport'
    rendered = 0
    for provider_dir in sorted(d for d in cache.glob('*') if d.is_dir()):
        rendered += render_provider(provider_dir, Path(args.out_root) / provider_dir.name / 'code' / 'conversations')
    if not rendered:
        print('code: no projected sessions under tmp/cache/code-transport — nothing to render')
    return 0


def render_provider(cache: Path, out: Path) -> int:
    """One provider's sessions into its corpus root; returns how many rendered."""
    provider = cache.name
    # One file per SESSION, across machines: several machines may hold the same
    # session (cache is keyed <machine>/<project>/<session>); the maximal copy
    # renders — most turns, then latest activity — since by the prefix
    # lattice the longest log holds every shorter one.
    held: dict = {}
    for f in sorted(cache.glob('*/*/*/conversation.json')):
        c = json.loads(f.read_text())
        if c.get('provider') != provider:
            print(f'FAIL: {f.relative_to(REPO)}: provider {c.get("provider")!r} under the cache of {provider!r}', file=sys.stderr)
            continue
        rival = held.get(c['session_id'])
        if rival is None or ((len(c['messages']), c['last_activity'])
                             > (len(rival['messages']), rival['last_activity'])):
            held[c['session_id']] = c
    convs = sorted(held.values(), key=lambda c: c['created'])
    if not convs:
        return 0

    width = len(str(len(convs)))  # ordered()'s width rule — the one enumeration style
    files, seen = {}, set()
    for i, c in enumerate(convs, 1):
        name = assign_name(c['title'] or c['session_id'][:8], c['session_id'], seen)
        files[f'{i:0{width}d}-{name}.md'] = render_session(c)
    deposit(out, files, f'{provider}/code: {len(files)} session(s)',
            because='its session left the store')
    return len(files)


if __name__ == '__main__':
    sys.exit(main())
