#!/usr/bin/env python
"""
indexing.py — the book-style index over the corpus (headword → turn locators)
and the curation surface behind it: accept / reject / list-candidates over the concept
capture. Driven by `corpus-yoga indexing` (see src/main/cli/).

Building an index is the first proper USE of the corpus rather than merely writing into it.
It scans the readable markdown library (data/output/markdown/{claude,gemini}/conversations/),
matches the accepted headwords (data/output/indexing/accepted-semantic-concepts.txt: 'headword = alias,
...' lines, case-insensitive on word boundaries), and writes data/output/markdown/index.md —
one alphabetised entry per headword, locators grouped by conversation, every locator
a link to the turn's durable anchor (message uuid for claude, role-count for
gemini), so an entry survives corpus renumbering.

Human-and-agent-amenable by construction: the entry text reads as a book index
(conversation name, turn labels H3/A7), while every locator's href is a
machine-followable file#anchor. accepted-semantic-concepts.txt is the curation surface; the index
is derived dressing (regenerate at will; deterministic output — no timestamps —
so regeneration is a no-op when nothing changed, per CALCULUS L1).

Curation is reproducible from the repo, on the schema system's template
(candidates -> disposal record -> coverage gate): see src/main/cli/readings.md
for the three line-list formats (accepted-semantic-concepts.txt, rejected-semantic-concepts.txt, candidate-semantic-concepts.txt) and
the loop. `list-candidates` derives the candidates into a rebuildable tmp/cache/ file
(tmp/cache/indexing/candidate-semantic-concepts.txt) from the single-source concept capture
(data/output/indexing/inferred-semantic-concepts.json); every captured concept must end up
accepted or rejected — anything else is a CANDIDATE, reported here and by the
pre-commit data tier.

The disposal acts (accept / reject) are verbs too: the judgment stays human; the
verb only writes the durable line-lists with format discipline, then reports how
many candidates remain.

Usage (via corpus-yoga indexing):
  corpus-yoga indexing                                    # status: counts + candidates
  corpus-yoga indexing list-candidates [--top N]          # derive tmp/cache/indexing/candidate-semantic-concepts.txt: each
      #   candidate concept with the aliases that anchor it; the unanchorable named, not queued
  corpus-yoga indexing accept <term> [alias ...]          # accept a concept (merge aliases)
  corpus-yoga indexing accept --all                       # accept the whole queue as read, aliases folded in
  corpus-yoga indexing reject [--reason <why>] <concept>  # reject a concept
  corpus-yoga indexing reject --all [--reason <why>]      # reject the whole queue as read
  corpus-yoga indexing sync                               # build data/output/markdown/index.md
  corpus-yoga indexing capture [--conversations <path>]   # PAID: the model re-reads the corpus for
      [--only semantic-concepts|chat-categories]   #   the two index tables (see capture.sh);
      [--dry-run]                                  #   --dry-run: coverage preview, spends nothing
"""
import re
import sys
from pathlib import Path

SELF = 'src/main/cli/indexing/indexing.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main/ on the path
from markdown_projection import REPO
from declared_parser import command_parser

MARKDOWN_DIR = REPO / 'data' / 'output' / 'markdown'                    # the corpus to index
ACCEPTED_FILE = REPO / 'data' / 'output' / 'indexing' / 'accepted-semantic-concepts.txt'  # the concepts accepted as headwords (read + written)
REJECTED_FILE = REPO / 'data' / 'output' / 'indexing' / 'rejected-semantic-concepts.txt'  # the concepts rejected, with reasons (read + written)

TURN_RE = re.compile(
    r'^## (?P<role>Human|Claude|Gemini) \((?P<n>\d+)\) <a id="(?P<anchor>[^"]+)"></a>$',
    flags=re.M)

# Show this many turn links per (headword, conversation) before folding the rest
# into a "+N more" note — book indexes cite, they do not enumerate.
LOCATORS_SHOWN = 4


def parse_accepted(path: Path) -> dict[str, list[str]]:
    """{headword: [headword, alias, ...]} preserving file order of headwords.
    Absent file → empty (accepted-semantic-concepts.txt lives in git-ignored data/output/, so a fresh machine
    before iCloud sync has none — degrade to 'no headwords', never crash)."""
    entries: dict[str, list[str]] = {}
    if not path.exists():
        return entries
    for raw in path.read_text().splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        head, _, aliases = line.partition('=')
        head = head.strip()
        terms = [head] + [a.strip() for a in aliases.split(',') if a.strip()]
        entries[head] = terms
    return entries


def parse_rejected(path: Path) -> set[str]:
    """Lower-cased rejected concepts from data/output/indexing/rejected-semantic-concepts.txt — one per
    line, 'term # optional reason' (the file name says 'rejected', so no verb
    prefix). A '# …'-only line is a comment."""
    rejected = set()
    if path.exists():
        for raw in path.read_text().splitlines():
            term = raw.split('#', 1)[0].strip()
            if term:
                rejected.add(term.lower())
    return rejected


def inferred_concepts() -> list[str]:
    """The finite candidate source: the single-source concept capture
    data/output/indexing/inferred-semantic-concepts.json (a model reading the corpus; refresh with `corpus-yoga indexing capture`).
    Durable and shared across machines (via data/output/), so both curate one shared base — the
    24-vs-27 divergence of the old per-batch, per-machine tmp/cache/ inference is gone.
    Empty where no capture has been taken yet."""
    import json
    f = INFERRED_FILE
    if not f.exists():
        return []
    return [r[0] for r in json.loads(f.read_text()).get('rows', [])]


def term_regex(terms: list[str]) -> re.Pattern:
    """One alternation over the headword and its aliases, word-bounded where the
    term's edges are word characters (so 'S/T'-ish terms still match sanely).
    Empty terms → a NEVER-match pattern: '|'.join([]) is '' which matches every
    string, so an empty accepted-semantic-concepts.txt would silently mark every concept covered."""
    if not terms:
        return re.compile(r'(?!)')
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
    """[(source, stem, relpath, turns)] across the corpus, in listing order.
    The book index covers the chat channel of each provider (code sessions are
    corpus but not book — unchanged since the fused layout, where code/ was
    likewise unscanned)."""
    corpus = []
    for source in ('claude', 'gemini'):
        d = markdown_root / source / 'chat' / 'conversations'
        if not d.is_dir():
            continue
        for f in sorted(d.glob('*.md')):
            corpus.append((source, f.stem, f'{source}/chat/conversations/{f.name}',
                           turns_of(f.read_text())))
    return corpus


ANCHOR_STOPWORDS = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'vs', 'with'}


def _fold(word: str) -> list[str]:
    """A word and its number-folded twin: plural to singular and back, the one
    inflection the model's paraphrase and the turn's text differ on most
    ("commutative squares" against "a commutative square"). A capitalised word
    is a name and keeps its form; a word ending in a double s is never a plural."""
    if word[:1].isupper() or word.endswith('ss') or len(word) < 4:
        return [word]
    if word.endswith('ies'):
        return [word, word[:-3] + 'y']
    if word.endswith('s'):
        return [word, word[:-1]]
    if word.endswith('y'):
        return [word, word[:-1] + 'ies']
    return [word, word + 's']


def runs_of(concept: str) -> list[str]:
    """The concept itself, then every run of two or more of its content words,
    longest first, then a single word only where it is hyphenated (multi-agent) -
    a bare common word (map, square, truth) would index noise, so it is never
    proposed. What the anchoring tries, as the reader sees it."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", concept) if w.lower() not in ANCHOR_STOPWORDS]
    out = [concept]
    for size in range(len(words), 1, -1):
        out += [' '.join(words[start:start + size]) for start in range(0, len(words) - size + 1)]
    out += [w for w in words if '-' in w]
    seen: list[str] = []
    for ph in out:
        if ph.lower() not in [x.lower() for x in seen]:
            seen.append(ph)
    return seen


def phrasings_of(concept: str) -> list[str]:
    """Every phrasing the anchoring tries: each run of runs_of with each of its
    words in either number. Deterministic, so the queue derives the same on
    every machine that holds the corpus (#644)."""
    out: list[str] = []
    for run in runs_of(concept):
        variants: list[list[str]] = [[]]
        for w in run.split(' '):
            variants = [v + [f] for v in variants for f in _fold(w)]
        out += [' '.join(v) for v in variants]
    seen: list[str] = []
    for ph in out:
        if ph.lower() not in [x.lower() for x in seen]:
            seen.append(ph)
    return seen


def anchors_of(concept: str, bodies: list[str]) -> list[str]:
    """The phrasings of a concept that occur in at least one conversation turn,
    longest first - the aliases an accepted headword needs to have locators.
    Empty means the corpus cannot index the concept as the model phrased it."""
    found = []
    for ph in phrasings_of(concept):
        rx = term_regex([ph])
        if any(rx.search(b) for b in bodies):
            found.append(ph)
    return found


def turn_bodies(markdown_root: Path) -> list[str]:
    """Every turn body the index scans - the one text the anchoring judges against."""
    return [t[3] for _source, _stem, _rel, turns in scan(markdown_root) for t in turns]


def anchored_split(concepts: list[str], markdown_root: Path) -> tuple[list[tuple[str, list[str]]], list[tuple[str, list[str]]]]:
    """(anchored, unanchorable): each anchored concept with the aliases that anchor it,
    the concept itself omitted where it anchors as spelled; each unanchorable
    concept with the runs tried (each in either number). The queue is the
    anchored half; the unanchorable half is named, never queued (#644)."""
    bodies = turn_bodies(markdown_root) if markdown_root.is_dir() else []
    anchored, unanchorable = [], []
    for c in concepts:
        found = anchors_of(c, bodies)
        if found:
            anchored.append((c, [a for a in found if a.lower() != c.lower()]))
        else:
            unanchorable.append((c, runs_of(c)))
    return anchored, unanchorable


def build(markdown_root: Path, accepted_path: Path) -> str:
    entries = parse_accepted(accepted_path)
    corpus = scan(markdown_root)

    lines = [
        '# Index',
        '',
        # No tier path here, deliberately: the index is a CORPUS artifact, and
        # naming a machinery path in it couples corpus bytes to repo layout —
        # any tier move would rewrite corpus content. The verb is the stable
        # surface; `corpus-yoga indexing -h` says where things live.
        f'Headwords are curated with `corpus-yoga indexing` (accept/reject; `sync` '
        f'rebuilds this index). Locators link to durable turn anchors; '
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


INFERRED_FILE = REPO / 'data' / 'output' / 'indexing' / 'inferred-semantic-concepts.json'  # the model's proposals, corpus-yoga indexing capture's (read)
CANDIDATES_TXT = REPO / 'tmp' / 'cache' / 'indexing' / 'candidate-semantic-concepts.txt'


def _coverage(accepted_path: Path, rejected_path: Path):
    """The disposal predicate's state, in ONE place: (covered, rejected) — a regex
    over every accepted headword+alias, and the set of rejected concepts. A concept
    is DISPOSED iff covered.search(c) or c.lower() in rejected; a candidate otherwise.
    pending_concepts and the candidates() advisory both build from this, so 'what
    counts as disposed' has a single definition."""
    entries = parse_accepted(accepted_path)
    covered = term_regex([t for terms in entries.values() for t in terms])
    return covered, parse_rejected(rejected_path)


def candidates_report(accepted_path: Path, rejected_path: Path, markdown_root: Path) -> str:
    """The candidates as a line-list in accepted-semantic-concepts.txt's own format - one concept
    per line, `concept = alias, alias` where the concept anchors only by its
    aliases - the third disposal state beside accepted-semantic-concepts.txt and rejected-semantic-concepts.txt, and
    a DETERMINISTIC, reproducible derivation of
    data/output/indexing/inferred-semantic-concepts.json − accepted − rejected −
    unanchorable. Its format doc lives in src/main/cli/readings.md; here it is
    just the data. Reproducible, so it is a rebuildable tmp/cache/ file,
    regenerated on demand (not committed, not gated)."""
    anchored, _ = anchored_split(pending_concepts(accepted_path, rejected_path), markdown_root)
    lines = [c + (f' = {", ".join(aliases)}' if aliases else '') for c, aliases in anchored]
    return '\n'.join(lines) + ('\n' if lines else '')


def candidates(markdown_root: Path, accepted_path: Path, rejected_path: Path,
               top: int | None) -> None:
    """Write the candidate line-list (tmp/cache/indexing/candidate-semantic-concepts.txt) AND print it —
    the queue is the deliverable, so the console leads with it, never with a
    side report. The optional frequency advisory (frequent uncovered corpus
    words, --top N) scans data/output/markdown, so it is never filed — it would differ
    per machine — and it prints only when explicitly asked for: its raw word
    ranking is a prospecting aid, not the queue, and unasked it buried the
    queue under noise (user report, 2026-07-11)."""
    report = candidates_report(accepted_path, rejected_path, markdown_root)
    CANDIDATES_TXT.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES_TXT.write_text(report)
    pending = [l for l in report.splitlines() if l.strip()]
    print(f'{len(pending)} candidate concept(s) -> {CANDIDATES_TXT.relative_to(REPO)}'
          + (' - each anchors in the corpus by the aliases shown; dispose each: '
             'corpus-yoga indexing accept "<concept>" [alias ...] | reject "<concept>", or --all as read'
             if pending else ''))
    for c in pending:
        print(f'  {c}')
    _, unanchorable = anchored_split(pending_concepts(accepted_path, rejected_path), markdown_root)
    if unanchorable:
        print(f'{len(unanchorable)} unanchorable concept(s) - no phrasing occurs in any conversation turn, '
              'so the corpus cannot index them; named, not queued:')
        for c, tried in unanchorable:
            print(f'  {c}  (tried, in either number: {", ".join(tried)})')
    if top is None:
        return

    covered, rejected = _coverage(accepted_path, rejected_path)
    from collections import Counter
    word_convs: dict[str, set] = {}
    counts: Counter = Counter()
    for _source, stem, _rel, turns in scan(markdown_root):
        for _role, _n, _anchor, body in turns:
            for w in re.findall(r"[A-Za-z][A-Za-z'’-]{3,}", body):
                lw = w.lower().strip("'’-")
                if lw in STOPWORDS or lw in rejected or covered.search(lw):
                    continue
                counts[lw] += 1
                word_convs.setdefault(lw, set()).add(stem)
    ranked = sorted(counts, key=lambda w: (-len(word_convs[w]), -counts[w]))
    print(f'\n## Frequent uncovered corpus words (top {top} of {len(ranked)}; '
          'advisory — machine-local, terminal only)')
    for w in ranked[:top]:
        print(f'- {w} — {len(word_convs[w])} conversation(s), {counts[w]}×')


def accept(accepted_path: Path, term: str, aliases: list[str]) -> str:
    """Accept a concept as a headword (or merge new aliases into an existing one)
    in the durable line list. Append-at-end for new entries — the file's order
    is the curation history; presentation alphabetises (L5)."""
    entries = parse_accepted(accepted_path)
    accepted_path.parent.mkdir(parents=True, exist_ok=True)  # bootstrap on a fresh machine
    lines = accepted_path.read_text().splitlines() if accepted_path.exists() else []
    # Merge-vs-new is decided case-INSENSITIVELY, like coverage matching everywhere
    # else (term_regex, reject); otherwise 'Mathematics' would append a second entry
    # beside 'mathematics'. Merge into the already-curated headword, keeping its casing.
    existing = {h.lower(): h for h in entries}
    if not aliases and term.lower() not in existing and MARKDOWN_DIR.is_dir():
        # a concept accepted as the queue listed it takes the aliases the queue showed
        # for it - the phrasings that anchor it in a turn - so one word never makes an
        # orphan; aliases typed by hand override (#644)
        aliases = [a for a in anchors_of(term, turn_bodies(MARKDOWN_DIR)) if a.lower() != term.lower()]
    if term.lower() in existing:
        head = existing[term.lower()]
        known = {t.lower() for t in entries[head]}
        new = [a for a in aliases if a.lower() not in known]
        if not new:
            return f'{term!r}: already accepted' + (f' (as {head!r})' if head != term else '') + ' — no-op'
        merged = entries[head][1:] + new
        for i, raw in enumerate(lines):
            if raw.split('#', 1)[0].partition('=')[0].strip().lower() == head.lower():
                lines[i] = f'{head} = {", ".join(merged)}'
                break
        accepted_path.write_text('\n'.join(lines) + '\n')
        return f'{head!r}: merged alias(es) {", ".join(new)}'
    line = term + (f' = {", ".join(aliases)}' if aliases else '')
    accepted_path.write_text('\n'.join(lines + [line]) + '\n')
    return f'{term!r}: accepted' + (f' with alias(es) {", ".join(aliases)}' if aliases else '')


def reject(accepted_path: Path, rejected_path: Path, concept: str, reason: str) -> str:
    """Record a rejection in the durable disposal record — unless the concept is
    already covered (accepted) or already rejected; disposals never duplicate."""
    if concept.lower() in parse_rejected(rejected_path):
        return f'{concept!r}: already rejected — no-op'
    entries = parse_accepted(accepted_path)
    if term_regex([t for ts in entries.values() for t in ts]).search(concept):
        return f'{concept!r}: already covered by an accepted headword — no rejection needed'
    rejected_path.parent.mkdir(parents=True, exist_ok=True)  # bootstrap on a fresh machine
    lines = rejected_path.read_text().splitlines() if rejected_path.exists() else []
    lines.append(f'{concept}' + (f'  # {reason}' if reason else ''))
    rejected_path.write_text('\n'.join(lines) + '\n')
    return f'{concept!r}: rejected' + (f' ({reason})' if reason else '')


def dispose_all(accepted_path: Path, rejected_path: Path, verb: str, reason: str) -> str:
    """Enact the DERIVED queue — tmp/cache/indexing/candidate-semantic-concepts.txt, the artifact the
    reviewer read — never a live recomputation (#355). A missing or drifted queue is
    a refusal, so what is disposed is provably what was reviewed; the judgment stays
    human, its unit the list the human read. Wholesale accept folds each candidate's
    anchoring aliases in (#644; accepted-semantic-concepts.txt stays hand-editable); wholesale
    reject stamps the one reason on every line."""
    if not CANDIDATES_TXT.exists():
        return ('refused: no derived queue — run `corpus-yoga indexing list-candidates`, '
                'read it, then --all')
    as_read = CANDIDATES_TXT.read_text()
    live = candidates_report(accepted_path, rejected_path, MARKDOWN_DIR)
    if as_read != live:
        return ('refused: the queue moved since you listed it — re-run '
                '`corpus-yoga indexing list-candidates`, re-read, then --all')
    queue = [line.strip() for line in as_read.splitlines() if line.strip()]
    if not queue:
        return 'no candidates — the derived queue is empty'
    for line in queue:
        # the queue line is accepted-semantic-concepts.txt's own format: the concept, then the aliases
        # that anchor it - accepting folds them in, so a wholesale accept makes no orphan
        concept, _, aliases = line.partition('=')
        concept = concept.strip()
        alias_list = [a.strip() for a in aliases.split(',') if a.strip()]
        if verb == 'accept':
            print(accept(accepted_path, concept, alias_list))
        else:
            print(reject(accepted_path, rejected_path, concept, reason))
    # the queue is disposed; re-derive so the filed artifact stays the truth
    CANDIDATES_TXT.write_text(candidates_report(accepted_path, rejected_path, MARKDOWN_DIR))
    word = 'accepted' if verb == 'accept' else 'rejected'
    return f'{len(queue)} concept(s) {word}, the queue as read'


def pending_concepts(accepted_path: Path, rejected_path: Path) -> list[str]:
    """Captured concepts not yet accepted or rejected — the disposal queue."""
    covered, rejected = _coverage(accepted_path, rejected_path)
    return [c for c in inferred_concepts()
            if not covered.search(c) and c.lower() not in rejected]


def pending_report(accepted_path: Path, rejected_path: Path) -> None:
    """The loop's feedback: how many captured concepts remain undisposed, and how
    many the corpus cannot index and so are never queued."""
    if not inferred_concepts():
        print('candidates: unknown — no concept capture on this machine (corpus-yoga indexing capture)')
        return
    anchored, unanchorable = anchored_split(pending_concepts(accepted_path, rejected_path), MARKDOWN_DIR)
    print(f'candidates: {len(anchored)} concept(s) undisposed'
          + (f' - next: {anchored[0][0]!r} (corpus-yoga indexing accept "<term>" or reject "<concept>")' if anchored else ' - fully disposed')
          + (f'; {len(unanchorable)} unanchorable, named by list-candidates, not queued' if unanchorable else ''))


def orphan_headwords(markdown_root: Path, accepted_path: Path) -> list[str]:
    """Accepted headwords with ZERO corpus locators — the disposal record's
    orphan documentation, the reverse direction of the curate discipline (the
    model.json precedent, PR #36: a curation record must be grounded both ways).
    build() has always computed this — the located/total ratio in the sync
    line — but as an aggregate; a dead index entry (its concept left the
    corpus, or its aliases never matched) was a count, not a name. Same scan
    build() runs, so the two can never disagree."""
    entries = parse_accepted(accepted_path)
    corpus = scan(markdown_root)
    return sorted((h for h in entries
                   if not any(term_regex(entries[h]).search(body)
                              for _source, _stem, _rel, turns in corpus
                              for _role, _n, _anchor, body in turns)),
                  key=str.lower)


def anchor_report(concepts_file: Path, markdown_root: Path) -> None:
    """What the paid call bought, judged before promotion (#644): of the captured
    concepts not already disposed, which the corpus can index, by which
    phrasings, and which it cannot - the spend on those is visible here and
    nowhere else, since they never reach the queue."""
    import json
    concepts = [r[0] for r in json.loads(Path(concepts_file).read_text()).get('rows', [])]
    covered, rejected = _coverage(ACCEPTED_FILE, REJECTED_FILE)
    new = [c for c in concepts if not covered.search(c) and c.lower() not in rejected]
    anchored, unanchorable = anchored_split(new, markdown_root)
    print(f'  anchors: {len(concepts)} concept(s) captured, {len(concepts) - len(new)} already disposed; '
          f'of the {len(new)} new, {len(anchored)} anchor in a conversation turn and will be queued'
          + (f', {len(unanchorable)} do not and will not be:' if unanchorable else ''))
    for c, tried in unanchorable:
        print(f'    {c}  (tried, in either number: {", ".join(tried)})')


def status(accepted_path: Path, rejected_path: Path, markdown_root: Path) -> None:
    """Read-only state of data/output/indexing/ (bare `corpus-yoga indexing`): counts on
    stderr, the candidates as pure lines on stdout — human-amenable at the
    terminal (both interleave), agent-amenable in a pipe (queue only)."""
    a_rel = accepted_path.relative_to(REPO) if accepted_path.is_relative_to(REPO) else accepted_path
    r_rel = rejected_path.relative_to(REPO) if rejected_path.is_relative_to(REPO) else rejected_path
    n_accepted, n_rejected = len(parse_accepted(accepted_path)), len(parse_rejected(rejected_path))
    print(f'accepted: {n_accepted} entries ({a_rel}); rejected: {n_rejected} ({r_rel})',
          file=sys.stderr)
    if markdown_root.is_dir() and n_accepted:
        orphans = orphan_headwords(markdown_root, accepted_path)
        print(('FAIL: ' if orphans else '')
              + f'orphans: {len(orphans)} accepted headword(s) with zero corpus locators'
              + (f' — {", ".join(orphans)} (fix the aliases, or remove the line and '
                 f'reject the concept with a reason)' if orphans else ''),
              file=sys.stderr)
    if not inferred_concepts():
        print('candidates: unknown — no concept capture on this machine '
              '(corpus-yoga indexing capture)', file=sys.stderr)
        return
    anchored, unanchorable = anchored_split(pending_concepts(accepted_path, rejected_path), markdown_root)
    pending = [c for c, _ in anchored]
    # A nonzero queue is a violated property (every queued concept disposed),
    # stated as a FAIL atom (#535 - the dev gate's former concept_disposed
    # invocations, spoken here once); the names follow as the queue lines. A
    # concept the corpus cannot index is not the reader's to dispose: it is named
    # with what was tried, and the next capture may phrase it again (#644).
    print(f'FAIL: candidates: {len(pending)} concept(s) undisposed - each is the reader\'s act: '
          'corpus-yoga indexing accept "<term>" or corpus-yoga indexing reject "<concept>" --reason "<why>" '
          '(corpus-yoga indexing list-candidates reads the queue with the aliases that anchor each; --all disposes it as read):'
          if pending else 'candidates: none - fully disposed', file=sys.stderr)
    for c in pending:
        print(c)
    if unanchorable:
        print(f'unanchorable: {len(unanchorable)} captured concept(s) no conversation turn phrases - not queued: '
              + ', '.join(c for c, _ in unanchorable))


def main():
    # capture is bash machinery (capture.sh, this file's sibling): exec it with the
    # raw argv so its flags need no second parser here; the subparser below exists
    # so the declared surface and the argparse API stay mirrors.
    if len(sys.argv) > 1 and sys.argv[1] == 'capture':
        import os
        script = Path(__file__).resolve().parent / 'capture.sh'
        os.execv('/bin/bash', ['bash', str(script), *sys.argv[2:]])

    ap = command_parser('indexing')  # whole surface declared (#476, #477)
    args = ap.parse_args()

    accepted_path, rejected_path = ACCEPTED_FILE, REJECTED_FILE

    if args.verb == 'list-candidates':
        candidates(MARKDOWN_DIR, accepted_path, rejected_path, args.top)
        return
    if args.verb == 'accept':
        # exactly one of --all and a term: the flag disposes the queue as read, the
        # positional disposes one concept — both or neither is no instruction.
        if args.all == bool(args.term):
            ap.error('accept takes a <term> or --all, not both and not neither')
        if args.all:
            print(dispose_all(accepted_path, rejected_path, 'accept', ''))
        else:
            print(accept(accepted_path, args.term, args.aliases))
        pending_report(accepted_path, rejected_path)
        return
    if args.verb == 'reject':
        if args.all == bool(args.concept):
            ap.error('reject takes a <concept> or --all, not both and not neither')
        if args.all:
            print(dispose_all(accepted_path, rejected_path, 'reject', args.reason))
        else:
            print(reject(accepted_path, rejected_path, args.concept, args.reason))
        pending_report(accepted_path, rejected_path)
        return
    if args.verb == 'sync':
        root = MARKDOWN_DIR
        # A machine with no corpus skips, stated (#406): every data-reading
        # sibling in the corpus tail names its absence; this step must not be
        # the one that presumes its input into existence and tracebacks.
        if not root.is_dir():
            print(f'index: skipped — no corpus at {root.relative_to(REPO)} (corpus-yoga pipeline run projects it)')
            return
        text = build(root, accepted_path)
        out = root / 'index.md'
        out.write_text(text)
        print(f'index: {out.relative_to(REPO) if out.is_relative_to(REPO) else out} — '
              + text.rstrip().rsplit(chr(10), 1)[-1])
        return

    # bare `corpus-yoga indexing`: read-only status of the curation surface, then the
    # capture's own status face (deposits + the paid layer's currency, #409)
    status(accepted_path, rejected_path, MARKDOWN_DIR)
    import subprocess
    subprocess.run(['bash', str(Path(__file__).resolve().parent / 'capture.sh'), '--status'], check=False)


if __name__ == '__main__':
    main()
