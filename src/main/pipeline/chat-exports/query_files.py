#!/usr/bin/env python
"""
query_files.py — Run the standard SQL queries against files_audit.csv.

Loads tmp/cache/<export>/presentation/files_audit.csv into an in-memory SQLite
database and runs each of the five documented queries, writing results to
tmp/cache/<export>/audit_queries/.

Usage:
    python src/main/pipeline/chat-exports/query_files.py --chat-export  <path-to-export>
    python src/main/pipeline/chat-exports/query_files.py --chat-exports <path-to-exports>

Output files
────────────
    q1_extract_files.csv      Reproduces the extract_files.log per-chat summary.
    q2_extract_heredocs.csv   Reproduces the extract_heredocs.log per-chat summary.
    q3_tooltip_paths.csv      All tooltip paths, one per row, with chat info.
    q4_tooltip_only.csv       Tooltip paths absent from all disk sources at the
                              same path (path mismatches or genuinely lost files).
    q5_disk_only.csv          Disk paths absent from the tooltip at the same path
                              (files never returned as local_resource results).

The SQL for each query is defined in the QUERIES list below.
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[3]
CACHE_DIR    = REPO_ROOT / 'tmp' / 'cache' / 'chat-exports'

QUERIES: list[tuple[str, str, str]] = [
    (
        'q1_extract_files',
        'Reproduces extract_files.log per-chat summary',
        '''
        SELECT chat, chat_name,
            COUNT(*)                                    AS extracted,
            SUM(CASE WHEN in_dl='Y' THEN 1 ELSE 0 END) AS downloaded,
            SUM(CASE WHEN in_dl='N' THEN 1 ELSE 0 END) AS copied
        FROM files_audit
        WHERE source = 'ef'
        GROUP BY chat, chat_name
        ORDER BY chat
        ''',
    ),
    (
        'q2_extract_heredocs',
        'Reproduces extract_heredocs.log per-chat summary',
        '''
        SELECT chat, chat_name,
            COUNT(*)                                                    AS extracted,
            SUM(CASE WHEN dl_compare='identical'    THEN 1 ELSE 0 END) AS identical,
            SUM(CASE WHEN dl_compare='newline_only' THEN 1 ELSE 0 END) AS newline_only,
            SUM(CASE WHEN dl_compare='differs'      THEN 1 ELSE 0 END) AS differs,
            SUM(CASE WHEN dl_compare='not_present'  THEN 1 ELSE 0 END) AS copied
        FROM files_audit
        WHERE source IN ('eh_out', 'eh_wrk')
        GROUP BY chat, chat_name
        ORDER BY chat
        ''',
    ),
    (
        'q3_tooltip_paths',
        'All tooltip paths',
        '''
        SELECT chat, chat_name, path
        FROM files_audit
        WHERE source = 'tooltip'
        ORDER BY chat, path
        ''',
    ),
    (
        'q4_tooltip_only',
        'Tooltip paths absent from all disk sources at the same path',
        '''
        SELECT t.chat, t.chat_name, t.path AS tooltip_path
        FROM files_audit t
        WHERE t.source = 'tooltip'
          AND NOT EXISTS (
              SELECT 1 FROM files_audit d
              WHERE d.chat = t.chat
                AND d.source IN ('ef','eh_out','eh_wrk','dl')
                AND d.path = t.path
          )
        ORDER BY t.chat, t.path
        ''',
    ),
    (
        'q5_disk_only',
        'Disk paths absent from the tooltip at the same path',
        '''
        SELECT d.chat, d.chat_name, d.source, d.path
        FROM files_audit d
        WHERE d.source IN ('ef','eh_out','eh_wrk','dl')
          AND NOT EXISTS (
              SELECT 1 FROM files_audit t
              WHERE t.chat = d.chat
                AND t.source = 'tooltip'
                AND t.path = d.path
          )
        ORDER BY d.chat, d.source, d.path
        ''',
    ),
]


def run_one(name: str) -> None:
    csv_path = CACHE_DIR / name / 'audit_queries' / 'files_audit.csv'
    out_dir  = CACHE_DIR / name / 'audit_queries'
    out_dir.mkdir(exist_ok=True)

    if not csv_path.exists():
        sys.exit(f'Not found: {csv_path}\nRun audit_files.py first.')

    log = (out_dir / 'audit_files.log').open('a')

    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.execute('''
        CREATE TABLE files_audit (
            chat       INTEGER,
            chat_name  TEXT,
            source     TEXT,
            path       TEXT,
            in_dl      TEXT,
            dl_compare TEXT
        )
    ''')
    with csv_path.open() as fh:
        con.executemany(
            'INSERT INTO files_audit VALUES '
            '(:chat,:chat_name,:source,:path,:in_dl,:dl_compare)',
            csv.DictReader(fh),
        )
    con.commit()

    for stem, description, sql in QUERIES:
        rows = con.execute(sql).fetchall()
        out  = out_dir / f'{stem}.csv'
        with out.open('w', newline='') as fh:
            w = csv.writer(fh)
            if rows:
                w.writerow(rows[0].keys())
                w.writerows(rows)
        log.write(f'{len(rows):4d} rows  {stem}.csv  ({description})\n')

    con.close()
    log.close()
    print(f'  ✓ {name} → {out_dir.relative_to(CACHE_DIR.parent)}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--chat-export',  help='Path to a single export directory')
    group.add_argument('--chat-exports', help='Path to a directory containing multiple exports')
    args = parser.parse_args()

    if args.chat_export:
        run_one(Path(args.chat_export).resolve().name)
    else:
        for d in sorted(Path(args.chat_exports).glob('data-*/')):
            run_one(d.name)


if __name__ == '__main__':
    main()
