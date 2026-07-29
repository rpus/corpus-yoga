#!/usr/bin/env python
"""
present_corpus.py — render THE CORPUS dashboard: data/output/site/index.html.

The batch presenter (present.sh) renders ONE EXPORT's presentation under
tmp/cache/chat-exports/<batch>/presentation — an export artifact, honestly filed under
its export. This is the corpus one: the keys are corpus_index's 1..N ordinals
over data/output/markdown (every source, claude first — the same numbers the book index,
the NN- filenames, and rekey_chats speak), the two captured tables come from
data/output/dashboard, and every conversation-keyed table is derived from the projected
corpus itself, whole batches nowhere involved.

Values are best-effort by data reality: claude turn anchors are the messages'
UUIDv7 ids, whose first 48 bits are a millisecond timestamp, so claude lanes
carry real spans and dormancy; gemini scrapes hold no timestamps at all (ordinal
anchors, no frontmatter), so gemini lanes appear in the listing bar-less — the
absence is shown, never invented. Bolster the values when a source grows time
data; the KEYS are the contract.

Usage:
  present_corpus.py [--markdown <dir>] [--dashboard <dir>] [--out <dir>] [--page-out <dir>]

Defaults: data/output/markdown, data/output/dashboard, tmp/cache/dashboard/presentation for the
data tables, data/output/site for the finished page (its URL position; all repo-relative).
The page is the human-facing artifact (library tier); the per-table JSON it is built
from — machine feedstock, re-derived on every run — stay behind in the cache workshop.
Called by dashboard.sh (`yoga dashboard sync`) — free, local, re-derivable at will (L5).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = REPO / 'rsc' / 'site' / 'index.html'
DOWNLOADED_DIR = REPO / 'data' / 'output' / 'artifacts' / 'downloaded'

sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(SCRIPT_DIR))
from markdown_projection import corpus_index, turn_seq  # noqa: E402 — the format authority owns the parsers
from word_freq_literal import words_from, filtered, tables  # noqa: E402 — one tokenizer for both presenters

ANCHOR = re.compile(r'^## (?:Human|Claude|Gemini) [^\n]*<a id="([0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"></a>', re.M)


def uuid7_time(u: str) -> datetime:
    """A UUIDv7's creation instant: its first 48 bits are milliseconds since epoch."""
    return datetime.fromtimestamp(int(u.replace('-', '')[:12], 16) / 1000, tz=timezone.utc)


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


def run_helper(script: str, args: list[str], stdin_text: str | None = None) -> str:
    r = subprocess.run([sys.executable, str(SCRIPT_DIR / script), *args],
                       input=stdin_text, capture_output=True, text=True, check=True)
    if r.stderr:
        print(r.stderr, file=sys.stderr, end='')
    return r.stdout


def write_table(out_dir: Path, key: str, table: dict, html: Path) -> None:
    """Align (format_table), persist in the cache workshop, inject into the page —
    one motion per table, matching the batch presenter's artifacts."""
    styled = run_helper('format_table.py', [], json.dumps(table))
    f = out_dir / f'{key}.json'
    f.write_text(styled)
    subprocess.run([sys.executable, str(SCRIPT_DIR / 'inject.py'), str(html), key, str(f)], check=True)
    print(f'  ✓ {key}')


def main() -> int:
    ap = argparse.ArgumentParser(description='render the corpus dashboard from data/output/markdown + data/output/dashboard')
    ap.add_argument('--markdown', default=str(REPO / 'data' / 'output' / 'markdown'))
    ap.add_argument('--dashboard', default=str(REPO / 'data' / 'output' / 'dashboard'))
    ap.add_argument('--out', default=str(REPO / 'tmp' / 'cache' / 'dashboard' / 'presentation'),
                    help='cache workshop dir for the data tables (feedstock)')
    ap.add_argument('--page-out', default=str(REPO / 'data' / 'output' / 'site'),
                    help='publish-tree dir the finished index.html lands in (its URL position)')
    args = ap.parse_args()

    md_root, dash = Path(args.markdown), Path(args.dashboard)
    out_dir, page_out = Path(args.out), Path(args.page_out)
    entries = corpus_index(md_root)
    if not entries:
        print(f'error: no projected corpus under {md_root}', file=sys.stderr)
        return 1

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

        times = [uuid7_time(u) for u in ANCHOR.findall(md)]
        all_times += times
        for a, b, count in spans_of(times):
            span_rows.append([n, a, b, count])
        m = re.search(r'^last_activity: (\S+)$', md[:400], flags=re.M)
        dormant = m.group(1) if m else (iso(max(times)) if times else '')
        turns = list(turn_seq(md))
        chats_rows.append([n, file_ord, title, dormant, cid, provider, channel, len(turns)])

        for role, body in turns:
            ws = filtered(words_from(body))
            (human_words if role == 'H' else assistant_words).append(ws)
    human_words = [w for ws in human_words for w in ws]
    assistant_words = [w for ws in assistant_words for w in ws]

    print(f'presenting the corpus: {len(entries)} conversations '
          f'({", ".join(f"{v} {k}" for k, v in sorted(by_dir.items()))}) → {out_dir.relative_to(REPO)}')

    write_table(out_dir, 'data-chats',
                {'columns': ['chat', 'ord', 'name', 'dormant_from', 'uuid', 'provider', 'channel', 'turns'],
                 'rows': chats_rows}, html)
    write_table(out_dir, 'data-spans',
                {'columns': ['chat', 'from', 'to', 'messages'], 'rows': span_rows}, html)

    files_json = run_helper('files_from_downloaded.py', [str(DOWNLOADED_DIR), str(out_dir / 'data-chats.json')])
    write_table(out_dir, 'data-files', json.loads(files_json), html)

    # columnarise each sub-table into the template's {columns, rows} shape —
    # the same reshaping present.sh's jq_literal does for the batch page
    lit = {k: {'columns': ['word', 'count'], 'rows': [[d['word'], d['count']] for d in v]}
           for k, v in tables(human_words, assistant_words).items()}
    write_table(out_dir, 'data-literal-words', lit, html)

    concepts_file = dash / 'semantic-concepts.json'
    categories_file = dash / 'chat-categories.json'
    for key, f, note in (
        ('data-semantic-concepts', concepts_file,
         'Generated by Claude. Weights are inferred concept salience, not raw frequencies; since v2 each '
         'concept is tagged with the provider(s) it is salient in. The durable single-source capture '
         '(data/output/dashboard/semantic-concepts.json); refresh with `yoga dashboard capture`.'),
        ('data-chat-categories', categories_file,
         'Generated by Claude. Stored id-keyed (claude uuid / gemini app id); the chat index here is the '
         'corpus ordinal (corpus_index over data/output/markdown — every source), re-derived at presentation time. '
         'Refresh with `yoga dashboard capture`.'),
    ):
        if not f.exists():
            table = {'columns': [], 'rows': [], 'note': f'Not captured yet — run `yoga dashboard capture`. {note}'}
        elif key == 'data-chat-categories':
            rekeyed = run_helper('rekey_chats.py', ['--to-ordinal', '--conversations', str(md_root)],
                                 f.read_text())
            table = json.loads(rekeyed)
            table['note'] = note
        else:
            table = json.loads(f.read_text())
            table['note'] = note
        write_table(out_dir, key, table, html)

    claude_times = sorted(all_times)
    if claude_times:
        t0, t1 = claude_times[0], claude_times[-1]
        date_range = (f'{t0.strftime("%B")}–{t1.strftime("%B %Y")}' if t0.year == t1.year
                      else f'{t0.strftime("%B %Y")}–{t1.strftime("%B %Y")}')
    else:
        date_range = 'undated'
    title = (f'Conversation corpus — {len(entries)} conversations '
             f'({", ".join(f"{v} {k}" for k, v in sorted(by_dir.items()))}), {date_range}')
    html.write_text(re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html.read_text()))
    subprocess.run([sys.executable, str(SCRIPT_DIR / 'update_export_tooltip.py'), str(html),
                    f'the projected corpus: {md_root.relative_to(REPO) if md_root.is_relative_to(REPO) else md_root}'],
                   check=True)

    # The page is the human-facing artifact — it graduates to the library tier; the
    # data tables (self-contained, inlined above) stay behind in the cache workshop.
    page_out.mkdir(parents=True, exist_ok=True)
    page = page_out / 'index.html'
    page.unlink(missing_ok=True)
    shutil.move(str(html), str(page))
    print(f'  title: {title}')
    print(f'  data tables: {out_dir.relative_to(REPO)}/')
    print(f'→ {page.relative_to(REPO) if page.is_relative_to(REPO) else page}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
