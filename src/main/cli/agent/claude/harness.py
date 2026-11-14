"""
harness.py - the Claude Code adapter (issues/633): the live store is the projects
root, <project>/<session>.jsonl beside <project>/<session-uuid>/ (the eponymous
workspace: subagent transcripts and persisted tool results the log references);
the store keeps the same shape under <machine>/<project>/. The session log is
append-only, so a copy supersedes an existing one iff the existing bytes are a
prefix of it; the workspace moves with log semantics per file (agent.py's header
states the calculus). A project's memory/ is the room's own: no capture reads it
and no pull writes it (issues/1090). pull is this adapter's alone: it writes into
the harness-owned projects root.
"""
import json
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


def _capture_session(src_proj: Path, dest_proj: Path, held_projs: list[Path], session: Path, log: Log) -> None:
    """Mirror one session (log + workspace) into its project dir in the stage, said into
    the log under its outcome by its address, <project>/<session> (issues/857). Where the stage
    holds no copy, the held one under the first of held_projs - the project's own name, then
    the names a rename left (issues/1058) - is the baseline (issues/850), and a session another
    room's store dir holds identical or ahead is that room's, kept (issues/1071): a log the store
    holds identical or ahead is not staged and its workspace is not read, one that
    diverges from the held copy is a CONFLICT, as the promote would say, and one that
    extends it is written to the stage."""
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
        return
    if may_replace(relation):
        staged_log.parent.mkdir(parents=True, exist_ok=True)
        staged_log.write_bytes(data)
    which = outcome(relation)
    log.say(which, f'{src_proj.name}/{session.name}', fact(relation, data, existing, LIVE, STORE if against_store else STAGE), 'session')
    if against_store and which != 'wrote':
        return
    placed = place_tree(src_proj / session.stem, dest_proj / session.stem, True, LIVE, STAGE)
    if placed is not None:
        log.say(placed[0], f'{src_proj.name}/{session.stem}/', placed[1])


def capture_move(src_proj: Path, outbox: Path, held: Path, session: Path) -> Log:
    """Mirror ONE named session into the stage: <outbox>/<project>/."""
    log = Log(STAGE)
    _capture_session(src_proj, outbox / src_proj.name, [held / k for k in keys_of(src_proj.name)], session, log)
    return log


def capture_all(src_root: Path, outbox: Path, held: Path) -> Log:
    """git push --all, whole stable: mirror EVERY project's sessions into
    <outbox>/<project>/. The projects root is
    harness-owned and expires at Anthropic's pleasure; the store is the
    durable home, so the sweep covers every project, not just this repo's -
    and it is MONOTONE: a project absent from the projects root is left in
    the store untouched (outliving the harness is the point). Safe by the
    prefix lattice per session: silence, fast-forward, ahead-no-op, or a
    per-session CONFLICT - idempotent throughout."""
    log = Log(STAGE)
    for proj in _projects(src_root):
        for s in sorted(proj.glob('*.jsonl')):
            _capture_session(proj, outbox / proj.name, [held / k for k in keys_of(proj.name)], s, log)
    return log


def _pull_session(bundle_proj: Path, dest_proj: Path, session: Path, apply: bool, log: Log) -> None:
    """One held session into the projects root, said under its outcome by its address. A
    session that diverged from this room's live copy is kept as it stands, its divergence
    said (issues/1071)."""
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
        return
    if apply and may_replace(relation):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    which = outcome(relation)
    log.say(which, f'{bundle_proj.name}/{session.name}', fact(relation, data, existing, STORE, LIVE), 'session')
    placed = place_tree(bundle_proj / session.stem, held.parent / session.stem, apply, STORE, LIVE)
    if placed is not None:
        log.say(placed[0], f'{bundle_proj.name}/{session.stem}/', placed[1])


def pull_all(bundle: Path, dest_root: Path, apply: bool) -> Log:
    """git pull --all from one peer: every session in every project the machine
    transported, and none of its memory (issues/1090). The same lattice safety as
    capture --all; what it would write is corpus-yoga agent's status (issues/881). This
    is the ONE deliberate writer of the harness-owned projects root - never
    run by any pipeline, only by a user's explicit command. A project the peer holds
    under a key a former path of the checkout gave is written under the current key
    (issues/1058), so that a rename leaves one project in every room."""
    log = Log(LIVE, 'did' if apply else 'would')
    for proj in sorted(d for d in bundle.glob('-Users-*') if d.is_dir()):
        dest = dest_root / current_key(proj.name)
        for s in sorted(proj.glob('*.jsonl')):
            _pull_session(proj, dest, s, apply, log)
    return log


def pull_move(bundle_proj: Path, dest_root: Path, session: Path, apply: bool) -> Log:
    log = Log(LIVE, 'did' if apply else 'would')
    _pull_session(bundle_proj, dest_root / current_key(bundle_proj.name), session, apply, log)
    return log
