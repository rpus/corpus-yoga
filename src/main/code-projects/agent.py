#!/usr/bin/env python
"""
agent.py — transport an AGENT (session × memory) between machines.

The calculus (rsc/CALCULUS.md): an agent is the product session × memory;
transport is identity-preserving cp, componentwise, with each component's
class semantics enforced. A session is append-only, so a copy supersedes an
existing one iff the existing bytes are a PREFIX of it; anything else is a
loud CONFLICT. An agent's memory folder is a set of mutable documents:
absent → copy, byte-identical → skip, divergent → loud CONFLICT left in
place — a forked agent is two agents thereafter ("hone, not clone"), so no
overwrite is ever silent (L6). Re-running either direction on an unchanged
pair is silence (L1).

Rooms: --to/--from take a directory path, or a bare room name resolved as
ext/agents/<room> — a hand-made symlink (the ext/ convention) to whatever
medium the machines share. The projects root is ext/code-projects (PREP.sh's
symlink to the Claude Code projects folder), so both ends stay repo-relative
and the bundle mirrors the projects layout exactly:
<project-key>/<session>.jsonl + <project-key>/memory/.

    ./yoga agent transport --to <room-or-dir> [--session <uuid8>]
    ./yoga agent receive --from <room-or-dir> [--apply]

transport writes to the handoff medium immediately (it is not precious).
receive is dry-run by default and only --apply writes into this machine's
projects root — that is harness-owned state. Exit 1 on any CONFLICT.
"""
import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / 'ext' / 'code-projects'
ROOMS = REPO / 'ext' / 'agents'


def project_key() -> str:
    """The Claude Code projects key for THIS repo: its absolute path with
    '/' → '-' (the leading '/' becomes the leading '-')."""
    return str(REPO).replace('/', '-')


def resolve_room(name: str, writing: bool) -> Path:
    """A destination/source directory: a path as given, or a registered room
    (ext/agents/<name>, normally a hand-made symlink to the shared medium)."""
    p = Path(name).expanduser()
    if '/' in name or p.is_dir():
        if writing:
            p.mkdir(parents=True, exist_ok=True)
        return p
    room = ROOMS / name
    if not room.is_dir():
        sys.exit(f"error: room '{name}' is not registered — create ext/agents/{name} "
                 '(a directory, or a symlink to the medium this room shares with it)')
    return room


def pick_session(proj_dir: Path, uuid8: str | None) -> Path:
    """The session to move: --session's uuid prefix match, else newest .jsonl."""
    sessions = sorted(proj_dir.glob('*.jsonl'))
    if uuid8:
        sessions = [s for s in sessions if s.stem.startswith(uuid8)]
    if not sessions:
        sys.exit(f'error: no matching session .jsonl in {proj_dir}')
    return max(sessions, key=lambda s: s.stat().st_mtime)


def place_session(src: Path, dest: Path, apply: bool) -> tuple[str, int]:
    """Append-only placement: new, identical, prefix-superseded, or CONFLICT.
    Returns (status, conflicts)."""
    data = src.read_bytes()
    if not dest.exists():
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        return 'new', 0
    have = dest.read_bytes()
    if have == data:
        return 'identical — no-op', 0
    if data[:len(have)] == have:
        if apply:
            dest.write_bytes(data)
        return f'extends it ({len(have)} → {len(data)} bytes) — superseded', 0
    if have[:len(data)] == data:
        return 'destination is ahead — no-op', 0
    return '✗ CONFLICT: diverged — left in place', 1


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool) -> int:
    """Mutable-document merge, per file: absent → copy, identical → skip,
    divergent → loud CONFLICT left in place. Returns the conflict count."""
    conflicts = 0
    if not src_dir.is_dir():
        print('  memory: none at source')
        return 0
    for f in sorted(p for p in src_dir.rglob('*') if p.is_file() and p.name != '.DS_Store'):
        rel = f.relative_to(src_dir)
        target = dest_dir / rel
        if not target.exists():
            print(f'  memory/{rel}: new')
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
        elif target.read_bytes() == f.read_bytes():
            print(f'  memory/{rel}: identical — no-op')
        else:
            print(f'  memory/{rel}: ✗ CONFLICT: diverged — left in place (two agents now; merge is a human decision)')
            conflicts += 1
    return conflicts


def move(src_proj: Path, dest_proj: Path, session: Path, apply: bool, label: str) -> int:
    print(f'{label}: {session.name}')
    status, conflicts = place_session(session, dest_proj / session.name, apply)
    print(f'  session: {status}')
    conflicts += merge_memory(src_proj / 'memory', dest_proj / 'memory', apply)
    print('APPLIED' if apply else 'dry run — pass --apply to write into the projects root')
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser(description='transport an agent (session × memory) between machines')
    sub = ap.add_subparsers(dest='direction', required=True)
    t = sub.add_parser('transport', help='write the agent bundle to a room/handoff dir')
    t.add_argument('--to', required=True, help='room name (ext/agents/<room>) or directory')
    t.add_argument('--session', help='uuid(8) prefix; default: newest session')
    r = sub.add_parser('receive', help='install an agent bundle from a room/handoff dir')
    r.add_argument('--from', dest='source', required=True, help='room name or directory')
    r.add_argument('--session', help='uuid(8) prefix; default: newest session in the bundle')
    r.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not PROJECTS.is_dir():
        sys.exit(f'error: {PROJECTS.relative_to(REPO)} missing — src/main/code-projects/PREP.sh creates the symlink')
    key = project_key()

    if args.direction == 'transport':
        dest = resolve_room(args.to, writing=True)
        src_proj = PROJECTS / key
        session = pick_session(src_proj, args.session)
        return 1 if move(src_proj, dest / key, session, apply=True, label=f'transport → {args.to}') else 0

    src = resolve_room(args.source, writing=False)
    src_proj = src / key
    if not src_proj.is_dir():
        sys.exit(f'error: no {key} bundle under {src}')
    session = pick_session(src_proj, args.session)
    return 1 if move(src_proj, PROJECTS / key, session, args.apply, label=f'receive ← {args.source}') else 0


if __name__ == '__main__':
    sys.exit(main())
