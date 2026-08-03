"""
The one function every external command runs through: echo it, execute it, trap its
status, relay the verdict. Verbatim streams — stdout and stderr flow to the caller's own,
uncaptured, so the authority speaks in its own words. The narrative (the echo, the verdict)
goes to stderr, so a caller capturing the command's stdout gets exactly that and nothing
else.

The seam for the enactment-guard tier (#256): the one place a future policy would gate,
warn, or attribute an act, because every act already passes through here. Not implemented.
"""
import shlex
import subprocess
import sys


def enact(*command: str) -> int:
    printed = ' '.join(shlex.quote(part) for part in command)
    print(f'enact: {printed}', file=sys.stderr)
    status = subprocess.call(command)
    verdict = f'done: {printed}' if status == 0 else f'NOT done (exit {status}): {printed}'
    print(verdict, file=sys.stderr)
    return status
