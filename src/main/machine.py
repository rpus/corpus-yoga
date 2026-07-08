#!/usr/bin/env python
"""
machine.py — verify THIS machine against its room's manifest.

Manifests are docker-style desired state as committed data (rsc/machines/:
_base.csv layered under <room>.csv — format: rsc/machines/README.md); the
machine's identity is the one-line self.txt binding beside the manifests in
rsc/machines/ (the one gitignored file in the committed tree); the report
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
# The binding lives BESIDE the manifests it selects among — the one gitignored
# file in the committed tree, because the room is the machine's own name for
# itself: the anti-Mergeable, never shared, never transported (user placement,
# 2026-07-08; path built by arithmetic so no committed literal names a file
# that rightly does not exist on a fresh clone).
BINDING = MANIFESTS / 'self.txt'


def rooms() -> list[str]:
    return sorted(p.stem for p in MANIFESTS.glob('*.csv') if p.stem != '_base')


def bound_room() -> str:
    rel = BINDING.relative_to(REPO)
    if not BINDING.exists():
        # constant placeholder, deliberately never an existing room's name: an
        # example a new machine could paste verbatim would mint an identity
        # collision — the placeholder's own spelling carries the requirement
        sys.exit(f'unbound machine — name its room in the one-line {rel} binding:\n'
                 f'    echo <unique-room-name> > {rel}\n'
                 f'rooms already declared in rsc/machines/: {", ".join(rooms()) or "(none)"}')
    room = BINDING.read_text().strip()
    if room not in rooms():
        # declaredness gate, here in the ONE reader so every consumer inherits
        # it — above all transport, which would otherwise mint a phantom room
        # dir in the shared hall from a typo. Bootstrap order per the machines
        # README: a new room is a manifest PLUS a binding, declare then bind.
        sys.exit(f"bound to '{room}' but no manifest declares it — declare "
                 f'rsc/machines/{room}.csv, or fix the {rel} binding; '
                 f'rooms declared: {", ".join(rooms()) or "(none)"}')
    return room


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
    ap.add_argument('--room', help='manifest to verify against (default: the self.txt binding)')
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
