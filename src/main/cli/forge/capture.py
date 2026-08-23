#!/usr/bin/env python
"""capture.py (yoga forge capture) - deposit the forge's ledger as a record like every other.

The deposit is one stamped directory, data/input/github/forge/gh-CLI/<stamp>/, holding
one file per forge object class - the eight below - and nothing about itself: the
directory's name is the capture's one time label, the repository is the data root's,
every count is a file's length, and the act's record (room, head, the commands, the
verdict) is the launcher's run log under tmp/logs/forge/capture/, as for every verb.

| file                       | command                                                              |
| -------------------------- | -------------------------------------------------------------------- |
| issues_and_pulls.json      | gh api --paginate --slurp repos/{owner}/{repo}/issues?state=all      |
| pulls.json                 | gh api --paginate --slurp repos/{owner}/{repo}/pulls?state=all       |
| issue_comments.json        | gh api --paginate --slurp repos/{owner}/{repo}/issues/comments       |
| review_comments.json       | gh api --paginate --slurp repos/{owner}/{repo}/pulls/comments        |
| labels.json                | gh api --paginate --slurp repos/{owner}/{repo}/labels                |
| reviews_by_pull.json       | {"n": [...]} for every number n in pulls.json; gh api repos/{owner}/{repo}/pulls/n/reviews for the n whose reviews.totalCount is nonzero in one paginated GraphQL read (review-counts.graphql); [] for the rest |
| blocked_by_by_issue.json   | {"n": [...]} for every issue n in issues_and_pulls.json (no pull_request key); gh api repos/{owner}/{repo}/issues/n/dependencies/blocked_by for the n whose issue_dependencies_summary.total_blocked_by is nonzero in the list object (or absent); [] for the rest |
| repository.json            | gh api repos/{owner}/{repo}                                          |

Each paginated list is fetched whole (per_page=100, --slurp wraps the pages in one
array, flattened here) and written as a single array with json.dump(indent=1); the
per-pull and per-issue maps likewise. No record is filtered, renamed, or reordered.
A per-object read is made only where the bulk reads say there is something to read -
the GraphQL review counts, the list object's dependency summary - so a capture is some
fifty gh calls, not one per pull and per issue.

Content-keyed and idempotent (L1): the seven LEDGER files are compared byte-for-byte
with the latest deposit's; identical, nothing is deposited and the verdict says so.
repository.json rides along with a deposit but is not part of the key - its pushed_at
and size move with every push, and they are not ledger. Append-only: a deposit is a new
stamped directory; no earlier one is ever rewritten.

Known limits: the REST issues list includes pull requests (hence the file's name -
pulls.json is the same objects under the pull-request resource, with merge state and
head/base shas); only blocked_by edges are captured, the repository's one issue
relation (blocking derives from it); not captured: commit status checks, event
timelines, reactions, the dependency graph beyond blocked_by.

Usage:
    src/run_python_script.sh src/main/cli/forge/capture.py <stamp> [--to <dir>]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SELF = 'src/main/cli/forge/capture.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
from enact import quote  # noqa: E402
from send import SendRefused, assert_may_send  # noqa: E402

STORE = REPO / 'data' / 'input' / 'github' / 'forge' / 'gh-CLI'
REVIEW_COUNTS = 'src/main/cli/forge/review-counts.graphql'

LISTS = [
    ('issues_and_pulls.json', 'repos/{owner}/{repo}/issues?state=all&per_page=100'),
    ('pulls.json', 'repos/{owner}/{repo}/pulls?state=all&per_page=100'),
    ('issue_comments.json', 'repos/{owner}/{repo}/issues/comments?per_page=100'),
    ('review_comments.json', 'repos/{owner}/{repo}/pulls/comments?per_page=100'),
    ('labels.json', 'repos/{owner}/{repo}/labels?per_page=100'),
]
LEDGER = [name for name, _ in LISTS] + ['reviews_by_pull.json', 'blocked_by_by_issue.json']
ROSTER = LEDGER + ['repository.json']


def gh_api(*args: str) -> str:
    return quote('gh', 'api', *args)


def fetch_list(endpoint: str) -> list:
    pages = json.loads(gh_api('--paginate', '--slurp', endpoint))
    return [record for page in pages for record in page]


def fetch_map(endpoint: str, numbers: list[int], read: set[int], tolerate_refusal: bool) -> dict:
    """{"n": [...]} for every number; the endpoint is read only for n in `read`, the
    numbers the bulk reads showed to have something - the rest are [] unread."""
    out = {}
    for n in numbers:
        answer: list = []
        if n in read:
            try:
                answer = json.loads(gh_api(endpoint.replace('<n>', str(n))))
            except subprocess.CalledProcessError:
                if not tolerate_refusal:
                    raise
        out[str(n)] = answer if isinstance(answer, list) else []
    return out


def reviewed_pulls() -> set[int]:
    """The pull numbers with any review, from one paginated GraphQL read of every
    pull's reviews.totalCount (src/main/cli/forge/review-counts.graphql)."""
    pages = json.loads(gh_api('graphql', '--paginate', '--slurp', '-F', 'owner={owner}',
                              '-F', 'repo={repo}', '-F', f'query=@{REVIEW_COUNTS}'))
    return {node['number'] for page in pages
            for node in page['data']['repository']['pullRequests']['nodes']
            if node['reviews']['totalCount']}


def blocked_issues(issues: list[dict]) -> set[int]:
    """The issue numbers with any blocked_by edge, from the list object's
    issue_dependencies_summary.total_blocked_by; an issue without the summary is read."""
    return {i['number'] for i in issues
            if (i.get('issue_dependencies_summary') or {}).get('total_blocked_by', 1)}


Captured = list | dict


def fetch() -> dict[str, Captured]:
    lists = {name: fetch_list(endpoint) for name, endpoint in LISTS}
    pulls = [p['number'] for p in lists['pulls.json']]
    issues = [i for i in lists['issues_and_pulls.json'] if 'pull_request' not in i]
    got: dict[str, Captured] = dict(lists)
    got['reviews_by_pull.json'] = fetch_map(
        'repos/{owner}/{repo}/pulls/<n>/reviews', pulls, reviewed_pulls(), tolerate_refusal=False)
    got['blocked_by_by_issue.json'] = fetch_map(
        'repos/{owner}/{repo}/issues/<n>/dependencies/blocked_by', [i['number'] for i in issues],
        blocked_issues(issues), tolerate_refusal=True)
    got['repository.json'] = json.loads(gh_api('repos/{owner}/{repo}'))
    return got


def render(value: Captured) -> bytes:
    return (json.dumps(value, indent=1) + '\n').encode()


def latest_deposit(store: Path) -> Path | None:
    stamps = sorted(p for p in store.iterdir() if p.is_dir()) if store.is_dir() else []
    return stamps[-1] if stamps else None


def count(name: str, value: Captured) -> int:
    """Records in a file: a list's length, a map's summed lengths, the one repository record."""
    if name == 'repository.json':
        return 1
    return sum(len(v) for v in value.values()) if isinstance(value, dict) else len(value)


def main(argv: list[str]) -> int:
    stamp, to = argv[0], None
    if len(argv) == 3 and argv[1] == '--to':
        to = Path(argv[2])
    elif len(argv) != 1:
        sys.exit(f'usage: {SELF} <stamp> [--to <dir>]')
    store = to if to else STORE
    os.chdir(REPO)  # gh resolves {owner}/{repo} from the checkout's remote
    try:
        assert_may_send('gh api (forge capture)')
        got = fetch()
    except SendRefused as refused:
        print(f'forge capture: NOT DONE - {refused}')
        return 1
    except subprocess.CalledProcessError:
        print('forge capture: NOT DONE - a gh api read failed (the NOT-done line above names it); nothing deposited')
        return 1
    rendered = {name: render(got[name]) for name in ROSTER}
    latest = latest_deposit(store)
    rel = store.relative_to(REPO) if store.is_relative_to(REPO) else store
    print(f'{rel}/ - latest deposit: {latest.name if latest else "none"}')
    changed = []
    for name in ROSTER:
        before = (latest / name).read_bytes() if latest and (latest / name).exists() else None
        state = 'new' if before is None else ('same' if before == rendered[name] else 'changed')
        if name in LEDGER and state != 'same':
            changed.append(name)
        print(f'  {name}: {count(name, got[name])} ({state})')
    if latest and not changed:
        print(f'forge capture: DONE - the ledger is unchanged since {latest.name}; nothing deposited')
        return 0
    target = store / stamp
    target.mkdir(parents=True, exist_ok=False)
    for name in ROSTER:
        (target / name).write_bytes(rendered[name])
    since = f'changed since {latest.name}: {", ".join(changed)}' if latest else 'the first deposit'
    print(f'forge capture: DONE - deposited {rel}/{stamp}/ ({len(ROSTER)} files) - {since}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
