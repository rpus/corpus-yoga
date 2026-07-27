"""
The one reading of YOGA_NO_SEND, and the two ways of honouring it.

A SEND is an outward call — driving Safari against a logged-in session, fetching over the
network. It is the one effect with no scratch form: a read can be pointed at a fixture and
a write at a temp tree, but redirecting where a capture LANDS does not stop the call going
out. So the only way to exercise a send path without performing it is to refuse it, which
is what YOGA_NO_SEND=1 does.

Refusal means different things to the two kinds of caller, and both are named here so the
difference reads as a decision rather than an oversight:

  assert_may_send()  the send IS the work — a capture that never reached the account has
                     no result, and reporting success would be a lie, so refusal raises
  may_send()         the send only checks stored data — the gate's MCP currency probe —
                     so refusal must not veto a commit; the caller skips and passes

The environment is read in exactly one place, here, held by effects.send_switch_read_once
in src/test/run.py. Two readings of one switch is how the polarity of `== '1'` and `!= '1'`
gets to disagree.
"""
import os

SWITCH = 'YOGA_NO_SEND'


class SendRefused(RuntimeError):
    """Raised in place of an outward call when YOGA_NO_SEND=1, naming the send refused.

    The sentence is composed here, once, so no raise site can word the refusal
    differently and every catcher can print the exception unadorned."""

    def __init__(self, what):
        super().__init__(f'{SWITCH}=1 refuses this send: {what}')


def may_send():
    """Whether outward calls are permitted at all. The only reading of the environment."""
    return os.environ.get(SWITCH) != '1'


def assert_may_send(what):
    """Refuse loudly, for a send that IS the work. `what` names the call being refused."""
    if not may_send():
        raise SendRefused(what)
