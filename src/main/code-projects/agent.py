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

Rooms: bundles live in a shared ARRIVALS HALL — ext/agents, a hand-made
symlink on each machine to the same medium — each bundle FLAT under its
ORIGIN room's name: <room>/<session>.jsonl + <room>/<session-uuid>/ (the
eponymous workspace: subagent transcripts and persisted tool-results the log
REFERENCES, moved with log semantics per file) + <room>/memory/. Provenance
is spatial and sender-declared: transport takes no destination — it mirrors
the agent into ext/agents/<own room>, the room read from the ext/machine
binding (rsc/machines/) — and receive --from names the peer room whose bundle
to merge, the twin-dressing and marker label coming from that ADDRESS rather
than the receiver's assertion. An outbox is single-writer by construction, so
transport MIRRORS its memory (updated in place, absentees removed); every
merge subtlety lives in receive, where two agents actually meet. The projects
root is ext/code-projects (PREP.sh's symlink to the Claude Code projects
folder), so both ends stay repo-relative.

Received merges are DETECTABLE and INVERTIBLE: a receive that changes the
memory writes a marker block into MEMORY.md — begin/end comments wrapping the
unioned index lines, plus one act line per file action with content hash and
lengths — and `demerge` undoes the LATEST block exactly (delete the additions,
truncate the appendices, drop the block), all-or-nothing, refusing loudly if
anything was edited since the merge: the record licenses the undo (L3). This
is what makes safe VISITS possible — an agent received while the host is away
extracts by transporting itself home, and the host demerges the residue.

    ./yoga agent transport --session <uuid8> [--to <dir>]
    ./yoga agent receive --from <room> --session <uuid8> [--apply]
    ./yoga agent demerge [--apply]

--session is MANDATORY and matches by uuid prefix, exactly one: which agent
moves is never the tool's call — no recency guessing, no automatic choice.
--to is a directory override for scratch and tests only.

transport writes to the handoff medium immediately (it is not precious).
receive and demerge are dry-run by default and only --apply writes into this
machine's projects root — that is harness-owned state. Exit 1 on any CONFLICT.

Field note (2026-07-07, first scripted teleport): a received agent that does
not appear in the VSCode sidebar was probably trash-buttoned there once — the
extension tombstones session uuids in `hiddenSessionIds` (its globalState in
the machine's state.vscdb), machine-globally and with no unhide affordance;
purge that list with VSCode quit, or resume via the terminal CLI, which does
not consult it. The listing's other lie is the mirror image: it counts a
session's eponymous guid-dir (via its subagents/) as a session even after the
.jsonl is deleted — so the correct on-disk deletion rite is BOTH the .jsonl
AND its guid-dir together; delete only the file and the sidebar advertises a
ghost, whose only offered remedy is the tombstone that started this note.
"""
import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / 'ext' / 'code-projects'
HALL = REPO / 'ext' / 'agents'

sys.path.insert(0, str(REPO / 'src' / 'main'))  # machine.py owns the room binding
from machine import bound_room  # noqa: E402


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


def own_outbox() -> Path:
    """The hall directory this machine writes: ext/agents/<its ext/machine
    binding>. The hall itself is hand-made; the outbox inside it is ours."""
    if not HALL.is_dir():
        sys.exit('error: ext/agents missing — hand-make it as a symlink to the '
                 'shared arrivals hall (bundles live there under origin-room names)')
    out = HALL / bound_room()
    out.mkdir(exist_ok=True)
    return out


def peer_bundle(name: str) -> Path:
    """A source for receive: a directory path as given, or ext/agents/<room> —
    the bundle that room last transported."""
    p = Path(name).expanduser()
    if '/' in name or p.is_dir():
        return p
    room = HALL / name
    if not room.is_dir():
        rooms = sorted(d.name for d in HALL.iterdir() if d.is_dir()) if HALL.is_dir() else []
        sys.exit(f"error: no bundle from room '{name}' in the arrivals hall — "
                 f"present: {', '.join(rooms) or '(none)'}")
    return room


def pick_session(proj_dir: Path, uuid8: str) -> Path:
    """The session to move, by IDENTITY: the --session uuid prefix must match
    exactly one .jsonl. No recency guessing, no automatic choice, ever —
    transport moves an agent, and which agent is never the tool's call."""
    matches = [s for s in sorted(proj_dir.glob('*.jsonl')) if s.stem.startswith(uuid8)]
    if not matches:
        sys.exit(f'error: no session matching {uuid8!r} in {proj_dir}')
    if len(matches) > 1:
        sys.exit(f'error: {uuid8!r} is ambiguous here — matches: '
                 + ', '.join(s.stem[:8] for s in matches))
    return matches[0]


def place_log(data: bytes, dest: Path, apply: bool) -> tuple[str, int]:
    """Append-only placement: new, identical, prefix-superseded, or CONFLICT.
    Returns (status, conflicts)."""
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


def place_session(src: Path, dest: Path, apply: bool) -> tuple[str, int]:
    return place_log(src.read_bytes(), dest, apply)


def move_workspace(src_ws: Path, dest_ws: Path, apply: bool) -> int:
    """The session's eponymous workspace (subagent transcripts, persisted
    tool-results — files the session log REFERENCES) rides along. The
    filesystem, checked here and now, is the only oracle — no reconstruction
    of what "ever existed": a destination folder that is absent takes the
    workspace wholesale as a unit; one that is present (however it came to be)
    merges with log semantics per file — new / identical / prefix-superseded;
    divergence a loud CONFLICT. Returns the conflict count."""
    if not src_ws.is_dir():
        return 0
    files = sorted(p for p in src_ws.rglob('*') if p.is_file() and p.name != '.DS_Store')
    if not dest_ws.exists():
        print(f'  workspace {src_ws.name}/: new ({len(files)} file(s))')
        if apply:
            for f in files:
                dest = dest_ws / f.relative_to(src_ws)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        return 0
    tally = {'new': 0, 'identical': 0, 'extends': 0, 'ahead': 0}
    conflicts = 0
    for f in files:
        rel = f.relative_to(src_ws)
        status, c = place_log(f.read_bytes(), dest_ws / rel, apply)
        if c:
            print(f'  workspace/{rel}: {status}')
            conflicts += c
        else:
            key = ('new' if status == 'new' else
                   'identical' if status.startswith('identical') else
                   'extends' if status.startswith('extends') else 'ahead')
            tally[key] += 1
    print(f'  workspace {src_ws.name}/: '
          + ', '.join(f'{n} {k}' for k, n in tally.items() if n)
          + (f', {conflicts} CONFLICT(S)' if conflicts else '')
          if any(tally.values()) or conflicts else
          f'  workspace {src_ws.name}/: empty')
    return conflicts


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, room: str) -> int:
    """Memory-folder merge — RECEIVE only, where two agents actually meet
    (transport mirrors its own outbox instead; see mirror_memory). A leaf
    file's NAME is dressing; the fact is the identity — so per leaf: absent →
    copy (novelty); identical → skip; the incoming extends the local
    (byte-prefix) → superseded in place (an appendix); true divergence → BOTH
    kept, the incoming fact re-dressed as <stem>.<room>.md — room is the
    bundle's ADDRESS in the hall, sender-declared — with its [[links]]
    following (nothing lost, nothing silently overwritten, nothing blocking —
    reconciliation stays a human act, recorded in-folder). MEMORY.md is the
    index, not a fact: it unions by novelty-append, with lines for re-dressed
    facts rewritten to their new names. Returns the conflict count."""
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
            if not target.exists():
                continue
            form, have = dressed(raw, renamed), target.read_text()
            if form != have and not form.startswith(have) and not have.startswith(form):
                next_map[target.stem] = f'{target.stem}.{room}'
        if next_map == renamed:
            break
        renamed = next_map

    acts: list[str] = []  # merge-marker act lines: the undo record
    for rel, raw in leaves:
        target = dest_dir / rel
        form = dressed(raw, renamed)
        if not target.exists():
            print(f'  memory/{rel}: new')
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(form)
            acts.append(f'<!-- merge:act new {rel} sha={_sha(form)} len={len(form)} -->')
            continue
        have = target.read_text()
        if have == form:
            print(f'  memory/{rel}: identical — no-op')
        elif form.startswith(have):
            print(f'  memory/{rel}: extends it — superseded (appendix)')
            if apply:
                target.write_text(form)
            acts.append(f'<!-- merge:act appendix {rel} prior={len(have)} '
                        f'post={len(form)} sha={_sha(form)} -->')
        elif have.startswith(form):
            print(f'  memory/{rel}: destination is ahead — no-op')
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
            acts.append(f'<!-- merge:act index-new sha={_sha_lines(filtered)} -->')
            novel = []  # the whole index arrived; no separate union lines
        elif novel:
            print(f'  memory/MEMORY.md: index unioned — {len(novel)} line(s) appended '
                  '(inside the merge marker)')
        else:
            print('  memory/MEMORY.md: index already covers it — no-op')
    # the merge marker: begin/end comments wrapping the unioned lines, then the
    # acts — MEMORY.md carries the record that makes this merge demergeable
    if acts or novel:
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
    print('note: session .jsonl files and their eponymous workspace dirs are '
          'visit residue demerge does not touch')
    print('APPLIED' if apply else 'dry run — pass --apply to undo the merge')
    return 0


def mirror_memory(src_dir: Path, dest_dir: Path) -> None:
    """Transport writes the agent's OWN outbox — single-writer by construction —
    so the memory folder is MIRRORED, not merged: the outbox is a faithful
    projection of the agent's current aggregate (new files added, changed ones
    updated in place, absentees removed). Every merge subtlety stays in
    receive, where two agents meet."""
    files = {p.relative_to(src_dir): p for p in sorted(src_dir.rglob('*'))
             if p.is_file() and p.name != '.DS_Store'} if src_dir.is_dir() else {}
    if not files:
        print('  memory: none at source')
        return
    have = {p.relative_to(dest_dir): p for p in sorted(dest_dir.rglob('*'))
            if p.is_file() and p.name != '.DS_Store'} if dest_dir.is_dir() else {}
    new = updated = same = removed = 0
    for rel, f in files.items():
        target = dest_dir / rel
        data = f.read_bytes()
        if rel not in have:
            new += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        elif have[rel].read_bytes() == data:
            same += 1
        else:
            updated += 1
            target.write_bytes(data)
    for rel, p in have.items():
        if rel not in files:
            removed += 1
            p.unlink()
    print(f'  memory: mirrored — {new} new, {updated} updated, {same} identical'
          + (f', {removed} removed (absent at source)' if removed else ''))


def transport_move(src_proj: Path, outbox: Path, session: Path) -> int:
    print(f'transport → {outbox.name}: {session.name}')
    status, conflicts = place_session(session, outbox / session.name, apply=True)
    print(f'  session: {status}')
    conflicts += move_workspace(src_proj / session.stem, outbox / session.stem, apply=True)
    mirror_memory(src_proj / 'memory', outbox / 'memory')
    print('APPLIED')
    return conflicts


def receive_move(bundle: Path, dest_proj: Path, session: Path, apply: bool, room: str) -> int:
    print(f'receive ← {room}: {session.name}')
    status, conflicts = place_session(session, dest_proj / session.name, apply)
    print(f'  session: {status}')
    conflicts += move_workspace(bundle / session.stem, dest_proj / session.stem, apply)
    conflicts += merge_memory(bundle / 'memory', dest_proj / 'memory', apply, room)
    print('APPLIED' if apply else 'dry run — pass --apply to write into the projects root')
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser(description='transport an agent (session × memory) between machines')
    sub = ap.add_subparsers(dest='direction', required=True)
    t = sub.add_parser('transport', help="mirror the agent into its own room's dir in the arrivals hall")
    t.add_argument('--session', required=True,
                   help='uuid(8) prefix of the agent to move — identity is never guessed')
    t.add_argument('--to', help='directory override (scratch/tests); default: ext/agents/<ext/machine binding>')
    r = sub.add_parser('receive', help="install a peer room's bundle from the arrivals hall")
    r.add_argument('--from', dest='source', required=True,
                   help='origin room name in the hall (or a directory)')
    r.add_argument('--session', required=True,
                   help='uuid(8) prefix of the agent to install — identity is never guessed')
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
        if args.to:
            outbox = Path(args.to).expanduser()
            outbox.mkdir(parents=True, exist_ok=True)
        else:
            outbox = own_outbox()
        src_proj = PROJECTS / key
        session = pick_session(src_proj, args.session)
        return 1 if transport_move(src_proj, outbox, session) else 0

    bundle = peer_bundle(args.source)
    session = pick_session(bundle, args.session)
    # the twin-dressing and marker label: the bundle's ADDRESS — the origin room's
    # name as it stands in the hall (or the directory's own name for a path)
    room = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in bundle.name) or 'incoming'
    return 1 if receive_move(bundle, PROJECTS / key, session, args.apply, room) else 0


if __name__ == '__main__':
    sys.exit(main())
