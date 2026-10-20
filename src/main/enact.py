"""
The one function every external command should run through: say it, execute it, trap its
status, relay the verdict - each act one event of the record, a list item at the narration
depth through the printer (facts.narration, issues/805): `- <command>:` before it runs,
`did: done` or `did NOT: exit N` beneath after. Verbatim streams — stdout and stderr flow to the caller's own,
uncaptured, so the authority speaks in its own words. The narrative (the echo, the verdict)
goes to stderr, so a caller capturing the command's stdout gets exactly that and nothing
else.

The seam for the enactment-guard tier (issues/256): the one place a future policy would gate,
warn, or attribute an act, because every act already passes through here. Not implemented.

Success is silent: an act's own output is its evidence, and what a verb says when it
finishes is the verb's own business. query(), quote() and quiet() are the read faces, named
for how many times each renders the answer: query twice (the item carries the answer and
the return gives it), quote once (the return only; the item says done), quiet zero (the
item says done, the answer is discarded). Failure
is never quiet in any face. On failure query and quote raise; the shell face returns
the status — the pair's one ruled asymmetry (issues/277); the relay words themselves are
held identical by the gate.

CONSTRAINT ON EVERY CALLER, unenforceable here: the narrative rides stderr; silencing it
(stderr to devnull) renders a wrapped act invisible and the wrap decorative.
"""
import shlex
import subprocess
import sys

import facts


def _said(event) -> None:
    print('\n'.join(facts.narration(event)), file=sys.stderr)


def enact(*command: str) -> int:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(facts.narration({printed: {'did': 'done'}})[0], file=sys.stderr)
    status = subprocess.call(command)
    outcome = {'did': 'done'} if status == 0 else {'did NOT': f'exit {status}'}
    print('\n'.join(facts.narration({printed: outcome})[1:]), file=sys.stderr)
    return status


def query(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    answer = result.stdout.rstrip('\n')
    _said({printed: answer.splitlines() if '\n' in answer else answer})
    return answer


def quote(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    _said({printed: {'did': 'done'}})
    return result.stdout.rstrip('\n')


def quiet(*command: str) -> None:
    printed = ' '.join(shlex.quote(part) for part in command)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    _said({printed: {'did': 'done'}})
