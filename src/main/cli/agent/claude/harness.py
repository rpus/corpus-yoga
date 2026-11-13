"""
harness.py - the Claude Code adapter (issues/633): the live store is the projects
root, <project>/<session>.jsonl beside <project>/<session-uuid>/ (the eponymous
workspace: subagent transcripts and persisted tool results the log references)
and <project>/memory/; the store keeps the same shape under
<machine>/<project>/. The session log is append-only, so a copy supersedes an
existing one iff the existing bytes are a prefix of it; the workspace moves with
log semantics per file; the memory folder is mirrored out on capture and merged
in on pull (agent.py's header states the calculus). pull is
this adapter's alone: it writes into the harness-owned projects root.
"""
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from transport import LIVE, STAGE, STORE, Log, Relation, Session, current_key, fact, held_by_peer, keys_of, may_replace, outcome, place_log, place_tree, relate, strings

SELF = 'src/main/cli/agent/claude/harness.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

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
            out.append(Session(PROVIDER, f.stem, proj.name, f, lambda log=f: _title(log), st.st_size, st.st_mtime))
    return out


def live_sessions(mount: Path) -> list[Session]:
    return _sessions(mount)


def held_sessions(machine_dir: Path) -> list[Session]:
    return _sessions(machine_dir)


def written(session: Session) -> Iterator[str]:
    """Every string a tool call of the session carried as its input - the commands it
    ran, the files it wrote - in the record's order (issues/631): the session's own log, then
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


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, machine: str, room: str, log: Log, label: str) -> int:
    """Memory-folder merge — on pull only, where two agents actually meet
    (capture mirrors its own outbox instead; see mirror_memory). A leaf
    file's NAME is dressing; the fact is the identity — so per leaf, judged against
    its local copy alone with each link read as the fact it names: absent →
    copy (novelty); identical → skip; the incoming extends the local
    (byte-prefix) → superseded in place (an appendix); true divergence → BOTH
    kept, the incoming fact re-dressed as <stem>.<machine>.md — machine is the
    sender's ADDRESS under data/input/claude/code/machine-transport, sender-declared — with its [[links]]
    following (nothing lost, nothing blocking — reconciliation stays a human act). The twin is
    the sender's copy, so it follows the sender's fact (issues/1073). A file the sender holds as a
    twin of room's fact, or of its own, is no fact of its own: room's fact and the sender's
    plain one stand for them, so it is not received. MEMORY.md is the
    index, not a fact: it unions by novelty-append, with lines for re-dressed
    facts rewritten to their new names, and the merge leaves no record of itself in it
    (issues/1063): it only adds, so there is nothing to undo that removing a fact does not. Each leaf is said into the log under
    its outcome by its address, label/memory/<leaf> (issues/857). Returns the conflict count."""
    conflicts = 0
    if not src_dir.is_dir():
        return 0

    def said(which: str, rel, facts: dict[str, str]) -> None:
        log.say(which, f'{label}/memory/{rel}', facts, 'file')

    def dressed(text: str, renames: dict[str, str]) -> str:
        for old, new in renames.items():
            text = text.replace(f'[[{old}]]', f'[[{new}]]')
        return text

    def bare(text: str) -> str:
        """The text with each link to a fact re-dressed for the sender said by the fact's own
        name: a link names a fact, and the sender's suffix on it is no part of the fact."""
        return re.sub(rf'\[\[([^\]]+)\.{re.escape(machine)}\]\]', r'[[\1]]', text)

    def related(raw: str, have: str) -> str:
        """How the incoming copy of a fact stands to the local one, read bare."""
        incoming, held = bare(raw), bare(have)
        return ('identical' if incoming == held else 'extends' if incoming.startswith(held)
                else 'ahead' if held.startswith(incoming) else 'diverged')

    leaves = [(p.relative_to(src_dir), p.read_text())
              for p in sorted(src_dir.rglob('*'))
              if p.is_file() and p.name not in ('.DS_Store', 'MEMORY.md')]
    whose = {room: "{STORE} holds this room's own fact as the sender's twin of it",
             machine: '{STORE} holds the sender\'s own fact as a twin of it'}
    twins = {rel: rel.stem.rsplit('.', 1) for rel, _raw in leaves if rel.stem.rsplit('.', 1)[-1] in whose and '.' in rel.stem}
    for rel, (stem, of) in twins.items():
        said('kept', rel, {whose[of].format(STORE=STORE): f'read as {stem}{rel.suffix}'})
    leaves = [(rel, raw) for rel, raw in leaves if rel not in twins]
    # each pair of copies judged alone, read bare, so that no fact's judgement waits on another's
    # and a fact written with its links re-dressed is received again as identical (L1)
    relation = {rel: related(raw, (dest_dir / rel).read_text()) for rel, raw in leaves if (dest_dir / rel).exists()}
    renamed = {rel.stem: f'{rel.stem}.{machine}' for rel, held in relation.items() if held == 'diverged'}

    for rel, raw in leaves:
        target = dest_dir / rel
        form = dressed(raw, renamed)
        if not target.exists():
            said('wrote', rel, {f'{LIVE} holds nothing yet': f'{len(form)} bytes'})
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(form)
            continue
        have = target.read_text()
        if relation[rel] == 'identical':
            said('kept', rel, {f'{STORE} and {LIVE} hold identical text': f'{len(have)} bytes'})
        elif relation[rel] == 'extends':
            # the held text kept byte for byte, the incoming tail after it
            form = have + dressed(bare(raw)[len(bare(have)):], renamed)
            said('wrote', rel, {f'{STORE} extends {LIVE}': f'{len(have)} → {len(form)} bytes'})
            if apply:
                target.write_text(form)
        elif relation[rel] == 'ahead':
            said('kept', rel, {f'{LIVE} is ahead of {STORE}': f'{len(have)} > {len(form)} bytes'})
        else:
            twin = target.with_name(f'{renamed[rel.stem]}{target.suffix}')
            if twin.exists() and twin.read_text() == form:
                said('kept', rel, {f'{STORE} and {LIVE} diverged': f'the twin {twin.name} already holds it'})
            else:
                said('wrote', rel, {f'{STORE} and {LIVE} diverged': f'the twin {twin.name} follows the sender\'s'
                                    if twin.exists() else f'both kept - written as {twin.name}'})
                if apply:
                    twin.write_text(form)
    # MEMORY.md: the index unions by novelty-append, re-dressed lines rewritten
    src_index = src_dir / 'MEMORY.md'
    dest_index = dest_dir / 'MEMORY.md'
    novel: list[str] = []
    index: dict[str, str] = {}
    which = 'kept'
    if src_index.exists():
        have_lines = dest_index.read_text().splitlines() if dest_index.exists() else []
        # a store that holds an index from before issues/1063 holds merge records in it: they
        # are no index lines, and the index lines inside them union like any others
        src_lines = [l for l in src_index.read_text().splitlines()
                     if not l.lstrip().startswith('<!-- merge:') and not any(f'({rel.as_posix()})' in l for rel in twins)]
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
        elif novel:
            index['index unioned'] = f'{len(novel)} line(s) appended'
            which = 'wrote'
            if apply:
                cur = dest_index.read_text()
                dest_index.write_text(cur + ('' if cur.endswith('\n') or not cur else '\n') + '\n'.join(novel) + '\n')
        else:
            index['index already covers it'] = f'{len(have_lines)} line(s)'
    if index:
        said(which, 'MEMORY.md', index)
    return conflicts


def mirror_memory(src_dir: Path, dest_dir: Path, held_dirs: list[Path] = []) -> tuple[str, dict[str, str]] | None:
    """Transport writes the agent's OWN outbox - single-writer by construction -
    so the memory folder is MIRRORED, not merged: the outbox is a faithful
    projection of the agent's current aggregate (new files added, changed ones
    updated in place, absentees removed). Every merge subtlety stays in
    pull, where two agents meet. Where the outbox holds no copy, the held
    ones are the baseline (issues/850): a memory the store holds identical under any
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
    """The project names a store may hold proj's memory under - its own first, then those a
    link joins to it (issues/744), then the keys the checkout's former paths gave (issues/1058):
    the names a repository rename leaves."""
    own = (proj / 'memory').resolve()
    linked = sorted(p.name for p in _projects(src_root)
                    if p != proj and (p / 'memory').is_dir() and (p / 'memory').resolve() == own)
    return [proj.name, *linked, *(k for k in keys_of(proj.name)[1:] if k not in linked)]


def _capture_session(src_proj: Path, dest_proj: Path, held_projs: list[Path], session: Path, log: Log) -> bool:
    """Mirror one session (log + workspace) into its project dir in the stage, said into
    the log under its outcome by its address, <project>/<session> (issues/857). Where the stage
    holds no copy, the held one under the first of held_projs - the project's own name, then
    the names a rename left (issues/1058) - is the baseline (issues/850), and a session another
    room's store dir holds identical or ahead is that room's, kept (issues/1071): a log the store
    holds identical or ahead is not staged and its workspace is not read, one that
    diverges from the held copy is a CONFLICT, as the promote would say, and one that
    extends it is written to the stage. Returns whether the session conflicted."""
    data = session.read_bytes()
    staged_log = dest_proj / session.name
    held_log = next((held / session.name for held in held_projs if (held / session.name).exists()), held_projs[0] / session.name)
    against_store = not staged_log.exists() and held_log.exists()
    existing = held_log.read_bytes() if against_store else staged_log.read_bytes() if staged_log.exists() else None
    relation = relate(data, existing)
    peer = held_by_peer(held_projs[0].parent, session.name, data) if relation not in (Relation.IDENTICAL, Relation.AHEAD) else None
    if peer is not None:
        log.say('kept', f'{src_proj.name}/{session.name}',
                {f"{STORE} holds it as {peer[0]}'s": f'{len(data)} bytes here, {peer[1].stat().st_size} there'}, 'session')
        return False
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
    conflicted = _capture_session(src_proj, outbox / src_proj.name, [held / k for k in keys_of(src_proj.name)], session, log)
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
            conflicted = _capture_session(proj, outbox / proj.name, [held / k for k in keys_of(proj.name)], s, log) or conflicted
        _capture_memory(src_root, proj, outbox, held, conflicted, log)
    return log


def _pull_session(bundle_proj: Path, dest_proj: Path, session: Path, apply: bool, log: Log) -> bool:
    """One held session into the projects root, said under its outcome by its address;
    returns whether it conflicted. A session that diverged from this room's live copy is
    kept as it stands, its divergence said (issues/1071)."""
    data = session.read_bytes()
    target = dest_proj / session.name
    # a session the room holds still under a key a former path gave is the copy it holds (issues/1058)
    held = next((d / session.name for d in (dest_proj.parent / k for k in keys_of(dest_proj.name)) if (d / session.name).exists()), target)
    existing = held.read_bytes() if held.exists() else None
    relation = relate(data, existing)
    if relation is Relation.DIVERGED:
        # a session two rooms continued apart is each room's own (issues/1071): this room's stands,
        # the peer's stays in the store, and the divergence is a fact, withholding nothing
        log.say('kept', f'{bundle_proj.name}/{session.name}', fact(relation, data, existing, STORE, LIVE), 'session')
        return False
    if apply and may_replace(relation):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    which = outcome(relation)
    log.say(which, f'{bundle_proj.name}/{session.name}', fact(relation, data, existing, STORE, LIVE), 'session')
    placed = place_tree(bundle_proj / session.stem, held.parent / session.stem, apply, STORE, LIVE)
    if placed is not None:
        log.say(placed[0], f'{bundle_proj.name}/{session.stem}/', placed[1])
        return which == 'conflict' or placed[0] == 'conflict'
    return which == 'conflict'


def pull_all(bundle: Path, dest_root: Path, apply: bool, machine: str, room: str) -> Log:
    """git pull --all from one peer: every session in every project the machine
    transported (and each project's memory, merged once per project). The same lattice safety as
    capture --all; what it would write is corpus-yoga agent's status (issues/881). This
    is the ONE deliberate writer of the harness-owned projects root - never
    run by any pipeline, only by a user's explicit command. A project the peer holds
    under a key a former path of the checkout gave is written under the current key
    (issues/1058), so that a rename leaves one project in every room."""
    log = Log(LIVE, 'did' if apply else 'would')
    for proj in sorted(d for d in bundle.glob('-Users-*') if d.is_dir()):
        conflicted = False
        dest = dest_root / current_key(proj.name)
        for s in sorted(proj.glob('*.jsonl')):
            conflicted = _pull_session(proj, dest, s, apply, log) or conflicted
        if (proj / 'memory').is_dir():
            if conflicted:
                log.say('kept', f'{proj.name}/memory/', {'withheld': 'a session of the project conflicted; the agent transports as a product'}, 'memory')
            else:
                merge_memory(proj / 'memory', dest / 'memory', apply, machine, room, log, proj.name)
    return log


def pull_move(bundle_proj: Path, dest_root: Path, session: Path, apply: bool, machine: str, room: str) -> Log:
    log = Log(LIVE, 'did' if apply else 'would')
    conflicted = _pull_session(bundle_proj, dest_root / current_key(bundle_proj.name), session, apply, log)
    if conflicted:
        log.say('kept', f'{bundle_proj.name}/memory/', {'withheld': 'the session conflicted; the agent transports as a product'}, 'memory')
    else:
        merge_memory(bundle_proj / 'memory', dest_root / current_key(bundle_proj.name) / 'memory', apply, machine, room, log, bundle_proj.name)
    return log
