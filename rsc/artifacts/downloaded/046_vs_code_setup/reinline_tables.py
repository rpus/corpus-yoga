"""
reinline_tables.py

For each table ID in TABLE_IDS:
  1. Resolve json_path from data_dir (load_settings / CLI args)
  2. Read and parse the JSON file (json.loads)
  3. Pretty-print it (pretty_table)
  4. Write the pretty-printed JSON back to json_path (in-place)
  5. Splice it between the sentinel comments in the dashboard file (splice)

Reads settings.json from the repo root for default paths.
CLI args override settings.json.

Usage:
    python3 reinline_tables.py [--dashboard-file PATH] [--data-dir PATH] [--settings PATH]
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── tables to manage ─────────────────────────────────────────────────────────

TABLE_IDS = [
    'data-chats',
    'data-spans',
    'data-categories',
    'data-chat-categories',
    'data-files',
]


# ── settings ──────────────────────────────────────────────────────────────────

def load_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        return json.loads(settings_path.read_text())
    return {}


# ── pretty-printer ────────────────────────────────────────────────────────────

def pretty_table(data: dict) -> str:
    cols = data['columns']
    rows = data['rows']

    def cell_str(v):
        return json.dumps(v, ensure_ascii=False)

    col_widths = [len(json.dumps(c)) for c in cols]
    for row in rows:
        for i, v in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell_str(v)))

    padded_headers = [json.dumps(c).ljust(col_widths[i]) for i, c in enumerate(cols)]
    columns_line   = '  [' + ', '.join(padded_headers) + ']'

    padded_rows = []
    for row in rows:
        cells = []
        for i, v in enumerate(row):
            s = cell_str(v)
            cells.append(s.rjust(col_widths[i]) if isinstance(v, (int, float)) else s.ljust(col_widths[i]))
        padded_rows.append('  [' + ', '.join(cells) + ']')

    return (
        '{"columns":\n' +
        columns_line + ',\n' +
        '"rows":[\n' +
        ',\n'.join(padded_rows) + '\n' +
        ']}'
    )


# ── splice into dashboard HTML ────────────────────────────────────────────────

def splice(html: str, tid: str, pretty: str) -> str:
    filename  = f'{tid}.json'
    begin_tag = f'<!-- {filename}:begin -->'
    end_tag   = f'<!-- {filename}:end -->'
    pattern   = re.compile(
        re.escape(begin_tag) + r'.*?' + re.escape(end_tag),
        re.DOTALL
    )
    if not pattern.search(html):
        raise ValueError(f'Sentinel pair not found for {filename}')
    return pattern.sub(
        f'{begin_tag}\n'
        f'  <script id="{tid}" type="application/json">\n'
        f'{pretty}\n'
        f'  </script>\n'
        f'  {end_tag}',
        html
    )


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dashboard-file', default=None)
    parser.add_argument('--data-dir',       default=None)
    parser.add_argument('--settings',       default='settings.json')
    args = parser.parse_args()

    settings = load_settings(Path(args.settings))                          # (1)

    dashboard_file = Path(args.dashboard_file or settings.get('dashboard_file', './index.html'))
    data_dir       = Path(args.data_dir       or settings.get('data_dir',       './gen/data/'))

    if not dashboard_file.exists():
        sys.exit(f'Dashboard file not found: {dashboard_file}')
    if not data_dir.exists():
        sys.exit(f'Data directory not found: {data_dir}')

    html = dashboard_file.read_text()

    for tid in TABLE_IDS:
        json_path = data_dir / f'{tid}.json'                               # (1)

        if not json_path.exists():
            print(f'SKIP: {json_path} not found')
            continue

        data   = json.loads(json_path.read_text())                         # (2)
        pretty = pretty_table(data)                                        # (3)
        json_path.write_text(pretty + '\n')                                # (4)
        html   = splice(html, tid, pretty)                                 # (5)
        print(f'OK:   {json_path}')

    dashboard_file.write_text(html)
    print(f'\nUpdated: {dashboard_file}')


if __name__ == '__main__':
    main()
