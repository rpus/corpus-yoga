#!/usr/bin/env python
"""
reference.py - the upstream reference artefacts under rsc/reference (#572, #587):
one project per upstream, one directory per lineage upstream publishes, every
file byte-for-byte at the pin its provenance.csv row names.

`reference` is a NOUN: what is held. A bare invocation reports it against upstream
and writes nothing: per project, the lineages upstream lists against those held,
and per held file whether the bytes at its URL still hash as pinned - the
currency check, a send, so under YOGA_NO_SEND=1 it degrades to UNVERIFIED and
reports what is held. Only `sync` writes: it fetches every lineage upstream lists
that is not held, and every held file whose bytes drifted, and rewrites
provenance.csv; the lineage's changelog section (`## <pin>`) stays a hand act,
owed at the commit gate by reference.lineage_changelog. Re-running is silence (L1).

A project's reference.json names `upstream`; with `lineage_listing` (a GitHub
contents URL of the directory whose dated subdirectories are the lineages) and
`files` (what each lineage holds), the lineages are upstream's to list and the pin
is the newest upstream commit touching the file; without a listing, the lineages
are the provenance rows' and the pin is the URL's etag.

Usage:
    corpus-yoga reference         # status: what upstream lists, what is held, what drifted
    corpus-yoga reference sync    # fetch what is missing or drifted; write provenance.csv
"""

import csv
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

SELF = 'src/main/reference/reference.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ - modules both tiers import
from declared_parser import command_parser  # noqa: E402
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main - the tier's shared modules
from send import may_send, assert_may_send, SendRefused  # noqa: E402
from latest import lineages  # noqa: E402

ROOT = REPO / 'rsc' / 'reference'
COLUMNS = ('lineage', 'file', 'url', 'pin', 'sha256')
DATED = re.compile(r'\d{4}-\d{2}-\d{2}')
GITHUB_CONTENTS = re.compile(r'https://api\.github\.com/repos/([^/]+)/([^/]+)/contents/(.+)')
TIMEOUT = 20


def projects() -> list[Path]:
    return sorted(p for p in ROOT.iterdir() if p.is_dir())


def declaration(project: Path) -> dict:
    path = project / 'reference.json'
    return json.loads(path.read_text()) if path.is_file() else {}


def rows(project: Path) -> list[dict]:
    path = project / 'provenance.csv'
    if not path.is_file():
        return []
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh))


def write_rows(project: Path, table: list[dict]) -> None:
    with (project / 'provenance.csv').open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(sorted(table, key=lambda r: (r['lineage'], r['file'])))


def _get(url: str) -> tuple[bytes, dict]:
    request = urllib.request.Request(url, headers={'User-Agent': 'corpus-yoga reference'})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read(), dict(response.headers)


def _github(listing: str) -> tuple[str, str, str]:
    m = GITHUB_CONTENTS.fullmatch(listing)
    assert m, f'lineage_listing is not a GitHub contents URL: {listing}'
    return m.group(1), m.group(2), m.group(3).rstrip('/')


def upstream_lineages(listing: str) -> list[str]:
    body, _ = _get(listing)
    return sorted(e['name'] for e in json.loads(body) if e['type'] == 'dir' and DATED.fullmatch(e['name']))


def upstream_commit(owner: str, repo: str, path: str) -> str:
    body, _ = _get(f'https://api.github.com/repos/{owner}/{repo}/commits?path={path}&sha=main&per_page=1')
    commits = json.loads(body)
    assert commits, f'no commit touches {path} on {owner}/{repo} main'
    return commits[0]['sha']


def wanted(project: Path) -> list[dict]:
    """(lineage, file, url) for every file the project should hold: upstream's dated
    lineages by the declared files where a listing is declared, else the held rows."""
    decl = declaration(project)
    listing = decl.get('lineage_listing')
    if not listing:
        return [{'lineage': r['lineage'], 'file': r['file'], 'url': r['url']} for r in rows(project)]
    owner, repo, path = _github(listing)
    files = decl.get('files') or []
    assert files, f'{project.name}: reference.json declares a lineage listing but no files'
    return [{'lineage': lineage, 'file': file,
             'url': f'https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/main/{path}/{lineage}/{file}'}
            for lineage in upstream_lineages(listing) for file in files]


def _pin(project: Path, item: dict, headers: dict) -> str:
    decl = declaration(project)
    listing = decl.get('lineage_listing')
    if listing:
        owner, repo, path = _github(listing)
        return upstream_commit(owner, repo, f'{path}/{item["lineage"]}/{item["file"]}')
    etag = (headers.get('ETag') or headers.get('etag') or '').strip().removeprefix('W/').strip('"')
    return f'etag {etag}' if etag else f'sha256 {hashlib.sha256(item["bytes"]).hexdigest()}'


def _reading(project: Path) -> tuple[list[dict], list[str]]:
    """Every wanted item with its live bytes, and the lines to print: what is
    missing, what drifted. Sends."""
    held = {(r['lineage'], r['file']): r for r in rows(project)}
    items, lines = [], []
    for item in wanted(project):
        body, headers = _get(item['url'])
        digest = hashlib.sha256(body).hexdigest()
        row = held.get((item['lineage'], item['file']))
        state = 'missing' if row is None else ('drifted' if row['sha256'] != digest else 'current')
        items.append({**item, 'bytes': body, 'headers': headers, 'sha256': digest, 'state': state, 'row': row})
        if state != 'current':
            lines.append(f'  {state}: {item["lineage"]}/{item["file"]}'
                         + (f' - upstream hashes {digest[:12]}, provenance.csv pins {row["sha256"][:12]}' if row else ''))
    return items, lines


def status() -> int:
    stale = 0
    for project in projects():
        name = project.name
        held = [d.name for d in lineages(project)]
        table = rows(project)
        if not may_send():
            print(f'reference: {name}: holds {len(held)} lineage(s) {held}, {len(table)} pinned file(s) - '
                  'currency UNVERIFIED (YOGA_NO_SEND=1 refuses the probe)')
            continue
        items, lines = _reading(project)
        listing = declaration(project).get('lineage_listing')
        upstream = sorted({i['lineage'] for i in items}) if listing else held
        print(f'reference: {name}: upstream lists {len(upstream)} lineage(s), held {len(held)}; '
              f'{sum(1 for i in items if i["state"] == "current")}/{len(items)} file(s) hash as pinned'
              + ('' if not lines else f' - {len(lines)} to fetch (corpus-yoga reference sync)'))
        for line in lines:
            print(line)
        stale += len(lines)
    return 1 if stale else 0


def sync() -> int:
    assert_may_send('fetching upstream reference lineages')
    for project in projects():
        items, lines = _reading(project)
        if not lines:
            continue                                # current means no write and nothing said (L1)
        table = {(r['lineage'], r['file']): r for r in rows(project)}
        minted = set()
        for item in items:
            if item['state'] == 'current':
                continue
            path = project / item['lineage'] / item['file']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(item['bytes'])
            pin = _pin(project, item, item['headers'])
            table[(item['lineage'], item['file'])] = {'lineage': item['lineage'], 'file': item['file'],
                                                      'url': item['url'], 'pin': pin, 'sha256': item['sha256']}
            minted.add((item['lineage'], pin))
            print(f'  ✓ {path.relative_to(REPO)} ({item["state"]}, {len(item["bytes"]):,} bytes, pin {pin})')
        write_rows(project, list(table.values()))
        print(f'  ✓ {(project / "provenance.csv").relative_to(REPO)}')
        for lineage, pin in sorted(minted):
            print(f'  write the section `## {pin}` in {(project / lineage / "CHANGELOG.md").relative_to(REPO)} '
                  '(the dev gate holds reference.lineage_changelog)')
    return 0


def main():
    parser = command_parser('reference')
    args = parser.parse_args()
    try:
        sys.exit(sync() if args.verb == 'sync' else status())
    except SendRefused as refused:
        print(f'reference: NOT done - {refused}')
        sys.exit(1)


if __name__ == '__main__':
    main()
