#!/usr/bin/env python
"""
machine.py — verify THIS machine against its room's manifest.

Manifests are docker-style desired state as committed data (rsc/machines/:
_base.csv layered under <room>.csv — format: rsc/machines/README.md); the
machine's identity is the one-line gitignored binding ext/machine; the report
is strictly machine-local (L2). An unbound machine is told how to bind (L8).

    ./yoga machine                  # verify against the bound room
    ./yoga machine --room <name>    # verify against a named room

STDLIB-ONLY, like cli.py: works on a fresh clone before the venv exists.
Exit 1 iff a required item is absent.
"""
import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFESTS = REPO / 'rsc' / 'machines'
BINDING = REPO / 'ext' / 'machine'


def rooms() -> list[str]:
    return sorted(p.stem for p in MANIFESTS.glob('*.csv') if p.stem != '_base')


def bound_room() -> str:
    if not BINDING.exists():
        sys.exit(f'unbound machine — name its room in a one-line ext/machine file, e.g.:\n'
                 f'    echo {rooms()[0] if rooms() else "<room>"} > ext/machine\n'
                 f'rooms declared in rsc/machines/: {", ".join(rooms()) or "(none)"}')
    return BINDING.read_text().strip()


def manifest(room: str) -> list[dict]:
    """_base.csv layered under the room's own rows (the docker FROM analogy)."""
    room_csv = MANIFESTS / f'{room}.csv'
    if not room_csv.exists():
        sys.exit(f"error: no manifest rsc/machines/{room}.csv — rooms: {', '.join(rooms())}")
    rows: list[dict] = []
    for f in (MANIFESTS / '_base.csv', room_csv):
        with f.open() as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def probe(kind: str, arg: str) -> bool:
    if kind == 'cmd':
        return shutil.which(arg) is not None
    if kind == 'env':
        return bool(os.environ.get(arg))
    if kind == 'path':
        return (REPO / arg).exists()
    if kind == 'grep':
        file_part, _, pattern = arg.partition(' ')
        f = Path(file_part).expanduser()
        return f.is_file() and pattern in f.read_text()
    sys.exit(f'error: unknown manifest kind {kind!r} (see rsc/machines/README.md)')


def checks(room: str) -> list[tuple[str, bool, str, str]]:
    """[(label, present, level, note)] for the room's layered manifest."""
    return [(f'{r["kind"]}: {r["arg"]}', probe(r['kind'], r['arg']), r['level'], r['note'])
            for r in manifest(room)]


def main() -> int:
    ap = argparse.ArgumentParser(description='verify this machine against its room manifest')
    ap.add_argument('--room', help='manifest to verify against (default: the ext/machine binding)')
    args = ap.parse_args()
    room = args.room or bound_room()
    print(f'machine manifest: {room} (rsc/machines, _base layered first)')
    missing_required = 0
    for label, present, level, note in checks(room):
        if present:
            print(f'  ✓ {label}')
        elif level == 'optional':
            print(f'  – {label} — {note}')
        else:
            print(f'  ✗ {label} — {note}')
            missing_required += 1
    if missing_required:
        print(f'{missing_required} required item(s) absent — the notes above say how to satisfy each')
    return 1 if missing_required else 0


if __name__ == '__main__':
    sys.exit(main())
