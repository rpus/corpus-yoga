"""common.py — shared vocabulary of the restructure toolset (see README.md)."""
import csv
from pathlib import Path

# output/markdown: old prefix → new prefix (longest-first; applied to paths and,
# in the comparer, to embedded corpus links)
MARKDOWN_MAP = [
    ('claude/conversations/', 'claude/chat/conversations/'),
    ('claude/memories/',      'claude/chat/memories/'),
    ('claude/summaries/',     'claude/chat/summaries/'),
    ('code/conversations/',   'claude/code/conversations/'),
    ('gemini/conversations/', 'gemini/chat/conversations/'),
]


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
