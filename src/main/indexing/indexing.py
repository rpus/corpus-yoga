"""
indexing.py - the book-style index over the corpus (headword to turn locators), built from the
capture in use (issues/1189). Driven by `corpus-yoga indexing` (see src/main/cli/).

The capture in use, data/output/indexing/inferred-semantic-concepts.json, proposes the concepts;
the index's headwords are those of them some conversation turn phrases, each with the phrasings
that anchor it, and a concept no turn phrases is named in the status and left out. The build
scans the readable markdown library (data/output/markdown/{claude,gemini}/conversations/) and
writes data/output/indexing/indexed-semantic-concepts.json - each headword with every turn it is
found in, by the turn's durable anchor (message uuid for claude, role-count for gemini), so an
entry survives corpus renumbering. The server's book index (corpus-yoga server build) and the
site's concept table (corpus-yoga site build) are both written from it. The index is derived -
deterministic, no timestamps - so a rebuild is a no-op when nothing changed (CALCULUS L1).

Usage (via corpus-yoga indexing):
  corpus-yoga indexing                                     # status: the capture in use, the index
  corpus-yoga indexing build                               # build data/output/indexing/indexed-semantic-concepts.json
  corpus-yoga indexing adopt <stamp>                       # make a deposited capture the one in use
  corpus-yoga indexing capture [--conversations <path>]    # PAID: the model reads the corpus's titles for
      [--only semantic-concepts|chat-categories]           #   the two index tables (see capture.sh)
"""
import re
import sys
from dataclasses import dataclass
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import facts  # the one printer of a status's facts (issues/753)
import spell
from markdown_projection import turns, REPO
from declared_parser import command_parser

REPO_ROOT = tier.REPO

MARKDOWN_DIR = tier.DATA / 'output' / 'markdown'                    # the corpus to index
INDEXED_FILE = tier.DATA / 'output' / 'indexing' / 'indexed-semantic-concepts.json'  # the index, corpus-yoga indexing build's (written)



def inferred_concepts() -> list[str]:
    """The concepts of the capture in use, the index's one source:
    data/output/indexing/inferred-semantic-concepts.json (a model reading the corpus; refresh with `corpus-yoga indexing capture`).
    Durable and shared across machines (via data/output/), so both curate one shared base — the
    24-vs-27 divergence of the old per-batch, per-machine cache/ inference is gone.
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
    return [('H' if turn.role == 'Human' else 'G' if turn.role == 'Gemini' else 'A', turn.n, turn.anchor, turn.body)
            for turn in turns(md) if turn.anchor]   # the projection's turns, each with its anchor (issues/1001)


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
    every machine that holds the corpus (issues/644)."""
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
    anchored half; the unanchorable half is named, never queued (issues/644)."""
    bodies = turn_bodies(markdown_root) if markdown_root.is_dir() else []
    anchored, unanchorable = [], []
    for c in concepts:
        found = anchors_of(c, bodies)
        if found:
            anchored.append((c, [a for a in found if a.lower() != c.lower()]))
        else:
            unanchorable.append((c, runs_of(c)))
    return anchored, unanchorable


def inputs_digest(markdown_root: Path) -> str:
    """The digest of what the index is built from - the capture in use and every conversation
    the index scans, each by its path and bytes - so that whether the index is current is a
    comparison of content, never of clocks."""
    import hashlib
    digest = hashlib.sha256()
    digest.update(INFERRED_FILE.read_bytes() if INFERRED_FILE.is_file() else b'')
    for source in ('claude', 'gemini'):
        folder = markdown_root / source / 'chat' / 'conversations'
        for f in sorted(folder.glob('*.md')) if folder.is_dir() else []:
            digest.update(f'\0{source}/chat/conversations/{f.name}\0'.encode())
            digest.update(f.read_bytes())
    return 'sha256:' + digest.hexdigest()




def indexed(markdown_root: Path) -> dict:
    """The index as data: each concept of the capture in use that some conversation turn phrases,
    a headword, alphabetised, with the phrasings that anchor it and every turn it is found in,
    `[conversation, role, n, anchor]`, the conversation by its path under data/output/markdown;
    and the concepts no turn phrases, left out. The server's index.md and the site's concept
    table are both built from it, so neither reads the other's output."""
    anchored, unanchorable = anchored_split(inferred_concepts(), markdown_root)
    entries = {concept: [concept] + aliases for concept, aliases in anchored}
    corpus = scan(markdown_root)
    rows = []
    for head in sorted(entries, key=str.lower):
        rx = term_regex(entries[head])
        locators = [[rel, role, n, anchor] for _source, _stem, rel, turns in corpus
                    for role, n, anchor, body in turns if rx.search(body)]
        rows.append([head, [t for t in entries[head] if t != head], locators])
    return {'columns': ['headword', 'aliases', 'locators'], 'rows': rows, 'unanchorable': [c for c, _ in unanchorable],
            'conversations': len(corpus), 'built_from': inputs_digest(markdown_root)}


def summary_of(index: dict) -> str:
    """The index in one line: its headwords found in some turn, and the turn locators they hold."""
    located = [row for row in index['rows'] if row[2]]
    return facts.phrase('{headwords} headword(s); {locators} turn locators across {conversations} conversations.',
                        headwords=len(located), locators=sum(len(row[2]) for row in located), conversations=index['conversations'])


def held_index() -> dict | None:
    """The index as last built, or None where none is."""
    import json
    return json.loads(INDEXED_FILE.read_text()) if INDEXED_FILE.is_file() else None


def index_is_current(markdown_root: Path) -> bool:
    """Whether the index was built from the capture in use and the corpus as they stand."""
    held = held_index()
    return held is not None and held.get('built_from') == inputs_digest(markdown_root)


def conversation_count() -> int:
    """How many conversations the corpus holds, counted by its shape's one home,
    src/main/corpus_shape.sh; none where no corpus is projected."""
    import subprocess
    corpus = tier.DATA / 'output' / 'markdown'
    if not corpus.is_dir():
        return 0
    shape = REPO_ROOT / 'src' / 'main' / 'corpus_shape.sh'
    counted = subprocess.run(['bash', '-c', 'source "$1"; count_conversations "$2"', 'count', str(shape), str(corpus)],
                             capture_output=True, text=True).stdout.strip()
    return int(counted or 0)


def capture_lag() -> int:
    """How many conversations the capture in use does not cover - every one where no concept
    capture is in use."""
    import json
    categories = tier.DATA / 'output' / 'indexing' / 'inferred-chat-categories.json'
    covered = len(json.loads(categories.read_text()).get('rows', [])) if categories.is_file() and inferred_concepts() else 0
    return max(conversation_count() - covered, 0)


def waits_on(markdown_root: Path) -> str | None:
    """What the index waits on, or None where it is built from the capture in use and the corpus
    as they stand. The server's and the site's builds are offered only where this is None."""
    if not index_is_current(markdown_root):
        return facts.phrase('waits on corpus-yoga indexing build')
    return None


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


INFERRED_FILE = tier.DATA / 'output' / 'indexing' / 'inferred-semantic-concepts.json'  # the capture in use: the model's proposals (read)
CATEGORIES_FILE = tier.DATA / 'output' / 'indexing' / 'inferred-chat-categories.json'  # the capture in use: each conversation's category
CAPTURES_DIR = tier.DATA / 'output' / 'indexing' / 'capture'   # every paid capture, deposited under its stamp (issues/1185)


def deposit(staged: Path, stamp: str, names: list[str] | None = None) -> Path:
    """A paid capture's tables, moved from where the capture validated them into their own
    deposit, data/output/indexing/capture/<stamp>/, beside every earlier one - the capture in
    use left as it stands (issues/1185). `names` are the tables this capture took."""
    import shutil
    dest = CAPTURES_DIR / stamp
    dest.mkdir(parents=True, exist_ok=False)
    for name in names or [INFERRED_FILE.name, CATEGORIES_FILE.name]:
        if (staged / name).is_file():
            shutil.move(staged / name, dest / name)
    return dest


def deposits() -> list[str]:
    """Every deposited capture by its stamp, oldest first."""
    return sorted(d.name for d in CAPTURES_DIR.iterdir() if d.is_dir()) if CAPTURES_DIR.is_dir() else []


def in_use() -> str | None:
    """The stamp of the deposit the capture in use is - every table it holds the same bytes as the
    one in use - newest first; None where no deposit is (a capture from before deposits, or none)."""
    for stamp in reversed(deposits()):
        tables = [t for t in (CAPTURES_DIR / stamp).iterdir() if t.is_file()]
        held = {INFERRED_FILE.name: INFERRED_FILE, CATEGORIES_FILE.name: CATEGORIES_FILE}
        if tables and all(t.name in held and held[t.name].is_file() and held[t.name].read_bytes() == t.read_bytes() for t in tables):
            return stamp
    return None


def adopt(stamp: str) -> list[str]:
    """The deposit made the capture in use: each table it holds copied over the one in use."""
    import shutil
    took = []
    for table in sorted((CAPTURES_DIR / stamp).iterdir()):
        target = {INFERRED_FILE.name: INFERRED_FILE, CATEGORIES_FILE.name: CATEGORIES_FILE}.get(table.name)
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(table, target)
            took.append(table.name)
    return took


def _rows(path: Path) -> list:
    import json
    return json.loads(path.read_text()).get('rows', []) if path.is_file() else []


def changes(stamp: str) -> dict[str, int]:
    """What adopting the deposit would change against the capture in use: the concepts it adds and
    drops, and the conversations whose category it moves or gives for the first time."""
    dest = CAPTURES_DIR / stamp
    out: dict[str, int] = {}
    if (dest / INFERRED_FILE.name).is_file():
        new, old = {r[0] for r in _rows(dest / INFERRED_FILE.name)}, {r[0] for r in _rows(INFERRED_FILE)}
        out['concepts added'], out['concepts dropped'] = len(new - old), len(old - new)
    if (dest / CATEGORIES_FILE.name).is_file():
        new, old = {r[0]: r[1] for r in _rows(dest / CATEGORIES_FILE.name)}, {r[0]: r[1] for r in _rows(CATEGORIES_FILE)}
        out['categories moved'] = sum(1 for c, k in new.items() if c in old and old[c] != k)
        out['conversations newly categorised'] = sum(1 for c in new if c not in old)
    return out


def anchor_report(concepts_file: Path, markdown_root: Path) -> None:
    """What the paid call bought (issues/644): of the captured concepts, which the corpus can
    index - the headwords this capture gives once adopted - and which it cannot, by the runs tried."""
    import json
    concepts = [r[0] for r in json.loads(Path(concepts_file).read_text()).get('rows', [])]
    anchored, unanchorable = anchored_split(concepts, markdown_root)
    print('  anchors: ' + facts.phrase('{captured} concept(s) captured, {anchored} anchor in a conversation turn and are headwords once adopted',
                                       captured=len(concepts), anchored=len(anchored))
          + (', ' + facts.phrase('{n} do not and will not be', n=len(unanchorable)) if unanchorable else ''))
    for c, tried in unanchorable:
        print(f'    {c}  (' + facts.phrase('tried, in either number, {tried}', tried=', '.join(tried)) + ')')


@dataclass
class Unanchorable:
    concepts: list[str] = facts.named('captured concepts no conversation turn phrases, left out of the index')


@dataclass
class Index:
    """The index, data/output/indexing/indexed-semantic-concepts.json, against the capture in
    use and the corpus as they stand."""
    standing: str
    act: facts.Would | None = None


@dataclass
class Indexing:
    """The index: what the capture in use proposes that no conversation turn phrases, and the
    index against the capture and the corpus as they stand."""
    unanchorable: Unanchorable | None = None
    index: Index | str | None = None


def status(markdown_root: Path) -> Indexing:
    """Read-only state of the index (bare `corpus-yoga indexing`) as facts (issues/753,
    issues/759): the build offered wherever the index is not built from the capture in use and
    the corpus as they stand (issues/1189)."""
    out = Indexing()
    if not inferred_concepts():
        out.index = facts.phrase('none - no capture in use')
        return out
    if not markdown_root.is_dir():
        return out
    if index_is_current(markdown_root):
        # what the build left out, as it found it: the status searches no turn itself
        held = held_index() or {}
        if held.get('unanchorable'):
            out.unanchorable = Unanchorable(held['unanchorable'])
        out.index = Index(facts.phrase('current - built from the capture in use and the corpus as they stand'))
    else:
        out.index = Index(facts.phrase('stale - the capture in use or the corpus moved since it was built'),
                          facts.Would(spell.line('indexing', 'build'), {INDEXED_FILE.relative_to(REPO).as_posix() if INDEXED_FILE.is_relative_to(REPO) else str(INDEXED_FILE): 1}))
    return out


@dataclass
class Currency:
    """The capture in use against the corpus it reads."""
    conversations: int
    covered_by_the_capture_in_use: int
    act: facts.Would | None = None


@dataclass
class Pending:
    """The deposited captures not adopted, by stamp, with what adopting each would change, and
    the act that adopts the newest."""
    captures: dict[str, dict[str, int]]
    act: facts.Would | None = None


@dataclass
class Captures:
    """The paid captures: the one in use - the concepts the index's headwords are drawn from,
    the categories the site build colours by - and every other one deposited (issues/1185)."""
    in_use: str
    tables: dict[str, str]
    corpus: Currency | None = None
    deposited: Pending | str | None = None


@dataclass
class Status:
    indexing: Indexing
    captures: Captures = facts.named('data/output/indexing')


def captures() -> Captures:
    """The paid captures' standing: the capture in use, by its stamp where a deposit holds it, what
    it covers of the corpus, and each capture deposited and not adopted with what adopting it would
    change. The corpus is counted by its shape's one home, src/main/corpus_shape.sh."""
    rows: dict[str, int | None] = {t.name: (len(_rows(t)) if t.is_file() else None) for t in (INFERRED_FILE, CATEGORIES_FILE)}
    stamp = in_use()
    out = Captures(stamp or (facts.phrase('none - no capture taken') if all(n is None for n in rows.values())
                             else facts.phrase('a capture from before deposits')),
                   {name: facts.phrase('not captured yet') if n is None else facts.phrase('{n} rows', n=n) for name, n in rows.items()})
    if (tier.DATA / 'output' / 'markdown').is_dir():
        n = conversation_count()
        if n > 0:
            # always offered, paid (issues/1185): a capture is a fresh, non-deterministic reading of
            # every title, and replaces nothing until it is adopted
            out.corpus = Currency(n, rows[CATEGORIES_FILE.name] or 0, facts.Would(spell.line('indexing', 'capture'), {'data/output/markdown': n}))
    pending = [d for d in deposits() if d != stamp]
    out.deposited = (Pending({d: changes(d) for d in pending}, facts.Would(spell.line('indexing', 'adopt', pending[-1]), {pending[-1]: 1}))
                     if pending else facts.phrase('none but the capture in use'))
    return out


def main():
    # capture is bash machinery (capture.sh, this file's sibling): exec it with the
    # raw argv so its flags need no second parser here; the subparser below exists
    # so the declared surface and the argparse API stay mirrors.
    if len(sys.argv) > 1 and sys.argv[1] == 'capture':
        import os
        script = Path(__file__).resolve().parent / 'capture.sh'
        os.execv('/bin/bash', ['bash', str(script), *sys.argv[2:]])

    ap = command_parser('indexing')  # whole surface declared (issues/476, issues/477)
    args = ap.parse_args()

    if args.verb == 'adopt':
        if args.stamp not in deposits():
            ap.error(facts.phrase('no capture deposited at {stamp} - corpus-yoga indexing names them', stamp=args.stamp))
        changed = changes(args.stamp)
        took = adopt(args.stamp)
        facts.report(None, facts.act('indexing', 'adopt') + ': DONE - ' + facts.phrase('{stamp} is the capture in use - {tables}; {changed}', stamp=args.stamp,
                     tables=', '.join(took), changed=', '.join(f'{k} {v}' for k, v in changed.items()) or facts.phrase('nothing changed')))
        return
    if args.verb == 'build':
        import json
        root = MARKDOWN_DIR
        # A machine with no corpus skips, stated (issues/406): this step must not be the one
        # that presumes its input into existence and tracebacks.
        if not root.is_dir():
            facts.report(None, facts.act('indexing', 'build') + ': DONE - ' + facts.phrase('skipped; no corpus at {root}, which corpus-yoga pipeline collate projects', root=root.relative_to(REPO)))
            return
        out = INDEXED_FILE.relative_to(REPO) if INDEXED_FILE.is_relative_to(REPO) else INDEXED_FILE
        if index_is_current(root):
            facts.report(None, facts.act('indexing', 'build') + ': DONE - ' + facts.phrase('no effect; {path} is built from the capture in use and the corpus as they stand', path=out))
            return
        index = indexed(root)
        INDEXED_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEXED_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=1) + '\n')
        facts.report(None, facts.act('indexing', 'build') + ': DONE - ' + facts.phrase('{path} written; {summary}', path=out, summary=summary_of(index)))
        return

    # bare `corpus-yoga indexing`: read-only status of the index, then the paid captures'
    # standing (the capture in use, the deposits, the corpus they read)
    facts.say_standing(Status(status(MARKDOWN_DIR), captures()))


if __name__ == '__main__':
    main()
