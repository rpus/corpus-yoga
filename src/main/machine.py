#!/usr/bin/env python
"""
machine.py — the machine registry and this machine's binding to it. A LIBRARY,
not a command: nothing here reports. `./yoga prerequisites` is the one machine
voice, and it says everything this ever said, in more detail.

Two facts, and only two:

  machines()       the declared machines (rsc/machine/machines.csv) — the registry.
  bound_machine()  which one this is, from the one-line machine-name.txt binding
                   at the repo root, REFUSED unless the registry declares it.

That refusal is the whole point, and it guards exactly one write: agent.py keys the
shared transport store by this name (data/input/claude/code/machine-transport/<machine>/),
so a typo'd binding would mint a phantom machine in a store BOTH machines see. The
gate lives here, in the one reader, so every consumer inherits it. Declare a machine
in the registry first, then bind to it — never the other way round.

The two live apart because they are opposites. The registry is shared: every clone
carries the same machines.csv. The binding is the machine naming ITSELF, and that
name is never shared, never transported — so it sits at the repo root among the
other machine-local entries (tmp/cache/, data/input/, tmp/logs/, data/output/), gitignored, and
rsc/machine/ is left wholly committed. Until 2026-07-17 the binding lived INSIDE
rsc/machine/, the one gitignored file in the committed tree, and that single
exception cost more than it was worth: its path had to be built by arithmetic and
never spelled whole, because a committed literal naming it read as a reference to
a file that exists only on bound machines. Rooted, it is spelled outright here —
its own .gitignore rule is what makes that safe.

There is no per-machine manifest and no layering: machines do not diverge. What a
machine may or may not have is expressed by PREREQUISITES as optional, not by giving
each machine its own list. A machine is an IDENTITY, not a configuration variant.

STDLIB-ONLY, like cli.py: importable on a fresh clone before the venv exists.
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / 'rsc' / 'machine' / 'machines.csv'
BINDING = REPO / 'machine-name.txt'


def machines() -> list[str]:
    """The declared machines, in registry order."""
    with REGISTRY.open() as f:
        return [r['machine'].strip() for r in csv.DictReader(f) if r['machine'].strip()]


def bound_machine() -> str:
    """This machine's name — refused unless the registry declares it."""
    rel = BINDING.relative_to(REPO)
    declared = machines()
    if not BINDING.exists():
        # A constant placeholder, deliberately never a real machine's name: an
        # example a new machine could paste verbatim would mint an identity collision.
        sys.exit(f'unbound machine — name it in the one-line {rel} binding:\n'
                 f'    echo <unique-machine-name> > {rel}\n'
                 f'machines declared in {REGISTRY.relative_to(REPO)}: '
                 f'{", ".join(declared) or "(none)"}')
    name = BINDING.read_text().strip()
    if name not in declared:
        sys.exit(f"bound to '{name}' but the registry does not declare it — add it to "
                 f'{REGISTRY.relative_to(REPO)}, or fix the {rel} binding; '
                 f'declared: {", ".join(declared) or "(none)"}')
    return name
