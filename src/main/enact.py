"""
The one function every external command should run through: echo it, execute it, trap its
status, relay the verdict. Verbatim streams — stdout and stderr flow to the caller's own,
uncaptured, so the authority speaks in its own words. The narrative (the echo, the verdict)
goes to stderr, so a caller capturing the command's stdout gets exactly that and nothing
else.

The seam for the enactment-guard tier (#256): the one place a future policy would gate,
warn, or attribute an act, because every act already passes through here. Not implemented.

Success is silent: an act's own output is its evidence, and the consuming verb's closing
envelope is the one done-line. query() and quiet() are the read faces: the answer
returns to the caller; query relays it to the narrative, quiet elides the relay by
name, declared at the call site for answers the verb's own report renders. Failure
is never quiet in any face. On
failure query raises; the shell face returns the status — the pair's one ruled
asymmetry (#277); the relay words themselves are held identical by the gate.

CONSTRAINT ON EVERY CALLER, unenforceable here: the narrative rides stderr; silencing it
(stderr to devnull) renders a wrapped act invisible and the wrap decorative.
"""
import shlex
import subprocess
import sys


def enact(*command: str) -> int:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(f'enact: {printed}', file=sys.stderr)
    status = subprocess.call(command)
    if status != 0:
        print(f'NOT done (exit {status}): {printed}', file=sys.stderr)
    return status


def query(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(f'query: {printed}', file=sys.stderr)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        print(f'NOT done (exit {result.returncode}): {printed}', file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)
    answer = result.stdout.rstrip('\n')
    print(f'= {answer}', file=sys.stderr)
    return answer


def quiet(*command: str) -> str:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(f'quiet: {printed}', file=sys.stderr)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        print(f'NOT done (exit {result.returncode}): {printed}', file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)
    return result.stdout.rstrip('\n')
