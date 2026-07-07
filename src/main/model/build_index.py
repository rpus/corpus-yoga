#!/usr/bin/env python
"""
build_index.py — the book-style index over the corpus: headword → turn locators.

The first proper USE of the corpus rather than a means of building it. Scans the
readable markdown library (lib/markdown/{claude,gemini}/conversations/), matches
the curated headwords (rsc/index/headwords.txt: 'headword = alias, ...' lines,
case-insensitive on word boundaries), and writes lib/markdown/index.md — one
alphabetised entry per headword, locators grouped by conversation, every locator
a link to the turn's durable anchor (message uuid for claude, role-count for
gemini), so an entry survives corpus renumbering.

Human-and-agent-amenable by construction: the entry text reads as a book index
(conversation name, turn labels H3/A7), while every locator's href is a
machine-followable file#anchor. The headword file is the curation surface;
the index is derived dressing (regenerate at will; deterministic output — no
timestamps — so regeneration is a no-op when nothing changed, per CALCULUS L1).

Curation is reproducible from the repo, on the schema system's template
(candidates -> disposal record -> coverage gate): see rsc/index/README.md for
the two line-list formats (rsc/index/headwords.txt adopts, rsc/index/
decisions.txt declines) and the loop. --candidates derives the proposal report
as DATA (machine-local, under gen/index/) from the corpus and each batch's
inferred concept list; every inferred concept must end up adopted or declined —
anything else is PENDING, reported here and by the pre-commit data tier.

The disposal acts themselves are also verbs (the judgment stays human; the verb
only writes the committed line-lists with format discipline, then reports how
many inferred concepts remain pending):

Usage:
  src/run_python_script.sh src/main/model/build_index.py \
      [--markdown lib/markdown] [--headwords rsc/index/headwords.txt] \
      [--decisions rsc/index/decisions.txt]
  src/run_python_script.sh src/main/model/build_index.py --candidates [--top N]
  src/run_python_script.sh src/main/model/build_index.py headwords add <term> [alias ...]
  src/run_python_script.sh src/main/model/build_index.py decline <concept> [--because <why>]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO

TURN_RE = re.compile(
    r'^## (?P<role>Human|Claude|Gemini) \((?P<n>\d+)\) <a id="(?P<anchor>[^"]+)"></a>$',
    flags=re.M)

# Show this many turn links per (headword, conversation) before folding the rest
# into a "+N more" note — book indexes cite, they do not enumerate.
LOCATORS_SHOWN = 4


def parse_headwords(path: Path) -> dict[str, list[str]]:
    """{headword: [headword, alias, ...]} preserving file order of headwords."""
    entries: dict[str, list[str]] = {}
    for raw in path.read_text().splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        head, _, aliases = line.partition('=')
        head = head.strip()
        terms = [head] + [a.strip() for a in aliases.split(',') if a.strip()]
        entries[head] = terms
    return entries


def parse_decisions(path: Path) -> set[str]:
    """Lower-cased declined candidates from decisions.txt ('decline <term>' lines)."""
    declined = set()
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.split('#', 1)[0].strip()
            if line.startswith('decline '):
                declined.add(line[len('decline '):].strip().lower())
    return declined


def inferred_concepts() -> list[str]:
    """The finite candidate source: the latest batch's inferred concept list
    (machine-local; empty where no inference has run)."""
    import json
    files = sorted(d / 'inferred' / 'data-semantic.json'
                   for d in (REPO / 'gen' / 'chat-exports').glob('data-*'))
    files = [f for f in files if f.exists()]
    if not files:
        return []
    return [r[0] for r in json.loads(files[-1].read_text())['rows']]


def term_regex(terms: list[str]) -> re.Pattern:
    """One alternation over the headword and its aliases, word-bounded where the
    term's edges are word characters (so 'S/T'-ish terms still match sanely)."""
    parts = []
    for t in terms:
        esc = re.escape(t)
        lead = r'\b' if re.match(r'\w', t) else ''
        tail = r'\b' if re.search(r'\w$', t) else ''
        parts.append(f'{lead}{esc}{tail}')
    return re.compile('|'.join(parts), flags=re.I)


def turns_of(md: str):
    """[(role_letter, n, anchor, body)] for one conversation's markdown."""
    out = []
    matches = list(TURN_RE.finditer(md))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        role = 'H' if m['role'] == 'Human' else ('G' if m['role'] == 'Gemini' else 'A')
        out.append((role, int(m['n']), m['anchor'], md[m.end():end]))
    return out


def scan(markdown_root: Path):
    """[(source, stem, relpath, turns)] across the corpus, in listing order."""
    corpus = []
    for source in ('claude', 'gemini'):
        d = markdown_root / source / 'conversations'
        if not d.is_dir():
            continue
        for f in sorted(d.glob('*.md')):
            corpus.append((source, f.stem, f'{source}/conversations/{f.name}',
                           turns_of(f.read_text())))
    return corpus


def build(markdown_root: Path, headwords_path: Path) -> str:
    entries = parse_headwords(headwords_path)
    corpus = scan(markdown_root)

    lines = [
        '# Index',
        '',
        f'Headwords: `rsc/index/headwords.txt` (curated — edit and re-run '
        f'`src/main/model/build_index.py`). Locators link to durable turn anchors; '
        f'labels are H*n*/A*n* (claude) and H*n*/G*n* (gemini).',
        '',
    ]
    n_locators = 0
    hit_heads = 0
    letter = None
    for head in sorted(entries, key=str.lower):
        rx = term_regex(entries[head])
        per_conv = []
        for _source, stem, rel, turns in corpus:
            hits = [(role, n, anchor) for role, n, anchor, body in turns if rx.search(body)]
            if hits:
                per_conv.append((stem, rel, hits))
        if not per_conv:
            continue
        hit_heads += 1
        first = head[0].upper() if head[0].isalpha() else '·'
        if first != letter:
            letter = first
            lines += [f'## {letter}', '']
        lines.append(f'### {head}')
        for stem, rel, hits in per_conv:
            n_locators += len(hits)
            shown = [f'[{role}{n}]({rel}#{anchor})' for role, n, anchor in hits[:LOCATORS_SHOWN]]
            more = f' +{len(hits) - LOCATORS_SHOWN} more' if len(hits) > LOCATORS_SHOWN else ''
            lines.append(f'- [{stem}]({rel}#{hits[0][2]}) — {", ".join(shown)}{more}')
        lines.append('')
    lines += [
        '---',
        '',
        f'{hit_heads}/{len(entries)} headwords located; {n_locators} turn locators '
        f'across {len(corpus)} conversations.',
    ]
    return '\n'.join(lines) + '\n'


STOPWORDS = frozenset(
    """a about above after again all also am an and any are as at be because been
    before being below between both but by can could did do does doing down during
    each few for from further had has have having he her here hers him his how i
    if in into is it its itself just like me more most my no nor not now of off on
    once only or other our out over own same she should so some such than that the
    their them then there these they this those through to too under until up very
    was we were what when where which while who whom why will with would you your
    yours one two three first second new way many much may might must shall let us
    make made using use used get got say said see well thing things quite really
    actually indeed perhaps rather still yet even ever back right left good better
    yes something anything nothing everything someone anyone dont doesnt isnt cant
    im ive youre thats what's it's don't doesn't isn't can't that's here's exactly
    means mean case sense point time need needs want going go come comes work
    every each both again true false none non within without across against""".split())


def candidates(markdown_root: Path, headwords_path: Path, decisions_path: Path,
               top: int) -> None:
    """The machine's side of headword curation. Writes the proposal report as
    DATA (gen/index/candidates.md) and prints it; excludes declined candidates;
    names each inferred concept's disposal state. Never edits the curated files."""
    entries = parse_headwords(headwords_path)
    declined = parse_decisions(decisions_path)
    covered = term_regex([t for terms in entries.values() for t in terms])
    corpus = scan(markdown_root)

    from collections import Counter
    word_convs: dict[str, set] = {}
    counts: Counter = Counter()
    for _source, stem, _rel, turns in corpus:
        for _role, _n, _anchor, body in turns:
            for w in re.findall(r"[A-Za-z][A-Za-z'’-]{3,}", body):
                lw = w.lower().strip("'’-")
                if lw in STOPWORDS or lw in declined or covered.search(lw):
                    continue
                counts[lw] += 1
                word_convs.setdefault(lw, set()).add(stem)

    ranked = sorted(counts, key=lambda w: (-len(word_convs[w]), -counts[w]))
    pending = [c for c in inferred_concepts()
               if not covered.search(c) and c.lower() not in declined]

    lines = [
        '# Headword candidates',
        '',
        'Derived by `src/main/model/build_index.py --candidates` from the corpus and',
        'the latest inferred concept list; excludes candidates already adopted',
        '(`rsc/index/headwords.txt`) or declined (`rsc/index/decisions.txt`).',
        'Dispose of pending concepts by editing those two files — this report is',
        'derived data and never the record.',
        '',
        f'## Pending inferred concepts ({len(pending)})',
        '',
    ]
    lines += [f'- {c}' for c in pending] or ['(none — the concept list is fully disposed)']
    lines += ['', f'## Frequent uncovered corpus words (top {top} of {len(ranked)}; advisory)', '']
    lines += [f'- {w} — {len(word_convs[w])} conversation(s), {counts[w]}×'
              for w in ranked[:top]]
    report = '\n'.join(lines) + '\n'

    out = REPO / 'gen' / 'index' / 'candidates.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report, end='')
    print(f'-> {out.relative_to(REPO)}')


def adopt(headwords_path: Path, term: str, aliases: list[str]) -> str:
    """Adopt a headword (or merge new aliases into an existing one) in the
    committed line list. Append-at-end for new entries — the file's order is
    the curation history; presentation alphabetises (L5)."""
    entries = parse_headwords(headwords_path)
    lines = headwords_path.read_text().splitlines()
    if term in entries:
        known = {t.lower() for t in entries[term]}
        new = [a for a in aliases if a.lower() not in known]
        if not new:
            return f'{term!r}: already adopted — no-op'
        merged = entries[term][1:] + new
        for i, raw in enumerate(lines):
            if raw.split('#', 1)[0].partition('=')[0].strip() == term:
                lines[i] = f'{term} = {", ".join(merged)}'
                break
        headwords_path.write_text('\n'.join(lines) + '\n')
        return f'{term!r}: merged alias(es) {", ".join(new)}'
    line = term + (f' = {", ".join(aliases)}' if aliases else '')
    headwords_path.write_text('\n'.join(lines + [line]) + '\n')
    return f'{term!r}: adopted' + (f' with alias(es) {", ".join(aliases)}' if aliases else '')


def decline(headwords_path: Path, decisions_path: Path, concept: str, because: str) -> str:
    """Record a decline in the committed disposal record — unless the concept is
    already covered (adopted) or already declined; disposals never duplicate."""
    if concept.lower() in parse_decisions(decisions_path):
        return f'{concept!r}: already declined — no-op'
    entries = parse_headwords(headwords_path)
    if term_regex([t for ts in entries.values() for t in ts]).search(concept):
        return f'{concept!r}: already covered by an adopted headword — no decline needed'
    lines = decisions_path.read_text().splitlines() if decisions_path.exists() else []
    lines.append(f'decline {concept}' + (f'  # {because}' if because else ''))
    decisions_path.write_text('\n'.join(lines) + '\n')
    return f'{concept!r}: declined' + (f' ({because})' if because else '')


def pending_concepts(headwords_path: Path, decisions_path: Path) -> list[str]:
    """Inferred concepts not yet adopted or declined — the disposal queue."""
    entries = parse_headwords(headwords_path)
    declined = parse_decisions(decisions_path)
    covered = term_regex([t for ts in entries.values() for t in ts])
    return [c for c in inferred_concepts()
            if not covered.search(c) and c.lower() not in declined]


def pending_report(headwords_path: Path, decisions_path: Path) -> None:
    """The loop's feedback: how many inferred concepts remain undisposed."""
    if not inferred_concepts():
        print('pending: unknown — no inferred concept list on this machine')
        return
    pending = pending_concepts(headwords_path, decisions_path)
    print(f'pending: {len(pending)} inferred concept(s) undisposed'
          + (f' — next: {pending[0]!r}' if pending else ' — fully disposed'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--markdown', default=str(REPO / 'lib' / 'markdown'))
    ap.add_argument('--headwords', default=str(REPO / 'rsc' / 'index' / 'headwords.txt'))
    ap.add_argument('--decisions', default=str(REPO / 'rsc' / 'index' / 'decisions.txt'))
    ap.add_argument('--candidates', action='store_true',
                    help='derive the candidate report (gen/index/candidates.md) instead of building')
    ap.add_argument('--top', type=int, default=40)
    sub = ap.add_subparsers(dest='verb', help='curation verbs (default: build the index)')
    hw = sub.add_parser('headwords', help='bare: list pending concepts; add: adopt')
    hw_sub = hw.add_subparsers(dest='action')
    hw_add = hw_sub.add_parser('add', help='adopt a headword (or merge aliases into it)')
    hw_add.add_argument('term')
    hw_add.add_argument('aliases', nargs='*')
    dec = sub.add_parser('decline', help='record a decline in the disposal record')
    dec.add_argument('concept')
    dec.add_argument('--because', default='', help='reason, kept as a # comment')
    args = ap.parse_args()

    if args.verb == 'headwords':
        if args.action is None:
            # Bare noun: the state of the curation surface. Framing on stderr,
            # the pending queue as pure lines on stdout — human-amenable at the
            # terminal (both interleave), agent-amenable in a pipe (queue only).
            hw, dc = Path(args.headwords), Path(args.decisions)
            n_adopted, n_declined = len(parse_headwords(hw)), len(parse_decisions(dc))
            print(f'adopted: {n_adopted} entries ({hw.relative_to(REPO) if hw.is_relative_to(REPO) else hw}); '
                  f'declined: {n_declined} ({dc.relative_to(REPO) if dc.is_relative_to(REPO) else dc})',
                  file=sys.stderr)
            if not inferred_concepts():
                print('pending queue: unknown — no inferred concept list on this machine',
                      file=sys.stderr)
                return
            pending = pending_concepts(hw, dc)
            print(f'pending queue ({len(pending)} inferred concepts to dispose — '
                  'headwords add <term> adopts; decline <concept> refuses):'
                  if pending else 'pending queue: empty — fully disposed', file=sys.stderr)
            for c in pending:
                print(c)
            return
        print(adopt(Path(args.headwords), args.term, args.aliases))
        pending_report(Path(args.headwords), Path(args.decisions))
        return
    if args.verb == 'decline':
        print(decline(Path(args.headwords), Path(args.decisions), args.concept, args.because))
        pending_report(Path(args.headwords), Path(args.decisions))
        return

    root = Path(args.markdown)
    if args.candidates:
        candidates(root, Path(args.headwords), Path(args.decisions), args.top)
        return
    text = build(root, Path(args.headwords))
    out = root / 'index.md'
    out.write_text(text)
    print(f'index: {out.relative_to(REPO) if out.is_relative_to(REPO) else out} — '
          + text.rstrip().rsplit(chr(10), 1)[-1])


if __name__ == '__main__':
    main()
