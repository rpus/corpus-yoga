#!/usr/bin/env python
"""raise.py (corpus-yoga forge raise) - the PR, raised from the issues it aims to complete (#884).

The title is the first issue's title, verbatim (#479); the why section is one aim line
per issue, in src/main/cli/forge/aim.py's grammar; the rest of the body is the drafter's,
read from the body file: its first line the Signature, then the what, how and to sections
as .github/PULL_REQUEST_TEMPLATE.md teaches them, and no aim line, no why section and no
closes among them. Every open blocker of an aimed issue is aimed at too (#482), judged
here as the merge judges it, so a PR the merge would refuse is not raised. The body as
sent is kept under tmp/forge/raise/<stamp>.md, the record of what was raised.
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
import corpus  # noqa: E402 - the room's to-do, which every act ends on (#876)
import facts  # noqa: E402
import tier  # noqa: E402
from declared_parser import verb_parser  # noqa: E402
from enact import quote  # noqa: E402
from send import SendRefused, assert_may_send  # noqa: E402

RECORD = tier.TMP / 'forge' / 'raise'
SIGNATURE = re.compile(r'^Signature: [^/\s]+/[^/\s]+/[0-9a-f]{8}$')
FORBIDDEN = ('## why', f'{aim.CLOSES} #', 'Generated with', 'Co-Authored-By')


class Refused(Exception):
    """Why the raise does not happen, said in the verdict."""


def drafted(path: Path) -> tuple[str, str]:
    """The body file as the Signature line and the rest; refused where it carries what the
    forge writes or what no body may carry."""
    if not path.is_file():
        raise Refused(f'{path} is no file')
    text = path.read_text()
    lines = text.split('\n')
    if not lines or not SIGNATURE.match(lines[0]):
        raise Refused(f'the body\'s first line is not a Signature triad: {lines[0][:60]!r}')
    bare = aim.bare(text)
    if aim.PHRASE in bare:
        raise Refused(f'the body says {aim.PHRASE}; the forge writes the aim lines')
    for word in FORBIDDEN:
        if word in bare:
            raise Refused(f'the body carries {word!r}, which no raised body may')
    return lines[0], '\n'.join(lines[1:]).strip('\n')


def issue(number: int) -> tuple[str, str]:
    state, title = quote('gh', 'issue', 'view', str(number), '--json', 'state,title',
                         '--jq', '[.state, .title] | @tsv').split('\t', 1)
    return state, title


def open_blockers(number: int) -> list[int]:
    rows = quote('gh', 'api', f'repos/{{owner}}/{{repo}}/issues/{number}/dependencies/blocked_by',
                 '--jq', '.[] | select(.state == "open") | .number')
    return [int(row) for row in rows.split() if row]


def main(argv: list[str]) -> int:
    args = verb_parser('forge', 'raise').parse_args(argv)
    numbers = [int(n) for n in args.issue]
    os.chdir(REPO)  # gh resolves {owner}/{repo} from the checkout's remote
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
    try:
        if not numbers:
            raise Refused('no issue named; a PR aims to complete at least one')
        signature, rest = drafted(Path(args.body))
        assert_may_send('gh issue view, gh api, gh repo view and gh pr create (forge raise)')
        titles: dict[int, str] = {}
        for number in numbers:
            state, title = issue(number)
            if state != 'OPEN':
                raise Refused(f'#{number} is {state}; a PR aims only at an open issue')
            titles[number] = title
        for number in numbers:
            for blocker in open_blockers(number):
                if blocker not in numbers:
                    raise Refused(f'#{number} is blocked by open #{blocker}, which this PR does not aim to complete (#482)')
        base = quote('gh', 'repo', 'view', '--json', 'defaultBranchRef', '--jq', '.defaultBranchRef.name')
        why = '## why\n\n' + '\n'.join(aim.line(number, titles[number]) for number in numbers)
        body = f'{signature}\n\n{why}\n\n{rest}\n'
        RECORD.mkdir(parents=True, exist_ok=True)
        record = RECORD / f'{stamp}.md'
        record.write_text(body)
        url = quote('gh', 'pr', 'create', '--base', base, '--head', args.head,
                    '--title', titles[numbers[0]], '--body-file', str(record))
    except (Refused, SendRefused, ValueError) as why:
        facts.report(None, corpus.room_next(), f'forge raise: NOT DONE - {why}')
        return 1
    except subprocess.CalledProcessError:
        facts.report(None, corpus.room_next(), 'forge raise: NOT DONE - a gh call failed; the NOT-done line above names it')
        return 1
    pr = url.rstrip('/').rsplit('/', 1)[-1]
    outcomes = {'did raise': {f'#{pr}': url, 'head': args.head, 'base': base,
                              'title copies': f'#{numbers[0]}',
                              'aims to complete': {f'#{n}': titles[n] for n in numbers},
                              'body': str(record.relative_to(REPO))}}
    facts.report(outcomes, {**corpus.room_next(), f'corpus-yoga forge merge {pr}': 'merges it on the reviewer\'s word'},
                 f'forge raise: DONE - did raise #{pr} at {args.head} for ' + ', '.join(f'#{n}' for n in numbers))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
