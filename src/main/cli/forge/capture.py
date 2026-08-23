#!/usr/bin/env python
"""capture.py (yoga forge capture) - deposit the forge's ledger as a record like every other.

The deposit is one stamped directory, data/input/github/forge/gh-CLI/<stamp>/, holding
one file per forge read - the nine below - and nothing about itself: the directory's
name is the capture's one time label, the repository is the data root's, every count
is a file's length, and the act's record (room, head, the commands, the verdict) is
the launcher's run log under tmp/logs/forge/capture/, as for every verb.

| file                       | what the forge returned to                                           |
| -------------------------- | -------------------------------------------------------------------- |
| issues_and_PRs.json      | gh api --paginate --slurp repos/{owner}/{repo}/issues?state=all      |
| PRs.json                 | gh api --paginate --slurp repos/{owner}/{repo}/pulls?state=all       |
| issue_comments.json        | gh api --paginate --slurp repos/{owner}/{repo}/issues/comments       |
| review_comments.json       | gh api --paginate --slurp repos/{owner}/{repo}/pulls/comments        |
| labels.json                | gh api --paginate --slurp repos/{owner}/{repo}/labels                |
| review_counts.json         | gh api graphql --paginate --slurp -F query=@review-counts.graphql: every pull's number and reviews.totalCount |
| reviews_by_PR.json       | {"n": [...]}: gh api repos/{owner}/{repo}/pulls/n/reviews, for each n whose totalCount in review_counts.json is nonzero |
| blocked_by_by_issue.json   | {"n": [...]}: gh api repos/{owner}/{repo}/issues/n/dependencies/blocked_by, for each issue n (no pull_request key) whose issue_dependencies_summary.total_blocked_by in issues_and_PRs.json is nonzero or absent |
| repository.json            | gh api repos/{owner}/{repo}                                          |

Every byte under the stamp is something the forge returned: a paginated list is its
pages joined (--slurp wraps them in one array, flattened here), a map holds only the
objects actually read, and which objects were read is itself in the deposit (the
review counts, the dependency summaries) - so a per-object read is made only where a
bulk read says there is something to read, and a capture is some fifty gh calls, not
one per pull and per issue. Files are written as json.dump(indent=1); no record is
filtered, renamed, or reordered.

A capture reads its source and no other capture (the maintainer's ruling, 2026-08-23):
every run deposits a new stamped directory, and whether one deposit supersedes another
is a consumer's derivation (L3), never decided here. Nothing is written until every read
has succeeded, so a stamp is whole or absent.

Known limits: the REST issues list includes pull requests (hence the file's name -
PRs.json is the same objects under the pull-request resource, with merge state and
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
    ('issues_and_PRs.json', 'repos/{owner}/{repo}/issues?state=all&per_page=100'),
    ('PRs.json', 'repos/{owner}/{repo}/pulls?state=all&per_page=100'),
    ('issue_comments.json', 'repos/{owner}/{repo}/issues/comments?per_page=100'),
    ('review_comments.json', 'repos/{owner}/{repo}/pulls/comments?per_page=100'),
    ('labels.json', 'repos/{owner}/{repo}/labels?per_page=100'),
]
ROSTER = [name for name, _ in LISTS] + ['review_counts.json', 'reviews_by_PR.json',
                                        'blocked_by_by_issue.json', 'repository.json']

Captured = list | dict


def gh_api(*args: str) -> str:
    return quote('gh', 'api', *args)


def fetch_list(endpoint: str) -> list:
    pages = json.loads(gh_api('--paginate', '--slurp', endpoint))
    return [record for page in pages for record in page]


def fetch_map(endpoint: str, numbers: list[int], tolerate_refusal: bool) -> dict:
    """{"n": [...]} for each number read - only those; the endpoint's refusal, where
    tolerated, is the empty list it stands for."""
    out = {}
    for n in numbers:
        try:
            answer = json.loads(gh_api(endpoint.replace('<n>', str(n))))
        except subprocess.CalledProcessError:
            if not tolerate_refusal:
                raise
            answer = []
        out[str(n)] = answer if isinstance(answer, list) else []
    return out


def fetch_review_counts() -> list:
    """Every pull's number and reviews.totalCount, one paginated GraphQL read
    (src/main/cli/forge/review-counts.graphql), pages flattened to the nodes."""
    pages = json.loads(gh_api('graphql', '--paginate', '--slurp', '-F', 'owner={owner}',
                              '-F', 'repo={repo}', '-F', f'query=@{REVIEW_COUNTS}'))
    return [node for page in pages for node in page['data']['repository']['pullRequests']['nodes']]


def fetch() -> dict[str, Captured]:
    got: dict[str, Captured] = {name: fetch_list(endpoint) for name, endpoint in LISTS}
    counts = fetch_review_counts()
    got['review_counts.json'] = counts
    reviewed = [node['number'] for node in counts if node['reviews']['totalCount']]
    blocked = [i['number'] for i in got['issues_and_PRs.json'] if 'pull_request' not in i
               and (i.get('issue_dependencies_summary') or {}).get('total_blocked_by', 1)]
    got['reviews_by_PR.json'] = fetch_map(
        'repos/{owner}/{repo}/pulls/<n>/reviews', reviewed, tolerate_refusal=False)
    got['blocked_by_by_issue.json'] = fetch_map(
        'repos/{owner}/{repo}/issues/<n>/dependencies/blocked_by', blocked, tolerate_refusal=True)
    got['repository.json'] = json.loads(gh_api('repos/{owner}/{repo}'))
    return got


def render(value: Captured) -> bytes:
    return (json.dumps(value, indent=1) + '\n').encode()


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
    rel = store.relative_to(REPO) if store.is_relative_to(REPO) else store
    target = store / stamp
    target.mkdir(parents=True, exist_ok=False)
    for name in ROSTER:
        (target / name).write_bytes(render(got[name]))
        print(f'  {name}: {count(name, got[name])}')
    print(f'forge capture: DONE - deposited {rel}/{stamp}/ ({len(ROSTER)} files)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
