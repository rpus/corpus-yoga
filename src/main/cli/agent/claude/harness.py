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
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/cli/agent/claude/harness.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))
from transport import LIVE, STAGE, STORE, Log, Relation, Session, fact, may_replace, outcome, place_log, place_tree, relate, strings  # noqa: E402

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


def written(session: Session) -> Iterator[str]:
    """Every string a tool call of the session carried as its input - the commands it
    ran, the files it wrote - in the record's order (#631): the session's own log, then
    its subagents', whose logs lie in its companion directory and whose acts are its."""
    companion = session.path.with_suffix('')
    for log in [session.path] + (sorted(companion.rglob('*.jsonl')) if companion.is_dir() else []):
        with log.open() as f:
            for line in f:
                if '"tool_use"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                content = (record.get('message') or {}).get('content')
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        yield from strings(block.get('input'))


def capture(mount: Path, outbox: Path, held: Path, uuid8: str | None) -> Log:
    if uuid8 is None:
        return capture_all(mount, outbox, held)
    session = pick_session(mount, uuid8)
    return capture_move(session.parent, outbox, held, session)


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
        sys.exit(f'error: {uuid8!r} is ambiguous here — matches: '
                 + ', '.join(f'{s.parent.name}/{s.stem}' for s in matches))
    return matches[0]


def place_session(src: Path, dest: Path, apply: bool) -> tuple[Relation, str]:
    return place_log(src.read_bytes(), dest, apply)


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, machine: str, log: Log, label: str) -> int:
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
    facts rewritten to their new names. Each leaf is said into the log under
    its outcome by its address, label/memory/<leaf> (#857). Returns the conflict count."""
    conflicts = 0
    if not src_dir.is_dir():
        return 0

    def said(which: str, rel, facts: dict[str, str]) -> None:
        log.say(which, f'{label}/memory/{rel}', facts, 'file')

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
            said('wrote', rel, {f'{LIVE} holds nothing yet': f'{len(form)} bytes'})
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(form)
            acts.append(f'<!-- merge:act new {rel} sha={_sha(form)} len={len(form)} -->')
            continue
        have = target.read_text()
        if have == form:
            said('kept', rel, {f'{STORE} and {LIVE} hold identical text': f'{len(have)} bytes'})
        elif form.startswith(have):
            said('wrote', rel, {f'{STORE} extends {LIVE}': f'{len(have)} → {len(form)} bytes'})
            if apply:
                target.write_text(form)
            acts.append(f'<!-- merge:act appendix {rel} prior={len(have)} '
                        f'post={len(form)} sha={_sha(form)} -->')
        elif have.startswith(form):
            said('kept', rel, {f'{LIVE} is ahead of {STORE}': f'{len(have)} > {len(form)} bytes'})
        else:
            twin = target.with_name(f'{renamed[target.stem]}{target.suffix}')
            twin_rel = rel.with_name(twin.name)
            if twin.exists() and twin.read_text() == form:
                said('kept', rel, {f'{STORE} and {LIVE} diverged': f'the twin {twin.name} already holds it'})
            elif twin.exists():
                said('conflict', rel, {f'{STORE} and {LIVE} diverged': f'and the twin {twin.name} differs - left in place'})
                conflicts += 1
            else:
                said('wrote', rel, {f'{STORE} and {LIVE} diverged': f'both kept - installed as {twin.name}'})
                if apply:
                    twin.write_text(form)
                acts.append(f'<!-- merge:act new {twin_rel} sha={_sha(form)} len={len(form)} -->')
    # MEMORY.md: the index unions by novelty-append, re-dressed lines rewritten
    src_index = src_dir / 'MEMORY.md'
    dest_index = dest_dir / 'MEMORY.md'
    novel: list[str] = []
    index: dict[str, str] = {}
    which = 'kept'
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
            index[f'{LIVE} holds nothing yet'] = f'{len(src_lines)} line(s)'
            which = 'wrote'
            if apply:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_index.write_text(filtered)
            acts.append(f'<!-- merge:act index-new sha={_sha_lines(filtered)} -->')
            novel = []  # the whole index arrived; no separate union lines
        elif novel:
            index['index unioned'] = f'{len(novel)} line(s) appended inside the merge marker'
            which = 'wrote'
        else:
            index['index already covers it'] = f'{len(have_lines)} line(s)'
    # the merge marker: begin/end comments wrapping the unioned lines, then the
    # acts — MEMORY.md carries the record that makes this merge demergeable
    if acts or novel:
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')
        block = [f'<!-- merge:begin {stamp} from={machine} -->', *novel, *acts, '<!-- merge:end -->']
        index['merge marker'] = f'{len(acts)} act(s); corpus-yoga agent demerge undoes them'
        which = 'wrote'
        if apply:
            cur = dest_index.read_text() if dest_index.exists() else ''
            if cur and not cur.endswith('\n'):
                cur += '\n'
            dest_index.write_text(cur + '\n'.join(block) + '\n')
    if index:
        said(which, 'MEMORY.md', index)
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
    return 0


def mirror_memory(src_dir: Path, dest_dir: Path, held_dirs: list[Path] = []) -> tuple[str, dict[str, str]] | None:
    """Transport writes the agent's OWN outbox - single-writer by construction -
    so the memory folder is MIRRORED, not merged: the outbox is a faithful
    projection of the agent's current aggregate (new files added, changed ones
    updated in place, absentees removed). Every merge subtlety stays in
    install, where two agents meet. Where the outbox holds no copy, the held
    ones are the baseline (#850): a memory the store holds identical under any
    of held_dirs - the project's own name, or a name whose live memory is the
    same directory - is not mirrored again. Returns (outcome, facts), or None
    where the source has no memory."""
    files = {p.relative_to(src_dir): p for p in sorted(src_dir.rglob('*'))
             if p.is_file() and p.name != '.DS_Store'} if src_dir.is_dir() else {}
    if not files:
        return None
    live = {rel: f.read_bytes() for rel, f in files.items()}
    if not dest_dir.is_dir():
        for held_dir in held_dirs:
            if held_dir.is_dir() and live == {p.relative_to(held_dir): p.read_bytes() for p in sorted(held_dir.rglob('*'))
                                              if p.is_file() and p.name != '.DS_Store'}:
                return 'kept', {f'{LIVE} and {STORE} hold identical files': f'{len(files)} file(s)'}
    have = {p.relative_to(dest_dir): p for p in sorted(dest_dir.rglob('*'))
            if p.is_file() and p.name != '.DS_Store'} if dest_dir.is_dir() else {}
    new = updated = same = removed = 0
    for rel, data in live.items():
        target = dest_dir / rel
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
    if not (new or updated or removed):
        return 'kept', {f'{LIVE} and {STAGE} hold identical files': f'{same} file(s)'}
    return 'wrote', {f'mirrored into {STAGE}': f'{new} new, {updated} updated, {same} identical'
                     + (f', {removed} removed (absent in {LIVE})' if removed else '')}


def memory_names(src_root: Path, proj: Path) -> list[str]:
    """The project names whose live memory is the one directory proj's is - its own first,
    then those a link joins to it, the names a repository rename leaves (#744)."""
    own = (proj / 'memory').resolve()
    return [proj.name] + sorted(p.name for p in _projects(src_root)
                                if p != proj and (p / 'memory').is_dir() and (p / 'memory').resolve() == own)


def _capture_session(src_proj: Path, dest_proj: Path, held_proj: Path, session: Path, log: Log) -> bool:
    """Mirror one session (log + workspace) into its project dir in the stage, said into
    the log under its outcome by its address, <project>/<session> (#857). Where the stage
    holds no copy, the held one under held_proj is the baseline (#850): a log the store
    holds identical or ahead is not staged and its workspace is not read, one that
    diverges from the held copy is a CONFLICT, as the promote would say, and one that
    extends it is written to the stage. Returns whether the session conflicted."""
    data = session.read_bytes()
    staged_log, held_log = dest_proj / session.name, held_proj / session.name
    against_store = not staged_log.exists() and held_log.exists()
    existing = held_log.read_bytes() if against_store else staged_log.read_bytes() if staged_log.exists() else None
    relation = relate(data, existing)
    if may_replace(relation):
        staged_log.parent.mkdir(parents=True, exist_ok=True)
        staged_log.write_bytes(data)
    which = outcome(relation)
    log.say(which, f'{src_proj.name}/{session.name}', fact(relation, data, existing, LIVE, STORE if against_store else STAGE), 'session')
    if against_store and which != 'wrote':
        return which == 'conflict'
    placed = place_tree(src_proj / session.stem, dest_proj / session.stem, True, LIVE, STAGE)
    if placed is not None:
        log.say(placed[0], f'{src_proj.name}/{session.stem}/', placed[1])
        return which == 'conflict' or placed[0] == 'conflict'
    return which == 'conflict'


def _capture_memory(src_root: Path, proj: Path, outbox: Path, held: Path, withheld: bool, log: Log) -> None:
    """The project's memory into the stage, said under its outcome by its address."""
    if not (proj / 'memory').is_dir():
        return
    if withheld:
        log.say('kept', f'{proj.name}/memory/', {'withheld': 'a session of the project conflicted; the agent transports as a product'}, 'memory')
        return
    mirrored = mirror_memory(proj / 'memory', outbox / proj.name / 'memory',
                             held_dirs=[held / n / 'memory' for n in memory_names(src_root, proj)])
    if mirrored is not None:
        log.say(mirrored[0], f'{proj.name}/memory/', mirrored[1], 'memory')


def capture_move(src_proj: Path, outbox: Path, held: Path, session: Path) -> Log:
    """Mirror ONE named session (and its project's memory) into the stage:
    <outbox>/<project>/. The agent is the PRODUCT session × memory: a session
    CONFLICT withholds the memory mirror, or the store would hold a memory
    that reflects history its own session component does not contain."""
    log = Log(STAGE)
    conflicted = _capture_session(src_proj, outbox / src_proj.name, held / src_proj.name, session, log)
    _capture_memory(src_proj.parent, src_proj, outbox, held, conflicted, log)
    return log


def capture_all(src_root: Path, outbox: Path, held: Path) -> Log:
    """git push --all, whole stable: mirror EVERY project's sessions, and each
    project's memory, into <outbox>/<project>/. The projects root is
    harness-owned and expires at Anthropic's pleasure; the store is the
    durable home, so the sweep covers every project, not just this repo's -
    and it is MONOTONE: a project absent from the projects root is left in
    the store untouched (outliving the harness is the point). Safe by the
    prefix lattice per session: silence, fast-forward, ahead-no-op, or a
    per-session CONFLICT - idempotent throughout."""
    log = Log(STAGE)
    for proj in _projects(src_root):
        conflicted = False
        for s in sorted(proj.glob('*.jsonl')):
            conflicted = _capture_session(proj, outbox / proj.name, held / proj.name, s, log) or conflicted
        _capture_memory(src_root, proj, outbox, held, conflicted, log)
    return log


def _install_session(bundle_proj: Path, dest_proj: Path, session: Path, apply: bool, log: Log) -> bool:
    """One held session into the projects root, said under its outcome by its address;
    returns whether it conflicted."""
    data = session.read_bytes()
    target = dest_proj / session.name
    existing = target.read_bytes() if target.exists() else None
    relation = relate(data, existing)
    if apply and may_replace(relation):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    which = outcome(relation)
    log.say(which, f'{bundle_proj.name}/{session.name}', fact(relation, data, existing, STORE, LIVE), 'session')
    placed = place_tree(bundle_proj / session.stem, dest_proj / session.stem, apply, STORE, LIVE)
    if placed is not None:
        log.say(placed[0], f'{bundle_proj.name}/{session.stem}/', placed[1])
        return which == 'conflict' or placed[0] == 'conflict'
    return which == 'conflict'


def install_all(bundle: Path, dest_root: Path, apply: bool, machine: str) -> Log:
    """git pull --all from one peer: every session in every project the machine
    transported (and each project's memory, merged once per project - one
    marker block, one demerge, per project). The same lattice safety as
    capture --all, plus install's own guard: dry-run unless --apply. This
    is the ONE deliberate writer of the harness-owned projects root - never
    run by any pipeline, only by a user's explicit command."""
    log = Log(LIVE, 'did' if apply else 'would')
    for proj in sorted(d for d in bundle.glob('-Users-*') if d.is_dir()):
        conflicted = False
        for s in sorted(proj.glob('*.jsonl')):
            conflicted = _install_session(proj, dest_root / proj.name, s, apply, log) or conflicted
        if (proj / 'memory').is_dir():
            if conflicted:
                log.say('kept', f'{proj.name}/memory/', {'withheld': 'a session of the project conflicted; the agent transports as a product'}, 'memory')
            else:
                merge_memory(proj / 'memory', dest_root / proj.name / 'memory', apply, machine, log, proj.name)
    return log


def install_move(bundle_proj: Path, dest_root: Path, session: Path, apply: bool, machine: str) -> Log:
    log = Log(LIVE, 'did' if apply else 'would')
    conflicted = _install_session(bundle_proj, dest_root / bundle_proj.name, session, apply, log)
    if conflicted:
        log.say('kept', f'{bundle_proj.name}/memory/', {'withheld': 'the session conflicted; the agent transports as a product'}, 'memory')
    else:
        merge_memory(bundle_proj / 'memory', dest_root / bundle_proj.name / 'memory', apply, machine, log, bundle_proj.name)
    return log
