#!/usr/bin/env python
"""
provider.py - the provider registry (rsc/provider/providers.csv). A LIBRARY, not a
command: nothing here reports. `corpus-yoga prerequisites` is the voice that says what
this machine has of each provider.

One fact: providers(), the declared providers in registry order, each row as its
columns - provider, session_env_var, live_store, mount_name, bot_author_pattern,
note. A row states what was observed; an empty column is "not observed", and a
reader treats it as absent, never guesses.

The sibling of machine.py: a machine is an identity and so is a provider;
rsc/provider/README.md states the registry's one rule. STDLIB-ONLY,
like machine.py and cli.py: importable on a fresh clone before the venv exists, and
by the commit hook's readers.
"""
import csv
from pathlib import Path

SELF = 'src/main/provider.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
REGISTRY = REPO / 'rsc' / 'provider' / 'providers.csv'


def providers() -> list[dict[str, str]]:
    """The declared providers, in registry order."""
    with REGISTRY.open(newline='') as f:
        return [r for r in csv.DictReader(f) if r['provider'].strip()]


def provider_names() -> list[str]:
    return [r['provider'] for r in providers()]


def provider(name: str) -> dict[str, str]:
    """One declared provider's row - refused when the registry does not declare it."""
    for r in providers():
        if r['provider'] == name:
            return r
    raise KeyError(f'{name!r} is not a declared provider - declare it in '
                   f'{REGISTRY.relative_to(REPO)}; declared: {", ".join(provider_names())}')


def live_store(row: dict[str, str]) -> Path | None:
    """The harness's live session store on this machine, or None where the row
    observes none."""
    return Path(row['live_store']).expanduser() if row['live_store'] else None


def mount(row: dict[str, str]) -> Path | None:
    """The by-reference mount of the live store under ext/mnt/, or None."""
    return REPO / 'ext' / 'mnt' / row['mount_name'] if row['mount_name'] else None
