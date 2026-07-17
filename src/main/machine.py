#!/usr/bin/env python
"""
machine.py — the machine registry and this machine's binding to it. A LIBRARY,
not a command: nothing here reports. `./yoga prerequisites` is the one machine
voice, and it says everything this ever said, in more detail.

Two facts, and only two:

  machines()       the declared machines (rsc/machine/machines.csv) — the registry.
  bound_machine()  which one this is, from the one-line self.txt binding beside it,
                   REFUSED unless the registry declares it.

That refusal is the whole point, and it guards exactly one write: agent.py keys the
shared transport store by this name (input/claude/code/machine-transport/<machine>/),
so a typo'd binding would mint a phantom machine in a store BOTH machines see. The
gate lives here, in the one reader, so every consumer inherits it. Declare a machine
in the registry first, then bind to it — never the other way round.

The binding is the one gitignored file in the committed tree: a machine names ITSELF,
and that name is never shared, never transported (user placement, 2026-07-08). Its
path is built by arithmetic so no committed literal names a file that rightly does
not exist on a fresh clone — the same law the registry itself serves.

There is no per-machine manifest and no layering: machines do not diverge. What a
machine may or may not have is expressed by PREREQUISITES as optional, not by giving
each machine its own list. A machine is an IDENTITY, not a configuration variant.

STDLIB-ONLY, like cli.py: importable on a fresh clone before the venv exists.
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY_DIR = REPO / 'rsc' / 'machine'
REGISTRY = REGISTRY_DIR / 'machines.csv'
BINDING = REGISTRY_DIR / 'self.txt'


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
