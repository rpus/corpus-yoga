#!/usr/bin/env python
"""
provider.py - the provider registry (rsc/provider/providers.csv). A LIBRARY, not a
command: nothing here reports. `corpus-yoga prerequisites` is the voice that says what
this machine has of each provider.

One fact: providers(), the declared providers in registry order, each row as its
columns - provider, session_env_var, live_store, bot_author_pattern, note. A row states what was observed; an empty column is "not observed", and a
reader treats it as absent, never guesses.

The sibling of machine.py: a machine is an identity and so is a provider;
rsc/provider/README.md states the registry's one rule. STDLIB-ONLY,
like machine.py and cli.py: importable on a fresh clone before the venv exists. The
shell readers (the commit hook, the mount script, the machine report) take lines()
through src/run_python_script.sh, the venv's python (#478), so the csv grammar is
read in one place.
"""
import csv
from pathlib import Path

SELF = 'src/main/provider.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
REGISTRY = REPO / 'rsc' / 'provider' / 'providers.csv'
COLUMNS = ('provider', 'session_env_var', 'live_store', 'bot_author_pattern', 'note')
SEPARATOR = '\x1f'   # the ASCII unit separator: not whitespace, so `IFS=$'\x1f' read -r` keeps an empty field


def providers() -> list[dict[str, str]]:
    """The declared providers, in registry order."""
    with REGISTRY.open(newline='') as f:
        return [r for r in csv.DictReader(f) if r['provider'].strip()]


def lines() -> str:
    """The rows for a shell reader: one row per line, the fields in COLUMNS order joined
    by SEPARATOR. The csv grammar is read here and nowhere else, so a field may hold a
    comma or a quote; a field holding the separator or a newline is refused, since the
    shell reader could not tell it from the row's shape."""
    rows = []
    for r in providers():
        fields = [r[c] for c in COLUMNS]
        bad = [c for c, f in zip(COLUMNS, fields) if SEPARATOR in f or '\n' in f]
        if bad:
            raise ValueError(f'{REGISTRY.relative_to(REPO)}: {r["provider"]}: {", ".join(bad)} holds a separator or a newline')
        rows.append(SEPARATOR.join(fields))
    return '\n'.join(rows)


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


MOUNT_ROOT = REPO / 'ext' / 'mnt' / 'agent'
MOUNT_VINTAGES = REPO / 'rsc' / 'naming' / 'mount_vintages.csv'


def retired_mounts() -> list[tuple[str, str]]:
    """Every link this machine holds at a retired mount address: (repo-relative path,
    vintage id), per the legacy rows of rsc/naming/mount_vintages.csv. Named for the
    reader; nothing here removes one."""
    import re
    with MOUNT_VINTAGES.open(newline='') as f:
        legacy = [(r['id'], re.compile(r['pattern'])) for r in csv.DictReader(f) if r['status'] == 'legacy']
    ext = REPO / 'ext'
    found = []
    for base in (ext, ext / 'mnt'):
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            rel = str(path.relative_to(REPO))
            for vintage_id, pattern in legacy:
                if path.is_symlink() and pattern.match(rel):
                    found.append((rel, vintage_id))
    return found


def mount(row: dict[str, str]) -> Path | None:
    """The by-reference mount of the live store, ext/mnt/agent/<provider> (#636) -
    the provider name is the only segment the repository adds - or None where the
    row observes no live store."""
    return MOUNT_ROOT / row['provider'] if row['live_store'] else None
