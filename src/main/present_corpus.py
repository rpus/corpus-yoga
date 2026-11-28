"""
present_corpus.py — render THE CORPUS dashboard: data/output/site/index.html.

The batch presenter (present.sh) renders ONE EXPORT's presentation under
cache/pipeline/claude/chat/bulk-export/<batch>/presentation — an export artifact, honestly filed under
its export. This is the corpus one: the keys are corpus_index's 1..N ordinals
over data/output/markdown (every source, claude first — the same numbers the book index,
the NN- filenames, and rekey_chats speak), the concept table is the judged index
(data/output/indexing/indexed-semantic-concepts.json, the one the server's index.md is written
from), the category table is the paid capture as it returned it, and every
conversation-keyed table is derived from the projected corpus itself, whole batches nowhere involved.

Values are best-effort by data reality: claude turn anchors are the messages'
UUIDv7 ids, whose first 48 bits are a millisecond timestamp, so claude lanes
carry real spans and dormancy; gemini scrapes hold no timestamps at all (ordinal
anchors, no frontmatter), so gemini lanes appear in the listing bar-less — the
absence is shown, never invented. Bolster the values when a source grows time
data; the KEYS are the contract.

Usage:
  present_corpus.py [--markdown <dir>] [--indexing <dir>] [--out <dir>] [--page-out <dir>] [--placed <n>]

Defaults: data/output/markdown, data/output/indexing, cache/site/presentation for the
data tables, data/output/site for the finished page (its URL position; all repo-relative).
The page is the human-facing artifact (library tier); the per-table JSON it is built
from — machine feedstock, re-derived on every run — stay behind in the cache workshop.
Called by site.sh (`corpus-yoga site build`), after the pages it placed, whose count --placed
carries so that one verdict speaks for the whole tree — free, local, re-derivable at will (L5).
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import facts
from markdown_projection import corpus_index, turn_seq  # the format authority owns the parsers
from page_declaration import declared_of, turn_instants  # the one reading of what a conversation declares and when its turns were (issues/1000, issues/1007)
from word_freq_literal import words_from, filtered, tables  # one tokenizer for both presenters
from library import LIBRARY as DOWNLOADED_DIR  # the artifact library, one authority (issues/421)

REPO = tier.REPO
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = REPO / 'rsc' / 'site' / 'index.template.html'
# The library's address and migration note come from library.py, the one authority (issues/421)
CHAT_PIPELINE = REPO / 'src' / 'main' / 'export'   # source-scoped helpers stay there (issues/407)
MAIN = REPO / 'src' / 'main'   # the shared-primitives tier: common code at src/main's root




def iso(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def spans_of(times: list[datetime]) -> list[tuple[str, str, int]]:
    """Contiguous same-day blocks (present.sh's span semantics), from turn instants."""
    out = []
    for t in sorted(times):
        if out and out[-1][0].date() == t.date():
            out[-1][1] = t
            out[-1][2] += 1
        else:
            out.append([t, t, 1])
    return [(iso(a), iso(b), n) for a, b, n in out]


def run_helper(script: Path, args: list[str], stdin_text: str | None = None) -> str:
    r = subprocess.run([sys.executable, str(script), *args],
                       input=stdin_text, capture_output=True, text=True, check=True)
    if r.stderr:
        print(r.stderr, file=sys.stderr, end='')
    return r.stdout


def write_table(out_dir: Path, key: str, table: dict, html: Path) -> None:
    """Align (format_table), persist in the cache workshop, inject into the page —
    one motion per table, matching the batch presenter's artifacts."""
    styled = run_helper(MAIN / 'format_table.py', [], json.dumps(table))
    f = out_dir / f'{key}.json'
    f.write_text(styled)
    subprocess.run([sys.executable, str(MAIN / 'inject.py'), str(html), key, str(f)], check=True)
    # a table injected empty because its input is absent is said so, never ticked
    if not table.get('rows') and str(table.get('note', '')).startswith(('Not captured', 'Not built')):
        print(f'  ○ {key} - absent; the page carries the note')
    else:
        print(f'  ✓ {key} ({len(table.get("rows", []))} rows)')


def concept_table(index: dict) -> dict:
    """The page's concept table from the judged index: each located headword, weighted by
    the turns it is found in, with the provider(s) those turns are in."""
    rows = []
    for head, _aliases, locators in index['rows']:
        if not locators:
            continue
        providers = sorted({rel.split('/', 1)[0] for rel, _role, _n, _anchor in locators})
        rows.append([head, len(locators), providers[0] if len(providers) == 1 else 'both'])
    return {'columns': ['word', 'count', 'provider'], 'rows': rows}


def built_from(index_file: Path, categories_file: Path) -> str:
    """What the page's two indexing tables are built from, by content: the judged index's own
    record of its inputs, and the digest of the categories as captured. The site status reads it
    back from the page's meta to say whether the page is current."""
    index = json.loads(index_file.read_text()).get('built_from', '') if index_file.is_file() else ''
    categories = 'sha256:' + hashlib.sha256(categories_file.read_bytes()).hexdigest() if categories_file.is_file() else ''
    return f'index {index or "absent"}; categories {categories or "absent"}'


def main() -> int:
    ap = argparse.ArgumentParser(description='render the corpus dashboard from data/output/markdown + data/output/indexing')
    ap.add_argument('--markdown', default=str(tier.DATA / 'output' / 'markdown'))
    ap.add_argument('--indexing', default=str(tier.DATA / 'output' / 'indexing'))
    ap.add_argument('--out', default=str(tier.CACHE / 'site' / 'presentation'),
                    help='cache workshop dir for the data tables (feedstock)')
    ap.add_argument('--page-out', default=str(tier.DATA / 'output' / 'site'),
                    help='publish-tree dir the finished index.html lands in (its URL position)')
    ap.add_argument('--placed', type=int, default=0, help='how many pages site.sh placed before the corpus page')
    args = ap.parse_args()

    md_root, dash = Path(args.markdown), Path(args.indexing)
    out_dir, page_out = Path(args.out), Path(args.page_out)
    entries = corpus_index(md_root)
    if not entries:
        # a room with no corpus skips, stated (issues/406, issues/494): the run's step must not fail
        rel = md_root.relative_to(REPO) if md_root.is_relative_to(REPO) else md_root
        facts.report(None, facts.act('site', 'build') + ': DONE - ' + facts.phrase('{placed} page(s) placed; index.html skipped - no projected corpus under {root}, which corpus-yoga pipeline collate projects', placed=args.placed, root=rel))
        return 0

    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    html = out_dir / 'index.html'
    shutil.copy(TEMPLATE, html)

    chats_rows, span_rows = [], []
    human_words, assistant_words = [], []
    by_dir = Counter()
    all_times: list[datetime] = []
    for n, stem, title, cid in entries:
        # provider/channel ARE the corpus path segments now — the unfused layout
        # made the old dirname decode ('code' meaning claude×code) a plain read.
        # Identity is still never taken from the id shape (code sessions carry
        # 36-char uuids too and would masquerade as claude chat).
        provider, channel, fname = stem.split('/')
        file_ord = fname.split('-', 1)[0]  # the per-channel ordinal from the data/output/markdown filename
        by_dir[f'{provider}/{channel}'] += 1
        md = (md_root / provider / channel / 'conversations' / f'{fname}.md').read_text()

        times = turn_instants(md)               # the heading's instant, else a v7 uuid's (issues/1007)
        all_times += times
        for a, b, count in spans_of(times):
            span_rows.append([n, a, b, count])
        m = re.search(r'^last_activity: (\S+)$', md[:400], flags=re.M)
        dormant = m.group(1) if m else (iso(max(times)) if times else '')
        said = declared_of(md)                 # what the page declares of the conversation (issues/1000), its turns from their one home (issues/1001)
        chats_rows.append([n, file_ord, title, dormant, cid, provider, channel, said['human'], said['assistant'], said['bytes']])

        for role, body in turn_seq(md):
            ws = filtered(words_from(body))
            (human_words if role == 'H' else assistant_words).append(ws)
    human_words = [w for ws in human_words for w in ws]
    assistant_words = [w for ws in assistant_words for w in ws]

    print(f'presenting the corpus: {len(entries)} conversations '
          f'({", ".join(f"{v} {k}" for k, v in sorted(by_dir.items()))}) → {out_dir.relative_to(REPO)}')

    write_table(out_dir, 'data-chats',
                {'columns': ['chat', 'ord', 'name', 'dormant_from', 'uuid', 'provider', 'channel', 'human', 'assistant', 'bytes'],
                 'rows': chats_rows}, html)
    write_table(out_dir, 'data-spans',
                {'columns': ['chat', 'from', 'to', 'messages'], 'rows': span_rows}, html)

    files_json = run_helper(CHAT_PIPELINE / 'files_from_downloaded.py', [str(DOWNLOADED_DIR), str(out_dir / 'data-chats.json')])
    write_table(out_dir, 'data-files', json.loads(files_json), html)

    # columnarise each sub-table into the template's {columns, rows} shape —
    # the same reshaping present.sh's jq_literal does for the batch page
    lit = {k: {'columns': ['word', 'count'], 'rows': [[d['word'], d['count']] for d in v]}
           for k, v in tables(human_words, assistant_words).items()}
    write_table(out_dir, 'data-literal-words', lit, html)

    index_file = dash / 'indexed-semantic-concepts.json'
    categories_file = dash / 'inferred-chat-categories.json'
    note = ('The headwords the reader accepted, each weighted by the turns it is found in and tagged with the '
            'provider(s) of those turns, from the judged index (data/output/indexing/indexed-semantic-concepts.json); '
            'corpus-yoga indexing build refreshes it.')
    table = (dict(concept_table(json.loads(index_file.read_text())), note=note) if index_file.is_file()
             else {'columns': [], 'rows': [], 'note': f'Not built yet — run `corpus-yoga indexing build`. {note}'})
    write_table(out_dir, 'data-semantic-concepts', table, html)
    note = ('Generated by Claude, as the paid capture returned it - no judgement of categories exists. Stored id-keyed '
            '(claude uuid / gemini app id); the chat index here is the corpus ordinal (corpus_index over '
            'data/output/markdown — every source), re-derived at presentation time. Refresh with `corpus-yoga indexing capture`.')
    if categories_file.exists():
        table = json.loads(run_helper(SCRIPT_DIR / 'rekey_chats.py', ['--to-ordinal', '--conversations', str(md_root)],
                                      categories_file.read_text()))
        table['note'] = note
    else:
        table = {'columns': [], 'rows': [], 'note': f'Not captured yet — run `corpus-yoga indexing capture`. {note}'}
    write_table(out_dir, 'data-chat-categories', table, html)

    claude_times = sorted(all_times)
    if claude_times:
        t0, t1 = claude_times[0], claude_times[-1]
        date_range = (f'{t0.strftime("%B")}–{t1.strftime("%B %Y")}' if t0.year == t1.year
                      else f'{t0.strftime("%B %Y")}–{t1.strftime("%B %Y")}')
    else:
        date_range = 'undated'
    title = (f'Conversation corpus — {len(entries)} conversations '
             f'({", ".join(f"{v} {k}" for k, v in sorted(by_dir.items()))}), {date_range}')
    html.write_text(re.sub(r'<title>.*?</title>',
                           f'<title>{title}</title>\n  <meta name="corpus-yoga-built-from" content="{built_from(index_file, categories_file)}">',
                           html.read_text(), count=1))
    # The page declares the inputs it was rendered from (issues/494): the corpus it folds
    # (the title) and the paid layer's coverage - so a render over lagging captures
    # reads as exactly what it is, anchored, never laundered.
    covered = 0
    if categories_file.exists():
        covered = len(json.loads(categories_file.read_text()).get('rows', []))
    subprocess.run([sys.executable, str(MAIN / 'update_export_tooltip.py'), str(html),
                    f'the projected corpus: {md_root.relative_to(REPO) if md_root.is_relative_to(REPO) else md_root}'
                    f' ({len(entries)} conversations); captures cover {covered} of them'
                    f' (data/output/indexing; corpus-yoga indexing capture refreshes, paid)'],
                   check=True)

    # The page is the human-facing artifact — it graduates to the library tier; the
    # data tables (self-contained, inlined above) stay behind in the cache workshop.
    page_out.mkdir(parents=True, exist_ok=True)
    page = page_out / 'index.html'
    if page.exists() and page.read_bytes() == html.read_bytes():
        # content-keyed (issues/494): current inputs mean no write, and a quiet run stays quiet
        html.unlink()
        facts.report(None, facts.act('site', 'build') + ': DONE - ' + (
            facts.phrase('{placed} page(s) placed; index.html already current', placed=args.placed) if args.placed
            else facts.phrase('no effect; data/output/site/ already holds rsc/site/ and the corpus page as built')))
        return 0
    page.unlink(missing_ok=True)
    shutil.move(str(html), str(page))
    print(f'  title: {title}')
    print(f'  data tables: {out_dir.relative_to(REPO)}/')
    facts.report(None, facts.act('site', 'build') + ': DONE - ' + facts.phrase('{placed} page(s) placed; {page} written', placed=args.placed,
                                                                              page=page.relative_to(REPO) if page.is_relative_to(REPO) else page))
    return 0


if __name__ == '__main__':
    sys.exit(main())
