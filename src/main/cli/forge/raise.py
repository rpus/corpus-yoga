#!/usr/bin/env python
"""raise.py (corpus-yoga forge raise) - a PR or an issue, raised by the forge (issues/884, issues/887).

pr: the title is the first issue's title, verbatim (issues/479); the why section is one aim line
per issue, in src/main/cli/forge/aim.py's grammar; every open blocker of an aimed issue is
aimed at too (issues/482), judged here as the merge judges it. issue: the title is the should,
held to src/main/cli/forge/should.py's grammar; the as-at anchor is derived from the
forge's main; each relation is wired through the blocked_by API as the issue is raised and
read back; a superseded issue is closed, its relations transferred and its ledger note
posted, in the one act. Both faces stamp the Signature from the triad the commit hook
uses (src/main/provider.py), and take the drafter's sections from the body file, which
carries nothing the forge writes. The body as sent is kept under tmp/forge/raise/<stamp>.md.
"""
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/cli/forge/raise.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ - modules both tiers import
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'forge'))
import aim  # noqa: E402 - the aim's one grammar
import should  # noqa: E402 - the issue's one grammar
import facts  # noqa: E402
import provider  # noqa: E402 - the Signature triad, derived once
import tier  # noqa: E402
from declared_parser import verb_parser  # noqa: E402
from enact import quote  # noqa: E402
from send import SendRefused, assert_may_send  # noqa: E402

RECORD = tier.TMP / 'forge' / 'raise'
FOOTER = ('Generated with', 'Co-Authored-By')
KINDS = ('pr', 'issue')


class Refused(Exception):
    """Why the raise does not happen, said in the effect line."""


def drafted(path: Path) -> str:
    """The body file's text, refused where it carries an attribution or a footer: the
    Signature is the forge's to stamp, and no body carries a harness footer."""
    if not path.is_file():
        raise Refused(f'{path} is no file')
    text = path.read_text()
    if re.search(r'^Signature:', text, re.M):
        raise Refused('the body carries a Signature line; the forge stamps it')
    for word in FOOTER:
        if word in text:
            raise Refused(f'the body carries {word!r}, which no raised body may')
    return text.strip('\n')


def issue(number: int) -> tuple[str, str]:
    state, title = quote('gh', 'issue', 'view', str(number), '--json', 'state,title',
                         '--jq', '[.state, .title] | @tsv').split('\t', 1)
    return state, title


def edges(number: int, direction: str) -> list[int]:
    """The issue's blocked_by edges in one direction: 'blocked_by', what it waits on;
    'blocking', what waits on it."""
    rows = quote('gh', 'api', f'repos/{{owner}}/{{repo}}/issues/{number}/dependencies/{direction}',
                 '--jq', '.[] | [.number, .state] | @tsv')
    return [int(row.split('\t')[0]) for row in rows.splitlines() if row]


def open_blockers(number: int) -> list[int]:
    rows = quote('gh', 'api', f'repos/{{owner}}/{{repo}}/issues/{number}/dependencies/blocked_by',
                 '--jq', '.[] | select(.state == "open") | .number')
    return [int(row) for row in rows.split() if row]


def node_id(number: int) -> str:
    return quote('gh', 'api', f'repos/{{owner}}/{{repo}}/issues/{number}', '--jq', '.id')


def wire(blocked: int, blocker: int) -> None:
    """blocked waits on blocker: one blocked_by edge, the forge's one relation."""
    quote('gh', 'api', '-X', 'POST', f'repos/{{owner}}/{{repo}}/issues/{blocked}/dependencies/blocked_by',
          '-F', f'issue_id={node_id(blocker)}')


def default_branch() -> str:
    return quote('gh', 'repo', 'view', '--json', 'defaultBranchRef', '--jq', '.defaultBranchRef.name')


def record(stamp: str, body: str) -> Path:
    RECORD.mkdir(parents=True, exist_ok=True)
    path = RECORD / f'{stamp}.md'
    path.write_text(body)
    return path


def number_of(url: str) -> int:
    return int(url.rstrip('/').rsplit('/', 1)[-1])


def check_pr(args, text: str) -> None:
    """What the pr face refuses before any send."""
    if not args.issue:
        raise Refused('no issue named; a PR aims to complete at least one')
    if not args.head:
        raise Refused('--head names the branch a PR is raised from')
    if args.title or args.blocked_by or args.blocks or args.supersedes:
        raise Refused('--title, --blocked-by, --blocks and --supersedes are the issue face\'s; a PR takes its issues and --head')
    bare = aim.bare(text)
    if aim.PHRASE in bare:
        raise Refused(f'the body says {aim.PHRASE}; the forge writes the aim lines')
    for word in ('## why', f'{aim.CLOSES} #'):
        if word in bare:
            raise Refused(f'the body carries {word!r}, which the forge writes or the merge alone may')


def check_issue(args, text: str) -> None:
    """What the issue face refuses before any send."""
    if args.issue or args.head:
        raise Refused('issues and --head are the pr face\'s; an issue takes --title and its relations')
    if not args.title:
        raise Refused('--title states the should an issue is raised for')
    should.check_title(args.title)
    should.check_body(text)


def raise_pr(args, signature: str, text: str, stamp: str) -> tuple[dict, dict, str]:
    numbers = [int(n) for n in args.issue]
    titles: dict[int, str] = {}
    for number in numbers:
        state, title = issue(number)
        if state != 'OPEN':
            raise Refused(f'#{number} is {state}; a PR aims only at an open issue')
        titles[number] = title
    for number in numbers:
        for blocker in open_blockers(number):
            if blocker not in numbers:
                raise Refused(f'#{number} is blocked by open #{blocker}, which this PR does not aim to complete (issues/482)')
    base = default_branch()
    why = '## why\n\n' + '\n'.join(aim.line(number, titles[number]) for number in numbers)
    sent = record(stamp, f'{signature}\n\n{why}\n\n{text}\n')
    url = quote('gh', 'pr', 'create', '--base', base, '--head', args.head,
                '--title', titles[numbers[0]], '--body-file', str(sent))
    pr = number_of(url)
    outcomes = {'did raise': {f'#{pr}': url, 'head': args.head, 'base': base, 'title copies': f'#{numbers[0]}',
                              'aims to complete': {f'#{n}': titles[n] for n in numbers},
                              'body': str(sent.relative_to(REPO))}}
    following = {f'corpus-yoga forge merge {pr}': 'merges it on the reviewer\'s word'}
    return outcomes, following, f'forge raise: DONE - did raise PR #{pr} at {args.head} for ' + ', '.join(f'#{n}' for n in numbers)


def raise_issue(args, signature: str, text: str, stamp: str) -> tuple[dict, dict, str]:
    blocked_by = [int(n) for n in args.blocked_by or []]
    blocks = [int(n) for n in args.blocks or []]
    supersedes = int(args.supersedes) if args.supersedes else None
    for number in blocked_by + blocks + ([supersedes] if supersedes else []):
        state, _ = issue(number)
        if state != 'OPEN':
            raise Refused(f'#{number} is {state}; a relation is wired to an open issue')
    branch = default_branch()
    sha, subject = quote('gh', 'api', f'repos/{{owner}}/{{repo}}/commits/{branch}',
                         '--jq', '[.sha, (.commit.message | split("\\n")[0])] | @tsv').split('\t', 1)
    date = stamp[:10]
    machine = signature.split('/', 1)[0]
    body = should.compose(signature, text, should.as_at(sha, subject, machine, date), supersedes)
    sent = record(stamp, body)
    url = quote('gh', 'issue', 'create', '--title', args.title, '--body-file', str(sent))
    number = number_of(url)
    if supersedes:
        blocked_by = blocked_by + [n for n in edges(supersedes, 'blocked_by') if n not in blocked_by and n != number]
        blocks = blocks + [n for n in edges(supersedes, 'blocking') if n not in blocks and n != number]
    for blocker in blocked_by:
        wire(number, blocker)
    for blocked in blocks:
        wire(blocked, number)
    if supersedes:
        note = (f'Signature: {signature}\n\nSuperseded by #{number} on the maintainer\'s word, {machine}, {date}, '
                f'at {branch} @ {sha[:7]}; its relations are transferred to #{number}.')
        quote('gh', 'issue', 'close', str(supersedes), '--reason', 'not planned', '--comment', note)
    read_blocked_by = edges(number, 'blocked_by')
    read_blocks = edges(number, 'blocking')
    outcomes = {'did raise': {f'#{number}': url, 'title': args.title, 'as at': should.as_at(sha, subject, machine, date),
                              'blocked by': [f'#{n}' for n in read_blocked_by] or 'none',
                              'blocks': [f'#{n}' for n in read_blocks] or 'none',
                              **({'did supersede': f'#{supersedes}'} if supersedes else {}),
                              'body': str(sent.relative_to(REPO))}}
    wired = sorted(set(blocked_by) ^ set(read_blocked_by)) + sorted(set(blocks) ^ set(read_blocks))
    if wired:
        return outcomes, {}, f'forge raise: NOT DONE - did raise issue #{number}, but the forge reads edges other than those wired: ' + ', '.join(f'#{n}' for n in wired)
    return outcomes, {}, (f'forge raise: DONE - did raise issue #{number}; blocked by {len(read_blocked_by)}, blocking {len(read_blocks)}'
                          + (f'; did supersede #{supersedes}' if supersedes else ''))


def main(argv: list[str]) -> int:
    args = verb_parser('forge', 'raise').parse_args(argv)
    os.chdir(REPO)  # gh resolves {owner}/{repo} from the checkout's remote
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
    try:
        if args.kind not in KINDS:
            raise Refused(f'the kind is pr or issue, not {args.kind!r}')
        text = drafted(Path(args.body))
        (check_pr if args.kind == 'pr' else check_issue)(args, text)
        signature = provider.signature()
        if signature.count('/') != 2:
            raise Refused(f'the Signature triad is not derivable here: {signature}; the session names no provider the registry declares')
        assert_may_send('gh issue view, gh api, gh repo view and the raise\'s writes (forge raise)')
        face = raise_pr if args.kind == 'pr' else raise_issue
        outcomes, following, effect = face(args, f'Signature: {signature}', text, stamp)
    except (Refused, SendRefused, ValueError) as why:
        facts.report(None, f'forge raise: NOT DONE - {why}')
        return 1
    except subprocess.CalledProcessError:
        facts.report(None, 'forge raise: NOT DONE - a gh call failed; the NOT-done line above names it')
        return 1
    facts.report(outcomes, effect, {**following})
    return 0 if effect.startswith('forge raise: DONE') else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
