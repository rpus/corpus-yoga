"""common.py — shared vocabulary of the restructure toolset (see README.md).

Second service: the four-root taxonomy. Unlike the first migration, the corpus
CONTENT does not move — only the roots above it do — so the markdown map is
IDENTITY and the comparer's bar is byte-identical, full stop.
"""
import csv
from pathlib import Path

# The root relocations (longest-first where prefixes could nest — the mount row
# must be considered before its old parent claims it). Every path in the old
# layout maps under exactly one rule; gen_moves' totality check enforces it.
ROOT_MAP = [
    ('input/claude-code-projects', 'ext/claude-code-projects'),  # the mount: a live SOURCE, not a capture
    ('input/',  'data/input/'),
    ('output/', 'data/output/'),
    ('cache/',  'tmp/cache/'),
    ('logs/',   'tmp/logs/'),
]

# Machinery leaving the root: yoga fronts both, so the root keeps only the
# launcher, the README, and the four taxonomy dirs.
SCRIPT_MOVES = [
    ('RUNME.sh',         'src/RUNME.sh'),
    ('PREREQUISITES.sh', 'src/PREREQUISITES.sh'),
]

# The code-side sweep: OLD-layout literal → NEW-layout literal, as regexes
# (lookarounds keep new forms from rematching, so the sweep CONVERGES:
# data/input/ contains input/ but is not preceded by a bare boundary).
# gen_refs.py reports these sites; apply_refs.py performs exactly these swaps.
# NB the lookbehinds exclude ONLY word-tails and the new prefixes — a bare
# '/' before the tier word must still match ($SCRIPT_DIR/input/... is a hit).
REF_MAP = [
    ('mount', r'input/claude-code-projects', 'ext/claude-code-projects'),
    ('input-root', r'(?<![\w-])(?<!data/)input/(?!claude-code-projects)', 'data/input/'),
    ('output-root', r'(?<![\w-])(?<!data/)output/', 'data/output/'),
    ('cache-root', r'(?<![\w-])(?<!tmp/)cache/', 'tmp/cache/'),
    ('logs-root', r'(?<![\w-])(?<!tmp/)logs/', 'tmp/logs/'),
]

# Files the sweep never touches: derived artifacts, this machinery itself
# (its old-form mentions are its subject), immutable format histories (a
# quoted "input" there is a message-content key, not a path), and .gitignore
# (its anchor block is rewritten whole, by hand, with its own commentary).
SWEEP_SKIP_PREFIXES = ('src/restructure/', 'rsc/schema/')
SWEEP_SKIP_FILES = {'src/test/xref.csv', 'src/test/pre_commit.log', '.gitignore'}

# output/markdown: old prefix → new prefix. IDENTITY this service — the corpus
# must not notice the move (first service changed content paths; this one only
# lifts the roots). Kept as a constant so compare_outputs keeps one shape.
MARKDOWN_MAP: list[tuple[str, str]] = []


def read_moves(moves_csv):
    """[(old, new, rule)] — skips the header; every row, including excluded/dispose."""
    with open(moves_csv, newline='') as fh:
        rows = list(csv.reader(fh))
    assert rows and rows[0] == ['old', 'new', 'rule'], f'not a moves manifest: {moves_csv}'
    return [(o, n, r) for o, n, r in rows[1:]]


def write_moves(moves_csv, rows):
    Path(moves_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(moves_csv, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['old', 'new', 'rule'])
        w.writerows(rows)
