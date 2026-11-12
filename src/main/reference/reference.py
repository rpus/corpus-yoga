#!/usr/bin/env python
"""
reference.py - the upstream reference artefacts under rsc/reference (issues/572, issues/587):
one project per upstream, one directory per lineage upstream publishes, every
file byte-for-byte at the pin its provenance.csv row names.

`reference` is a NOUN: what is held. Upstream is its remote, and reaches a room by
`fetch` alone (issues/1054): every file upstream publishes, written under
tmp/reference/fetch/<project>/<lineage>/ with a record beside them, fetched.csv, in
provenance.csv's columns. A bare invocation reads that record against provenance.csv
and sends nothing: per project, the lineages held, and each file the fetch found
missing here or drifted from its pin - or that no fetch has recorded what upstream
holds. No verb writes rsc/reference: it is the dev gate's witness, and what a fetch
brings reaches it as a commit - the fetched files and their fetched.csv rows copied
in, each lineage's changelog section (`## <pin>`) written, owed at the commit gate by
reference.lineage_changelog.

A project's reference.json names `upstream`; with `lineage_listing` (a GitHub
contents URL of the directory whose dated subdirectories are the lineages) and
`files` (what each lineage holds), the lineages are upstream's to list and the pin
is the newest upstream commit touching the file; without a listing, the lineages
are the provenance rows' and the pin is the URL's etag.

Usage:
    corpus-yoga reference         # status: what is held, and what the last fetch found against it
    corpus-yoga reference fetch   # record what upstream publishes under tmp/reference/fetch
"""

import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
import urllib.request
from pathlib import Path
from declared_parser import command_parser
import facts  # the one printer of a status's facts (issues/753)
import spell
import tier  # the tiers, one home (issues/702)
import send  # every read of upstream is a send the declaration names (issues/1022)
from latest import lineages

SELF = 'src/main/reference/reference.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

ROOT = REPO / 'rsc' / 'reference'
FETCH = tier.TMP / 'reference' / 'fetch'   # what the last fetch recorded of upstream, by project
COLUMNS = ('lineage', 'file', 'url', 'pin', 'sha256')
DATED = re.compile(r'\d{4}-\d{2}-\d{2}')
GITHUB_CONTENTS = re.compile(r'https://api\.github\.com/repos/([^/]+)/([^/]+)/contents/(.+)')


def projects() -> list[Path]:
    return sorted(p for p in ROOT.iterdir() if p.is_dir())


def declaration(project: Path) -> dict:
    path = project / 'reference.json'
    return json.loads(path.read_text()) if path.is_file() else {}


def rows(project: Path, name: str = 'provenance.csv') -> list[dict]:
    path = project / name
    if not path.is_file():
        return []
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh))


def write_rows(project: Path, table: list[dict], name: str = 'provenance.csv') -> None:
    with (project / name).open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(sorted(table, key=lambda r: (r['lineage'], r['file'])))


def _get(url: str, name: str = 'github-api') -> tuple[bytes, dict]:
    request = urllib.request.Request(url, headers={'User-Agent': 'corpus-yoga reference'})
    with send.urlopen(name, request) as response:
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


def drift(project: Path, fetched: Path) -> dict[str, str] | None:
    """What the last fetch found of upstream against what the project pins, by file: missing
    here, or drifted from its pin; None where no fetch has recorded what upstream holds.
    Reads the two records; sends nothing."""
    if not (fetched / 'fetched.csv').is_file():
        return None
    held = {(r['lineage'], r['file']): r for r in rows(project)}
    lines: dict[str, str] = {}
    for found in rows(fetched, 'fetched.csv'):
        row = held.get((found['lineage'], found['file']))
        if row is None:
            lines[f'{found["lineage"]}/{found["file"]}'] = 'missing'
        elif row['sha256'] != found['sha256']:
            lines[f'{found["lineage"]}/{found["file"]}'] = f'drifted - upstream hashes {found["sha256"][:12]}, provenance.csv pins {row["sha256"][:12]}'
    return lines


@dataclass
class Project:
    lineages_held: list[str] | None = None
    pinned_files: int | None = None
    upstream: str | facts.Unsettled | None = None
    upstream_as_fetched: dict[str, str] | None = None   # by file: missing here, or drifted from its pin
    act: facts.Would | None = None


@dataclass
class Status:
    projects: dict[str, Project]
    reference: str                # the verdict

    def facts(self) -> dict:
        return {**self.projects, 'reference': self.reference}


def status() -> int:
    """Each project's held lineages, and what the last fetch found of upstream against them, as
    facts (issues/753): read from the fetch's record, never sent for (issues/1054)."""
    differing = unfetched = 0
    out: dict[str, Project] = {}
    for project in projects():
        name = project.name
        item = Project(lineages_held=[d.name for d in lineages(project)], pinned_files=len(rows(project)))
        lines = drift(project, FETCH / name)
        if lines is None:
            unfetched += 1
            item.upstream = facts.Unsettled(facts.phrase('unfetched - no fetch has recorded what upstream holds'), 'reference')
            item.act = facts.Would(spell.line('reference', 'fetch'), {name: 1})
        elif lines:
            differing += len(lines)
            item.upstream = facts.phrase('as fetched, {n} file(s) differ from what is held', n=len(lines))
            item.upstream_as_fetched = lines
        else:
            item.upstream = facts.phrase('as fetched, every file is held as pinned')
        out[name] = item
    facts.say_standing(Status(out, facts.phrase('{n} project(s), {differing} file(s) differing from upstream as fetched, {unfetched} unfetched',
                                                n=len(out), differing=differing, unfetched=unfetched)))
    return 0


def fetch() -> int:
    """Record what upstream publishes, per project (issues/1054): each wanted file's bytes under
    tmp/reference/fetch/<project>/<lineage>/, and fetched.csv beside them with each file's pin and
    hash. Sends; writes nothing under rsc/reference."""
    for project in projects():
        into = FETCH / project.name
        table: list[dict] = []
        for item in wanted(project):
            body, headers = _get(item['url'], 'upstream-raw')
            item = {**item, 'bytes': body}
            path = into / item['lineage'] / item['file']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            table.append({'lineage': item['lineage'], 'file': item['file'], 'url': item['url'],
                          'pin': _pin(project, item, headers), 'sha256': hashlib.sha256(body).hexdigest()})
        into.mkdir(parents=True, exist_ok=True)
        write_rows(into, table, 'fetched.csv')
        print(f'  ✓ {(into / "fetched.csv").relative_to(tier.DATA_ROOT)} (' + facts.phrase('{n} file(s) of {project} as upstream publishes them', n=len(table), project=project.name) + ')')
    facts.report(None, 'reference fetch: DONE - ' + facts.phrase('did record what upstream publishes; corpus-yoga reference says what differs from what is held'))
    return 0


def main():
    parser = command_parser('reference')
    args = parser.parse_args()
    try:
        sys.exit(fetch() if args.verb == 'fetch' else status())
    except send.SendRefused as refused:
        facts.report(None, f'reference fetch: NOT DONE - {refused}')
        sys.exit(1)


if __name__ == '__main__':
    main()
