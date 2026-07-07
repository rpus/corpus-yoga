#!/usr/bin/env python
"""
agent.py — transport an AGENT (session × memory) between machines.

The calculus (rsc/CALCULUS.md): an agent is the product session × memory;
transport is identity-preserving cp, componentwise, with each component's
class semantics enforced. A session is append-only, so a copy supersedes an
existing one iff the existing bytes are a PREFIX of it; anything else is a
loud CONFLICT. A memory folder is a set of one-fact-per-file documents whose
NAMES are dressing (the fact is the identity) plus one index: on receive a
novel leaf copies in, an identical one skips, one the incoming EXTENDS is
superseded in place (an appendix), and true divergence keeps BOTH — the
incoming fact re-dressed as <stem>.<room>.md with its [[links]] following —
while MEMORY.md unions by novelty-append. Nothing is overwritten silently
(L6), nothing is lost (L4), and reconciliation of diverged facts remains a
human act — recorded in-folder rather than blocking the transport ("hone,
not clone": the twins are the fork, made visible). Re-running either
direction on an unchanged pair is silence (L1).

Rooms: --to/--from take a directory path, or a bare room name resolved as
ext/agents/<room> — a hand-made symlink (the ext/ convention) to whatever
medium the machines share. The projects root is ext/code-projects (PREP.sh's
symlink to the Claude Code projects folder), so both ends stay repo-relative
and the bundle mirrors the projects layout exactly:
<project-key>/<session>.jsonl + <project-key>/memory/.

Received merges are DETECTABLE and INVERTIBLE: a receive that changes the
memory writes a marker block into MEMORY.md — begin/end comments wrapping the
unioned index lines, plus one act line per file action with content hash and
lengths — and `demerge` undoes the LATEST block exactly (delete the additions,
truncate the appendices, drop the block), all-or-nothing, refusing loudly if
anything was edited since the merge: the record licenses the undo (L3). This
is what makes safe VISITS possible — an agent received while the host is away
extracts by transporting itself home, and the host demerges the residue.

    ./yoga agent transport --to <room-or-dir> [--session <uuid8>]
    ./yoga agent receive --from <room-or-dir> [--apply]
    ./yoga agent demerge [--apply]

transport writes to the handoff medium immediately (it is not precious).
receive and demerge are dry-run by default and only --apply writes into this
machine's projects root — that is harness-owned state. Exit 1 on any CONFLICT.
"""
import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / 'ext' / 'code-projects'
ROOMS = REPO / 'ext' / 'agents'


def project_key() -> str:
    """The Claude Code projects key for THIS repo: its absolute path with
    '/' → '-' (the leading '/' becomes the leading '-')."""
    return str(REPO).replace('/', '-')


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _sha_lines(text: str) -> str:
    """Line-canonical hash (trailing-newline-insensitive) — used where the
    hashed content is reconstructed from splitlines at demerge time."""
    return _sha('\n'.join(text.splitlines()))


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


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, room: str | None) -> int:
    """Memory-folder merge. A leaf file's NAME is dressing; the fact is the
    identity — so per leaf: absent → copy (novelty); identical → skip; the
    incoming extends the local (byte-prefix) → superseded in place (an
    appendix); true divergence → BOTH kept, the incoming fact re-dressed as
    <stem>.<room>.md with its [[links]] following (nothing lost, nothing
    silently overwritten, nothing blocking — reconciliation stays a human act,
    recorded in-folder). MEMORY.md is the index, not a fact: it unions by
    novelty-append, with lines for re-dressed facts rewritten to their new
    names. Without a room name (transport into a handoff) divergence is a
    blocking CONFLICT instead — a bundle should be one agent's memory, and a
    divergent bundle usually means: receive first. Returns the conflict count."""
    conflicts = 0
    if not src_dir.is_dir():
        print('  memory: none at source')
        return 0

    def dressed(text: str, renames: dict[str, str]) -> str:
        for old, new in renames.items():
            text = text.replace(f'[[{old}]]', f'[[{new}]]')
        return text

    leaves = [(p.relative_to(src_dir), p.read_text())
              for p in sorted(src_dir.rglob('*'))
              if p.is_file() and p.name not in ('.DS_Store', 'MEMORY.md')]

    # Settle the rename map by fixpoint BEFORE acting: a leaf is compared in its
    # INSTALLED form (links already re-dressed), so a file that differs from its
    # local copy only because a linked fact was re-dressed is identical, not
    # diverged — which is what makes re-receiving the same bundle silence (L1).
    renamed: dict[str, str] = {}
    for _ in range(5):
        next_map: dict[str, str] = {}
        for rel, raw in leaves:
            target = dest_dir / rel
            if room is None or not target.exists():
                continue
            form, have = dressed(raw, renamed), target.read_text()
            if form != have and not form.startswith(have) and not have.startswith(form):
                next_map[target.stem] = f'{target.stem}.{room}'
        if next_map == renamed:
            break
        renamed = next_map

    acts: list[str] = []  # merge-marker act lines (receive only): the undo record
    for rel, raw in leaves:
        target = dest_dir / rel
        form = dressed(raw, renamed)
        if not target.exists():
            print(f'  memory/{rel}: new')
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(form)
            if room is not None:
                acts.append(f'<!-- merge:act new {rel} sha={_sha(form)} len={len(form)} -->')
            continue
        have = target.read_text()
        if have == form:
            print(f'  memory/{rel}: identical — no-op')
        elif form.startswith(have):
            print(f'  memory/{rel}: extends it — superseded (appendix)')
            if apply:
                target.write_text(form)
            if room is not None:
                acts.append(f'<!-- merge:act appendix {rel} prior={len(have)} '
                            f'post={len(form)} sha={_sha(form)} -->')
        elif have.startswith(form):
            print(f'  memory/{rel}: destination is ahead — no-op')
        elif room is None:
            print(f'  memory/{rel}: ✗ CONFLICT: diverged — left in place (receive before transporting?)')
            conflicts += 1
        else:
            twin = target.with_name(f'{renamed[target.stem]}{target.suffix}')
            twin_rel = rel.with_name(twin.name)
            if twin.exists() and twin.read_text() == form:
                print(f'  memory/{rel}: diverged twin already installed as {twin.name} — no-op')
            elif twin.exists():
                print(f'  memory/{rel}: ✗ CONFLICT: diverged AND its twin {twin.name} differs — left in place')
                conflicts += 1
            else:
                print(f'  memory/{rel}: diverged — both kept; incoming installed as {twin.name}')
                if apply:
                    twin.write_text(form)
                acts.append(f'<!-- merge:act new {twin_rel} sha={_sha(form)} len={len(form)} -->')
    # MEMORY.md: the index unions by novelty-append, re-dressed lines rewritten
    src_index = src_dir / 'MEMORY.md'
    dest_index = dest_dir / 'MEMORY.md'
    novel: list[str] = []
    if src_index.exists():
        have_lines = dest_index.read_text().splitlines() if dest_index.exists() else []
        # A merge record is a fact about ITS OWN folder and never travels: the
        # source's marker machinery is dropped; the plain index lines inside its
        # blocks (real entries) union like any others.
        src_lines = [l for l in src_index.read_text().splitlines()
                     if not l.lstrip().startswith('<!-- merge:')]
        for line in src_lines:
            for old, new in renamed.items():
                line = line.replace(f'({old}.md)', f'({new}.md)').replace(f'[[{old}]]', f'[[{new}]]')
            if line.strip() and line not in have_lines:
                novel.append(line)
        if not dest_index.exists():
            filtered = '\n'.join(src_lines) + ('\n' if src_lines else '')
            print('  memory/MEMORY.md: new')
            if apply:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_index.write_text(filtered)
            if room is not None:
                acts.append(f'<!-- merge:act index-new sha={_sha_lines(filtered)} -->')
            novel = []  # the whole index arrived; no separate union lines
        elif novel:
            print(f'  memory/MEMORY.md: index unioned — {len(novel)} line(s) appended'
                  + (' (inside the merge marker)' if room is not None else ''))
            if apply and room is None:
                dest_index.write_text('\n'.join(have_lines + novel) + '\n')
        else:
            print('  memory/MEMORY.md: index already covers it — no-op')
    # the merge marker: begin/end comments wrapping the unioned lines, then the
    # acts — MEMORY.md carries the record that makes this merge demergeable
    if room is not None and (acts or novel):
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
        block = [f'<!-- merge:begin {stamp} from={room} -->', *novel, *acts, '<!-- merge:end -->']
        print(('  memory/MEMORY.md: merge marker recorded' if apply else
               '  memory/MEMORY.md: would record merge marker')
              + f' ({len(acts)} act(s); undo via: agent demerge)')
        if apply:
            cur = dest_index.read_text() if dest_index.exists() else ''
            if cur and not cur.endswith('\n'):
                cur += '\n'
            dest_index.write_text(cur + '\n'.join(block) + '\n')
    return conflicts


def demerge(proj_dir: Path, apply: bool) -> int:
    """Undo the LATEST merge recorded in MEMORY.md, exactly and all-or-nothing:
    delete the recorded additions (novelties, twins), truncate the recorded
    appendices to their pre-merge lengths, drop the marker block (with the
    unioned index lines inside it). Every act is verified against its recorded
    hash first — anything edited since the merge is a CONFLICT and NOTHING is
    undone (L6): the record licenses the undo (L3), and a stale record licenses
    nothing. Repeated demerges peel the record stack newest-first (L1: a folder
    with no markers demerges to silence). Session .jsonl files are visit
    residue this never touches — transport the visitor home, then remove its
    session deliberately."""
    mem = proj_dir / 'memory'
    idx = mem / 'MEMORY.md'
    if not idx.exists():
        print('no MEMORY.md — nothing to demerge')
        return 0
    lines = idx.read_text().splitlines()
    begins = [i for i, l in enumerate(lines) if l.startswith('<!-- merge:begin ')]
    if not begins:
        print('no merge markers in MEMORY.md — nothing to demerge')
        return 0
    b = begins[-1]
    e = next((i for i in range(b + 1, len(lines)) if lines[i] == '<!-- merge:end -->'), None)
    if e is None:
        sys.exit('error: unterminated merge block in MEMORY.md — repair by hand')
    print(f'demerge (latest of {len(begins)} record(s)): '
          + lines[b].removeprefix('<!-- merge:begin ').removesuffix(' -->'))
    remaining = lines[:b] + lines[e + 1:]
    conflicts = 0
    index_new = False
    ops: list[tuple[str, Path, int]] = []
    for l in lines[b + 1:e]:
        if not l.startswith('<!-- merge:act '):
            continue
        parts = l.removeprefix('<!-- merge:act ').removesuffix(' -->').split()
        kind = parts[0]
        kv = dict(p.split('=', 1) for p in parts[1:] if '=' in p)
        if kind == 'new':
            rel, f = parts[1], mem / parts[1]
            if not f.exists():
                print(f'  {rel}: already gone — no-op')
            elif _sha(f.read_text()) != kv['sha']:
                print(f'  {rel}: ✗ CONFLICT: edited since the merge — refusing')
                conflicts += 1
            else:
                print(f'  {rel}: remove')
                ops.append(('rm', f, 0))
        elif kind == 'appendix':
            rel, f = parts[1], mem / parts[1]
            prior, post = int(kv['prior']), int(kv['post'])
            cur = f.read_text() if f.exists() else None
            if cur is not None and len(cur) == post and _sha(cur) == kv['sha']:
                print(f'  {rel}: truncate to pre-merge length ({post} → {prior})')
                ops.append(('trunc', f, prior))
            elif cur is not None and len(cur) > post and _sha(cur[:post]) == kv['sha']:
                print(f'  {rel}: ✗ CONFLICT: appended to since the merge — refusing')
                conflicts += 1
            else:
                print(f'  {rel}: ✗ CONFLICT: '
                      + ('missing' if cur is None else 'edited since the merge') + ' — refusing')
                conflicts += 1
        elif kind == 'index-new':
            if _sha('\n'.join(remaining)) != kv['sha']:
                print('  MEMORY.md: ✗ CONFLICT: index edited since the merge — refusing')
                conflicts += 1
            else:
                print('  MEMORY.md: remove (the whole index arrived with this merge)')
                index_new = True
    if conflicts:
        print(f'{conflicts} conflict(s) — NOTHING undone (all-or-nothing; reconcile by hand, or accept the merge)')
        return conflicts
    if apply:
        for kind, f, n in ops:
            if kind == 'rm':
                f.unlink()
            else:
                f.write_text(f.read_text()[:n])
        if index_new:
            idx.unlink()
        else:
            idx.write_text('\n'.join(remaining) + ('\n' if remaining else ''))
    print('note: session .jsonl files are visit residue demerge does not touch')
    print('APPLIED' if apply else 'dry run — pass --apply to undo the merge')
    return 0


def move(src_proj: Path, dest_proj: Path, session: Path, apply: bool, label: str,
         room: str | None = None) -> int:
    print(f'{label}: {session.name}')
    status, conflicts = place_session(session, dest_proj / session.name, apply)
    print(f'  session: {status}')
    conflicts += merge_memory(src_proj / 'memory', dest_proj / 'memory', apply, room)
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
    d = sub.add_parser('demerge', help='undo the latest received merge (memory only, all-or-nothing)')
    d.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not PROJECTS.is_dir():
        sys.exit(f'error: {PROJECTS.relative_to(REPO)} missing — src/main/code-projects/PREP.sh creates the symlink')
    key = project_key()

    if args.direction == 'demerge':
        return 1 if demerge(PROJECTS / key, args.apply) else 0

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
    # the twin-dressing label for diverged facts: the room name as given, or the
    # directory's own name when --from was a path
    room = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in Path(args.source).name) or 'incoming'
    return 1 if move(src_proj, PROJECTS / key, session, args.apply,
                     label=f'receive ← {args.source}', room=room) else 0


if __name__ == '__main__':
    sys.exit(main())
