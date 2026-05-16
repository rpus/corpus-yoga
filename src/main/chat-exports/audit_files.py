#!/usr/bin/env python
"""
audit_files.py — Full-outer-join file audit for one export.

Writes a CSV to gen/chat-exports/<export>/audit_queries/files_audit.csv with one row per
(source, file-path) covering every file known about for the export across five
sources:

    source   description
    ───────  ─────────────────────────────────────────────────────────────────
    tooltip  Paths from data-files.json, which is derived from
             rsc/artifacts/downloaded/ by files_from_downloaded.py.
             This is what the index.html tooltip shows.
    ef       Files written to gen/<export>/extracted_files/ by src/main/chat-exports/extract_files.py
             (from create_file tool calls).
    eh_out   Files written to gen/<export>/extracted_heredocs/<chat>/outputs/
             by src/main/chat-exports/extract_heredocs.py (heredoc target was /mnt/user-data/outputs/).
    eh_wrk   Files written to gen/<export>/extracted_heredocs/<chat>/working/
             by src/main/chat-exports/extract_heredocs.py (heredoc target was /home/claude/).
    dl       Files in rsc/artifacts/downloaded/<chat>/ (manually downloaded
             from the claude.ai UI).

Columns
───────
    chat          Integer chat index (0-based, sorted by conversation created_at).
    chat_name     Human-readable conversation name.
    source        One of: tooltip, ef, eh_out, eh_wrk, dl.
    path          Path as it appears in this source (relative to the chat/bucket
                  root; no container prefix).
    in_dl         For ef/eh_out/eh_wrk rows: Y if a counterpart exists in
                  rsc/artifacts/downloaded at the expected path; N otherwise.
                  Empty for tooltip and dl rows.
    dl_compare    For ef/eh_out/eh_wrk rows: comparison result against the
                  downloaded counterpart —
                    identical     byte-for-byte match
                    newline_only  differ only by a trailing newline
                    differs       downloaded is substantively ahead
                    not_present   no counterpart in downloaded
                  Empty for tooltip and dl rows.
    in_rsc        For ef/eh_out/eh_wrk rows: Y if this file was copied to
                  rsc/artifacts/extracted_files/ or rsc/artifacts/extracted_heredocs/
                  (i.e. it had no downloaded counterpart and was preserved there);
                  N if it was not copied (counterpart existed in downloaded).
                  Empty for tooltip and dl rows.

Downloaded path conventions
────────────────────────────
    ef      rsc/artifacts/downloaded/<chat_slug>/<path>          (no bucket)
    eh_out  rsc/artifacts/downloaded/<chat_slug>/<path>          (no bucket)
    eh_wrk  rsc/artifacts/downloaded/<chat_slug>/working/<path>  (bucket preserved)

Usage
─────
    src/main/chat-exports/audit_files.sh --chat-export  <path-to-export>
    src/main/chat-exports/audit_files.sh --chat-exports <path-to-exports>

    Example:
        src/main/chat-exports/audit_files.sh --chat-export \\
            ext/chat-exports/data-0fc4c1e0-...-batch-0000

SQL queries
───────────
The CSV can be loaded into any SQL engine (e.g. sqlite3, DuckDB) or pandas.
The standard queries (reproducing both extract logs, tooltip lists, and mismatch
reports) are defined in src/main/chat-exports/query_files.py and can be run with:

    python src/main/chat-exports/query_files.py <export-name>
"""

import argparse
import csv
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[2]
GEN_DIR    = REPO_ROOT / 'gen' / 'chat-exports'
DL_ROOT    = REPO_ROOT / 'rsc' / 'artifacts' / 'downloaded'
RSC_EF     = REPO_ROOT / 'rsc' / 'artifacts' / 'extracted_files'
RSC_EH     = REPO_ROOT / 'rsc' / 'artifacts' / 'extracted_heredocs'


def slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '_', s)
    return s[:60].strip('_') or 'untitled'


def compare(src_path, dl_path):
    """Return dl_compare value for an extraction source file vs its downloaded counterpart."""
    if not dl_path.exists():
        return 'not_present'
    a = src_path.read_text()
    b = dl_path.read_text()
    if a == b:
        return 'identical'
    if a + '\n' == b or a == b + '\n':
        return 'newline_only'
    return 'differs'


def run_one(name: str) -> None:
    exp_dir    = GEN_DIR / name
    pres       = exp_dir / 'presentation'
    ef_root    = exp_dir / 'extracted_files'
    eh_root    = exp_dir / 'extracted_heredocs'
    out_dir    = exp_dir / 'audit_queries'
    out_dir.mkdir(exist_ok=True)
    out_path   = out_dir / 'files_audit.csv'
    log        = (out_dir / 'audit_files.log').open('w')

    files_j = json.loads((pres / 'data-files.json').read_text())
    chats_j = json.loads((pres / 'data-chats.json').read_text())
    fc = {c: i for i, c in enumerate(files_j['columns'])}
    cc = {c: i for i, c in enumerate(chats_j['columns'])}
    chat_names = {r[cc['chat']]: r[cc['name']] for r in chats_j['rows']}

    from collections import defaultdict
    tooltip_by_chat = defaultdict(set)
    for r in files_j['rows']:
        tooltip_by_chat[r[fc['chat']]].add(r[fc['file']])

    rows: list[list[int | str]] = []

    for chat_idx, cname in sorted(chat_names.items()):
        cs = f'{chat_idx:03d}_{slug(cname)}'

        # ── tooltip ───────────────────────────────────────────────────────────
        # Paths from local_resource tool results; this is what the tooltip shows.
        for p in sorted(tooltip_by_chat[chat_idx]):
            rows.append([chat_idx, cname, 'tooltip', p, '', '', ''])

        # ── extracted_files ───────────────────────────────────────────────────
        # Written by src/main/chat-exports/extract_files.py from create_file tool calls.
        # Downloaded counterpart is at dl/<chat_slug>/<path> (no bucket prefix).
        ef_dir = ef_root / cs
        if ef_dir.exists():
            for f in sorted(ef_dir.rglob('*')):
                if not f.is_file():
                    continue
                rel    = f.relative_to(ef_dir)
                dl_p   = DL_ROOT / cs / rel
                cmp    = compare(f, dl_p)
                in_rsc = 'Y' if (RSC_EF / cs / rel).exists() else 'N'
                rows.append([chat_idx, cname, 'ef', str(rel),
                             'Y' if dl_p.exists() else 'N', cmp, in_rsc])

        # ── extracted_heredocs / outputs ──────────────────────────────────────
        # Written by src/main/chat-exports/extract_heredocs.py; heredoc target was /mnt/user-data/outputs/.
        # Downloaded counterpart is at dl/<chat_slug>/<path> (no bucket prefix).
        eh_out = eh_root / cs / 'outputs'
        if eh_out.exists():
            for f in sorted(eh_out.rglob('*')):
                if not f.is_file():
                    continue
                rel    = f.relative_to(eh_out)
                dl_p   = DL_ROOT / cs / rel
                cmp    = compare(f, dl_p)
                in_rsc = 'Y' if (RSC_EH / cs / 'outputs' / rel).exists() else 'N'
                rows.append([chat_idx, cname, 'eh_out', str(rel),
                             'Y' if dl_p.exists() else 'N', cmp, in_rsc])

        # ── extracted_heredocs / working ──────────────────────────────────────
        # Written by src/main/chat-exports/extract_heredocs.py; heredoc target was /home/claude/.
        # Downloaded counterpart is at dl/<chat_slug>/working/<path>
        # (the working/ bucket prefix is preserved in the downloaded tree).
        eh_wrk = eh_root / cs / 'working'
        if eh_wrk.exists():
            for f in sorted(eh_wrk.rglob('*')):
                if not f.is_file():
                    continue
                rel    = f.relative_to(eh_wrk)
                dl_p   = DL_ROOT / cs / 'working' / rel
                cmp    = compare(f, dl_p)
                in_rsc = 'Y' if (RSC_EH / cs / 'working' / rel).exists() else 'N'
                rows.append([chat_idx, cname, 'eh_wrk', str(rel),
                             'Y' if dl_p.exists() else 'N', cmp, in_rsc])

        # ── downloaded ────────────────────────────────────────────────────────
        # Everything in rsc/artifacts/downloaded/<chat_slug>/.
        dl_dir = DL_ROOT / cs
        if dl_dir.exists():
            for f in sorted(dl_dir.rglob('*')):
                if f.is_file() and f.name != '.DS_Store':
                    rows.append([chat_idx, cname, 'dl',
                                 str(f.relative_to(dl_dir)), '', '', ''])

    # ── Write normalised table ────────────────────────────────────────────────
    with out_path.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['chat', 'chat_name', 'source', 'path',
                    'in_dl', 'dl_compare', 'in_rsc'])
        w.writerows(rows)
    log.write(f'{len(rows)} rows → {out_path.relative_to(REPO_ROOT)}\n')

    # ── Write joined table ────────────────────────────────────────────────────
    # One row per (chat, filename) with the actual path as it appears in each
    # source. Multiple paths for the same filename in one source are joined with
    # ' | '. This makes path mismatches directly visible across columns.
    SOURCES = ('tooltip', 'ef', 'eh_out', 'eh_wrk', 'dl')
    # keyed by (chat_idx, chat_name, bare_filename) → {source: [path, ...]}
    by_name: dict[tuple[int, str, str], dict[str, list[str]]] = {}
    for row in rows:
        chat_i   = int(row[0])
        cname_s  = str(row[1])
        source_s = str(row[2])
        path_s   = str(row[3])
        key = (chat_i, cname_s, Path(path_s).name)
        if key not in by_name:
            by_name[key] = {s: [] for s in SOURCES}
        by_name[key][source_s].append(path_s)

    joined_path = out_dir / 'files_audit_joined.csv'
    with joined_path.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['chat', 'chat_name', 'filename',
                    'tip_path', 'ef_path', 'eh_out_path', 'eh_wrk_path', 'dl_path'])
        for (chat_i, cname_s, fname), paths in sorted(by_name.items()):
            w.writerow([
                chat_i, cname_s, fname,
                ' | '.join(sorted(paths['tooltip'])),
                ' | '.join(sorted(paths['ef'])),
                ' | '.join(sorted(paths['eh_out'])),
                ' | '.join(sorted(paths['eh_wrk'])),
                ' | '.join(sorted(paths['dl'])),
            ])
    log.write(f'{len(by_name)} rows → {joined_path.relative_to(REPO_ROOT)}\n')
    log.close()


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
