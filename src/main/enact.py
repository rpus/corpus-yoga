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
import os
import shlex
import signal
import subprocess
import sys

import facts

SEND_TIMEOUT = 'CORPUS_YOGA_SEND_TIMEOUT'   # the bound on any one command, in seconds (issues/945); 60 unset


def bound() -> int:
    return int(os.environ.get(SEND_TIMEOUT) or 60)


def _said(event) -> None:
    print('\n'.join(facts.narration(event)), file=sys.stderr)


def _ended_whole(process) -> None:
    """End an act that ran out whole (issues/992): every descendant, deepest first, then the act,
    so that nothing of it survives the bound - a gate's python outlived its shell once, and
    the tree was removed beneath it."""
    rows = [line.split() for line in subprocess.run(['ps', '-axo', 'pid=,ppid='], capture_output=True, text=True).stdout.splitlines()]
    tree = [process.pid]
    for pid in tree:
        tree.extend(int(child) for child, parent in rows if int(parent) == pid)
    for pid in reversed(tree):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    process.wait()


def _bounded(command, capture: bool):
    """The command under the send bound, as subprocess.run would return it; TimeoutExpired
    where it ran out, with nothing of it left running."""
    with subprocess.Popen(command, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, text=True) as process:
        try:
            out, err = process.communicate(timeout=bound())
        except subprocess.TimeoutExpired:
            _ended_whole(process)
            raise
    return subprocess.CompletedProcess(command, process.returncode, out, err)


def enact(*command: str) -> int:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(facts.narration({printed: {'did': 'done'}})[0], file=sys.stderr)
    try:
        status = _bounded(command, capture=False).returncode
    except subprocess.TimeoutExpired:
        print('\n'.join(facts.narration({printed: {'did NOT': f'no answer within {bound()} s'}})[1:]), file=sys.stderr)
        return 124
    outcome = {'did': 'done'} if status == 0 else {'did NOT': f'exit {status}'}
    print('\n'.join(facts.narration({printed: outcome})[1:]), file=sys.stderr)
    return status


def labour(*command: str) -> int:
    """enact under no bound (issues/992): a local act whose duration is its own - a gate, a sync -
    never a send's; said and relayed exactly as enact says and relays."""
    printed = ' '.join(shlex.quote(part) for part in command)
    print(facts.narration({printed: {'did': 'done'}})[0], file=sys.stderr)
    status = subprocess.call(command)
    outcome = {'did': 'done'} if status == 0 else {'did NOT': f'exit {status}'}
    print('\n'.join(facts.narration({printed: outcome})[1:]), file=sys.stderr)
    return status


def query(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    try:
        result = _bounded(command, capture=True)
    except subprocess.TimeoutExpired:
        _said({printed: {'did NOT': f'no answer within {bound()} s'}})
        raise subprocess.CalledProcessError(124, command)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    answer = result.stdout.rstrip('\n')
    _said({printed: answer.splitlines() if '\n' in answer else answer})
    return answer


def quote(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    try:
        result = _bounded(command, capture=True)
    except subprocess.TimeoutExpired:
        _said({printed: {'did NOT': f'no answer within {bound()} s'}})
        raise subprocess.CalledProcessError(124, command)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    _said({printed: {'did': 'done'}})
    return result.stdout.rstrip('\n')


def quiet(*command: str) -> None:
    printed = ' '.join(shlex.quote(part) for part in command)
    try:
        result = _bounded(command, capture=True)
    except subprocess.TimeoutExpired:
        _said({printed: {'did NOT': f'no answer within {bound()} s'}})
        raise subprocess.CalledProcessError(124, command)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        _said({printed: {'did NOT': f'exit {result.returncode}'}})
        raise subprocess.CalledProcessError(result.returncode, command)
    _said({printed: {'did': 'done'}})
