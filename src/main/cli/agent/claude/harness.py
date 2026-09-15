#!/usr/bin/env python
"""
harness.py - the Claude Code adapter (#633): the live store is the projects
root, <project>/<session>.jsonl beside <project>/<session-uuid>/ (the eponymous
workspace: subagent transcripts and persisted tool results the log references)
and <project>/memory/; the store keeps the same shape under
<machine>/<project>/. The session log is append-only, so a copy supersedes an
existing one iff the existing bytes are a prefix of it; the workspace moves with
log semantics per file; the memory folder is mirrored out on capture and merged
in on install (agent.py's header states the calculus). install and demerge are
this adapter's alone: they write into the harness-owned projects root.
"""
import contextlib
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/cli/agent/claude/harness.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))
from transport import Relation, Session, ambiguous, may_replace, move_workspace, place_log, word_placement  # noqa: E402

PROVIDER = 'claude'


def _projects(root: Path) -> list[Path]:
    return sorted(d for d in root.glob('-Users-*') if d.is_dir())


def _title(log: Path) -> str:
    """The session's last ai-title record - the title history rides the log, so
    this reads the same on a live and a transported session."""
    title = '(untitled)'
    for line in log.open(errors='replace'):
        if '"ai-title"' in line:
            try:
                title = json.loads(line).get('aiTitle') or title
            except ValueError:
                continue
    return title


def _sessions(root: Path) -> list[Session]:
    out = []
    for proj in _projects(root):
        for f in sorted(proj.glob('*.jsonl')):
            st = f.stat()
            out.append(Session(PROVIDER, f.stem, proj.name, f, _title(f), st.st_size, st.st_mtime))
    return out


def live_sessions(mount: Path) -> list[Session]:
    return _sessions(mount)


def held_sessions(machine_dir: Path) -> list[Session]:
    return _sessions(machine_dir)


def capture(mount: Path, outbox: Path, uuid8: str | None) -> int:
    if uuid8 is None:
        return capture_all(mount, outbox)
    session = pick_session(mount, uuid8)
    return capture_move(session.parent, outbox, session)


def model_rows(mount: Path) -> list[tuple[str, str, str, int]]:
    """message.model over every "type":"assistant" record, per project and
    session (subagent transcripts bucketed as 'subagents'): the model is a
    per-record fact, so a mid-session switch shows as a mixed session;
    '<synthetic>' rows are harness-authored records (no model spoke)."""
    rows = []
    for proj in sorted(p for p in mount.iterdir() if p.is_dir()):
        buckets: dict[str, Counter] = {}
        for f in sorted(proj.rglob('*.jsonl')):
            bucket = f.stem[:8] if f.parent == proj else 'subagents'
            for line in f.open(errors='replace'):
                if '"assistant"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get('type') != 'assistant':
                    continue
                model = (rec.get('message') or {}).get('model') or 'null'
                buckets.setdefault(bucket, Counter())[model] += 1
        for bucket in sorted(buckets):
            for model, n in buckets[bucket].most_common():
                rows.append((proj.name, bucket, model, n))
    return rows


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _sha_lines(text: str) -> str:
    """Line-canonical hash (trailing-newline-insensitive) — used where the
    hashed content is reconstructed from splitlines at demerge time."""
    return _sha('\n'.join(text.splitlines()))


def pick_session(root: Path, uuid8: str) -> Path:
    """The session to move, by IDENTITY: the --id uuid prefix must match
    exactly one .jsonl across the root's projects (root is a projects root or
    a machine's store dir — both nest <project>/<session>.jsonl). No recency
    guessing, no automatic choice, ever — capture moves an agent, and which
    agent is never the tool's call."""
    matches = [s for p in sorted(d for d in root.glob('-Users-*') if d.is_dir())
               for s in sorted(p.glob('*.jsonl')) if s.stem.startswith(uuid8)]
    if not matches:
        sys.exit(f'error: no session matching {uuid8!r} in {root}')
    if len(matches) > 1:
        sys.exit(ambiguous(uuid8, [(s.parent.name, s.stem) for s in matches], PROVIDER))
    return matches[0]


def place_session(src: Path, dest: Path, apply: bool) -> tuple[Relation, str]:
    return place_log(src.read_bytes(), dest, apply)


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, machine: str) -> int:
    """Memory-folder merge — INSTALL only, where two agents actually meet
    (capture mirrors its own outbox instead; see mirror_memory). A leaf
    file's NAME is dressing; the fact is the identity — so per leaf: absent →
    copy (novelty); identical → skip; the incoming extends the local
    (byte-prefix) → superseded in place (an appendix); true divergence → BOTH
    kept, the incoming fact re-dressed as <stem>.<machine>.md — machine is the
    sender's ADDRESS under data/input/claude/code/machine-transport, sender-declared — with its [[links]]
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
                next_map[target.stem] = f'{target.stem}.{machine}'
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
        block = [f'<!-- merge:begin {stamp} from={machine} -->', *novel, *acts, '<!-- merge:end -->']
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
    print('DONE' if apply else 'dry run — pass --apply to undo the merge')
    return 0


def mirror_memory(src_dir: Path, dest_dir: Path, quiet_noop: bool = False) -> bool:
    """Transport writes the agent's OWN outbox — single-writer by construction —
    so the memory folder is MIRRORED, not merged: the outbox is a faithful
    projection of the agent's current aggregate (new files added, changed ones
    updated in place, absentees removed). Every merge subtlety stays in
    install, where two agents meet. Returns eventful (anything beyond L1
    silence); with quiet_noop an all-identical mirror narrates nothing —
    the --all caller counts the silence instead."""
    files = {p.relative_to(src_dir): p for p in sorted(src_dir.rglob('*'))
             if p.is_file() and p.name != '.DS_Store'} if src_dir.is_dir() else {}
    if not files:
        if not quiet_noop:
            print('  memory: none at source')
        return False
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
    eventful = bool(new or updated or removed)
    if eventful or not quiet_noop:
        print(f'  memory: mirrored — {new} new, {updated} updated, {same} identical'
              + (f', {removed} removed (absent at source)' if removed else ''))
    return eventful


def _capture_session(src_proj: Path, dest_proj: Path, session: Path, label: str,
                       quiet_noop: bool = False) -> tuple[int, bool, bool]:
    """Mirror one session (log + workspace) into its project dir in the store.
    Returns (conflicts, wrote, eventful) with move_workspace's semantics
    extended to the pair. With quiet_noop, a session that lands wholly on L1
    silence (identical log, identical-or-absent workspace) narrates NOTHING —
    the --all caller names the silent ones in one line instead of three each.
    `label` is the header's destination spelling (<machine>/<project>)."""
    relation, detail = place_session(session, dest_proj / session.name, apply=True)
    conflicts = 1 if relation is Relation.DIVERGED else 0
    ws_narration = io.StringIO()
    with contextlib.redirect_stdout(ws_narration):
        ws_conflicts, ws_wrote, ws_eventful = move_workspace(
            src_proj / session.stem, dest_proj / session.stem, apply=True,
            src_label='local', dest_label='remote')
    conflicts += ws_conflicts
    wrote = ws_wrote or may_replace(relation)
    eventful = wrote or bool(conflicts) or ws_eventful or relation is not Relation.IDENTICAL
    if eventful or not quiet_noop:
        print(f'capture → {label}: {session.name}')
        print(f'  session: {word_placement(relation, detail, "local", "remote")}')
        print(ws_narration.getvalue(), end='')
    return conflicts, wrote, eventful


def capture_move(src_proj: Path, outbox: Path, session: Path) -> int:
    """Mirror ONE named session (and its project's memory) into the store:
    <outbox>/<project>/. The agent is the PRODUCT session × memory: a session
    CONFLICT withholds the memory mirror, or the store would hold a memory
    that reflects history its own session component does not contain."""
    dest_proj = outbox / src_proj.name
    conflicts, _, _ = _capture_session(src_proj, dest_proj, session,
                                         f'{outbox.name}/{src_proj.name}')
    if conflicts:
        print('  memory: WITHHELD — session CONFLICT above; the agent transports as a '
              'product, so reconcile the session first')
        print('DONE')
        return conflicts
    mirror_memory(src_proj / 'memory', dest_proj / 'memory')
    print('DONE')
    return conflicts


def capture_all(src_root: Path, outbox: Path) -> int:
    """git push --all, whole stable: mirror EVERY project's sessions, and each
    project's memory, into <outbox>/<project>/. The projects root is
    harness-owned and expires at Anthropic's pleasure; the store is the
    durable home, so the sweep covers every project, not just this repo's —
    and it is MONOTONE: a project absent from the projects root is left in
    the store untouched (outliving the harness is the point). Safe by the
    prefix lattice per session: silence, fast-forward, ahead-no-op, or a loud
    per-session CONFLICT — idempotent throughout. Narration is lattice-shaped:
    sessions and memories landing on L1 silence are counted, not narrated,
    and the tail keeps EFFECT (what this run wrote) and POSTCONDITION (what
    the store now holds) apart."""
    projects = sorted(d for d in src_root.glob('-Users-*') if d.is_dir())
    if not projects:
        print(f'error: no projects under {src_root}', file=sys.stderr)
        return 1
    conflicts, written, total, quiet, quiet_mem = 0, 0, 0, [], 0
    for proj in projects:
        label = f'{outbox.name}/{proj.name}'
        sessions = sorted(proj.glob('*.jsonl'))
        total += len(sessions)
        proj_conflicts = 0
        for s in sessions:
            c, wrote, eventful = _capture_session(proj, outbox / proj.name, s,
                                                    label, quiet_noop=True)
            conflicts += c
            proj_conflicts += c
            written += 1 if wrote else 0
            if not eventful:
                quiet.append(s.stem[:8])
        if (proj / 'memory').is_dir():
            if proj_conflicts:
                print(f'capture → {label}: memory/ WITHHELD — session CONFLICT(S) in this '
                      'project; the agent transports as a product, so reconcile first')
                continue
            mem_narration = io.StringIO()
            with contextlib.redirect_stdout(mem_narration):
                mem_eventful = mirror_memory(proj / 'memory',
                                             outbox / proj.name / 'memory', quiet_noop=True)
            if mem_eventful:
                print(f'capture → {label}: memory/')
                print(mem_narration.getvalue(), end='')
            else:
                quiet_mem += 1
    if quiet:
        print(f'{len(quiet)} session(s) identical in local and remote '
              f'(log and workspace): {", ".join(quiet)}')
    if quiet_mem:
        print(f'{quiet_mem} project memor(y/ies) identical in local and remote')
    # The tail names the strongest true statement: with no effect, the
    # PRECONDITION ("already held" — it was true before the run, so nothing
    # needed doing); with writes, effect and postcondition as separate clauses.
    if conflicts:
        print(f'DONE — effect: {written} of {total} session(s) written, '
              f'{conflicts} CONFLICT(S); postcondition: remote ({outbox.name}) does NOT '
              'yet hold everything local holds — CONFLICT(S) above left in place, '
              'their projects\' memories withheld')
    elif written:
        print(f'DONE — effect: {written} of {total} session(s) written; '
              f'postcondition: remote ({outbox.name}) holds everything local holds')
    else:
        print(f'DONE — no effect: remote ({outbox.name}) already held everything local holds')
    return conflicts


def _install_session(bundle_proj: Path, dest_proj: Path, session: Path, apply: bool, machine: str) -> int:
    print(f'install ← {machine}/{bundle_proj.name}: {session.name}')
    relation, detail = place_session(session, dest_proj / session.name, apply)
    print(f'  session: {word_placement(relation, detail, "remote", "local")}')
    ws_conflicts, _, _ = move_workspace(bundle_proj / session.stem, dest_proj / session.stem, apply,
                                        src_label='remote', dest_label='local')
    return (1 if relation is Relation.DIVERGED else 0) + ws_conflicts


def install_all(bundle: Path, dest_root: Path, apply: bool, machine: str) -> int:
    """git pull --all from one peer: every session in every project the machine
    transported (and each project's memory, merged once per project — one
    marker block, one demerge, per project). The same lattice safety as
    capture --all, plus install's own guard: dry-run unless --apply. This
    is the ONE deliberate writer of the harness-owned projects root — never
    run by any pipeline, only by a user's explicit command."""
    projects = sorted(d for d in bundle.glob('-Users-*') if d.is_dir())
    if not projects:
        print(f'error: no projects in {bundle}', file=sys.stderr)
        return 1
    conflicts = total = 0
    for proj in projects:
        proj_conflicts = 0
        for s in sorted(proj.glob('*.jsonl')):
            total += 1
            proj_conflicts += _install_session(proj, dest_root / proj.name, s, apply, machine)
        conflicts += proj_conflicts
        if (proj / 'memory').is_dir():
            if proj_conflicts:
                print(f'install ← {machine}/{proj.name}: memory/ WITHHELD — session '
                      'CONFLICT(S) in this project; the agent transports as a product, '
                      'so reconcile first')
                continue
            conflicts += merge_memory(proj / 'memory', dest_root / proj.name / 'memory', apply, machine)
    print(f'{"DONE" if apply else "dry run — pass --apply to write into the projects root"}'
          f' — {total} session(s)' + (f', {conflicts} CONFLICT(S)' if conflicts else ''))
    return conflicts


def install_move(bundle_proj: Path, dest_root: Path, session: Path, apply: bool, machine: str) -> int:
    conflicts = _install_session(bundle_proj, dest_root / bundle_proj.name, session, apply, machine)
    if conflicts:
        print('  memory: WITHHELD — session CONFLICT above; the agent transports as a '
              'product, so reconcile the session first')
    else:
        conflicts += merge_memory(bundle_proj / 'memory', dest_root / bundle_proj.name / 'memory', apply, machine)
    print('DONE' if apply else 'dry run — pass --apply to write into the projects root')
    return conflicts
