"""
pretty_md_tables.py

Finds all markdown tables in each input file, aligns columns in-place,
and rewrites the file. Safe to re-run; idempotent.

Usage:
    python3 pretty_md_tables.py [--dry-run] FILE [FILE ...]
    find . -name "*.md" | xargs python3 pretty_md_tables.py [--dry-run]

Options:
    --dry-run   Report what would change without writing anything.
"""

import re
import sys
from pathlib import Path


# ── table parsing ─────────────────────────────────────────────────────────────

def parse_row(line: str) -> list[str]:
    """Split a pipe-delimited markdown row into stripped cell strings."""
    cells = line.strip().split('|')
    if cells and cells[0].strip() == '':
        cells = cells[1:]
    if cells and cells[-1].strip() == '':
        cells = cells[:-1]
    return [c.strip() for c in cells]

def is_separator_cell(cell: str) -> bool:
    """True if cell is a header/body separator (e.g. ---, :---, :---:)."""
    return bool(re.fullmatch(r':?-+:?', cell.strip()))

def is_table_row(line: str) -> bool:
    return '|' in line


# ── table formatting ──────────────────────────────────────────────────────────

def format_table(rows: list[str]) -> list[str]:
    """
    Given raw table lines, return pretty-printed lines.
    Preserves separator rows; aligns all columns to max width.
    """
    parsed  = [parse_row(r) for r in rows]
    n_cols  = max(len(r) for r in parsed)
    parsed  = [r + [''] * (n_cols - len(r)) for r in parsed]

    col_widths = [3] * n_cols
    for row in parsed:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    output = []
    for row in parsed:
        is_sep = all(is_separator_cell(c) or c == '' for c in row)
        if is_sep:
            cells = ['-' * col_widths[i] for i in range(n_cols)]
        else:
            cells = [row[i].ljust(col_widths[i]) for i in range(n_cols)]
        output.append('| ' + ' | '.join(cells) + ' |')

    return output


# ── file processing ───────────────────────────────────────────────────────────

def process(text: str) -> str:
    """Find all markdown tables in text and replace with aligned versions."""
    lines  = text.splitlines()
    output = []
    i      = 0

    while i < len(lines):
        if is_table_row(lines[i]):
            table_lines = []
            while i < len(lines) and is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            output.extend(format_table(table_lines))
        else:
            output.append(lines[i])
            i += 1

    result = '\n'.join(output)
    if text.endswith('\n'):
        result += '\n'
    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args     = sys.argv[1:]
    dry_run  = '--dry-run' in args
    paths    = [a for a in args if not a.startswith('--')]

    if not paths:
        sys.exit('Usage: python3 pretty_md_tables.py [--dry-run] FILE [FILE ...]')

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            print(f'SKIP:            {path}')
            continue
        original = path.read_text()
        prettied = process(original)
        if prettied == original:
            print(f'OK (unchanged):  {path}')
        elif dry_run:
            print(f'WOULD UPDATE:    {path}')
        else:
            path.write_text(prettied)
            print(f'OK (updated):    {path}')


if __name__ == '__main__':
    main()
