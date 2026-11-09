"""
send.py - a send run by its name, the python face (send.sh is the shell's): the one reading
of CORPUS_YOGA_NO_SEND in this language, and the one place a send is refused, bounded and
narrated (issues/1022).

A SEND is an outward call - driving Safari against a logged-in session, fetching over the
network, writing outside the tree. It is the one effect with no scratch form: a read can be
pointed at a fixture and a write at a temp tree, but redirecting where a capture LANDS does
not stop the call going out. So the only way to exercise a send path without performing it
is to refuse it, which is what CORPUS_YOGA_NO_SEND=1 does.

Every send is one entry of the declaration the launcher dispatched, or of its noun's, which
the noun's verbs share - read once, at dispatch, and handed to the running code in
tier.DECLARATION (dispatched()), so that nothing the act does to the working tree changes
which sends it may make (issues/1036): under `sends`, its name, what it `runs`, what refusal does to it - it
`fails` where the send is the work, it `degrades` where it only enriches a report - and what
it `does`, in words. A script runs a send by that name alone, so a name the declaration lacks
cannot run, and the command has one home:

  run(face, name, *args)   the declared command and the args, through enact's face
  process(name, *args)     the declared command and the args, the completed process returned
  urlopen(name, request)   urllib.request.urlopen, the declared call
  within(name)             a block that is the send - a write outside the tree
  cleared(name)            the entry, where the send may run - for an act that must stop
                           before its local steps where a later send would be refused

Refused, each raises SendRefused, whatever the entry's `refused` says: a caller whose send
degrades catches it and says the reading unverified, and one whose send is the work lets it
fail the act.
"""
import contextlib
import json
import os
import shlex
import subprocess
import sys
import urllib.request
from pathlib import Path

import enact
import facts
import tier

SWITCH = 'CORPUS_YOGA_NO_SEND'
REFUSED_STATUS = 75   # the exit status of a script whose send was refused - send.sh's SEND_REFUSED, held equal by the gate
REPO = tier.REPO


class SendRefused(RuntimeError):
    """Raised in place of a send when CORPUS_YOGA_NO_SEND=1, naming what it runs. The
    sentence is composed here, once, so no catcher words a refusal differently."""

    def __init__(self, runs: str) -> None:
        super().__init__(f'{SWITCH}=1 refuses the send {runs}')


class Undeclared(RuntimeError):
    """Raised where the dispatched declaration names no send by the name asked."""


def refused() -> bool:
    """Whether outward calls are refused - the one reading of the environment."""
    return os.environ.get(SWITCH) == '1'


def dispatched(declaration: str) -> str:
    """The declaration as the running code is handed it, the value of tier.DECLARATION: its
    repo-relative address and its sends - the verb's own entries over its noun's, which every
    verb of the noun shares - read now, once."""
    path = REPO / declaration
    sends: dict = {}
    for held in (path.parent / f'{path.parent.name}.json', path):
        if held.is_file():
            sends.update(json.loads(held.read_text()).get('sends', {}))
    return json.dumps({'declaration': declaration, 'sends': sends})


def entry(name: str) -> dict:
    """The send the dispatched declaration names `name`; Undeclared otherwise."""
    handed = json.loads(os.environ.get(tier.DECLARATION) or '{}')
    sends = handed.get('sends', {})
    if name not in sends:
        raise Undeclared(f'{handed.get("declaration", "no declaration")} declares no send {name}')
    return sends[name]


def runs(name: str) -> str:
    """What the named send runs, as its declaration writes it."""
    return entry(name)['runs']


def cleared(name: str) -> dict:
    """The named send's entry, once it is declared and not refused; refused, the refusal is
    narrated as the send's outcome and raised."""
    declared = entry(name)
    if refused():
        _said(declared['runs'], {'did NOT': f'{SWITCH}=1 refuses it'})
        raise SendRefused(declared['runs'])
    return declared


def _said(printed: str, outcome: dict) -> None:
    print('\n'.join(facts.narration({printed: outcome})), file=sys.stderr)


def _argv(declared: dict, args) -> list[str]:
    """The declared command and the args; a program beside the interpreter - the venv's
    own - is preferred to one on PATH."""
    argv = shlex.split(declared['runs']) + list(args)
    beside = Path(sys.executable).parent / argv[0]
    if beside.is_file():
        argv[0] = str(beside)
    return argv


def run(face: str, name: str, *args: str):
    """The named send through enact's face - enact, labour, query, quote or quiet."""
    return getattr(enact, face)(*_argv(cleared(name), args))


def process(name: str, *args: str, **options) -> subprocess.CompletedProcess:
    """The named send as a process, under the send bound, its completed process returned -
    for a caller that reads its streams itself. Ended by the bound, it raises
    subprocess.TimeoutExpired."""
    options.setdefault('timeout', enact.bound())
    return subprocess.run(_argv(cleared(name), args), **options)


def urlopen(name: str, request):
    """The named send, urllib.request.urlopen, under the send bound."""
    cleared(name)
    return urllib.request.urlopen(request, timeout=enact.bound())


@contextlib.contextmanager
def within(name: str):
    """A block that is the named send - a write outside the tree."""
    cleared(name)
    yield
