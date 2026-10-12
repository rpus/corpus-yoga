#!/usr/bin/env python
"""
harness.py - the Antigravity adapter (#633), from the store as observed on
home-room 2026-09-14 (Antigravity 2.13.0): a session is brain/<uuid>/ with its
transcript at .system_generated/logs/transcript.jsonl (one JSON object per
step) and transcript_full.jsonl beside it, a steps/ directory where present,
the step database conversations/<uuid>.db (sqlite, payloads protobuf), and its
row in conversation_summaries.db at the store's root (title, step count,
workspace uris, project id, status). The store keeps a session as
<machine>/<project>/<uuid>/: the two transcripts placed append-only (a copy
supersedes an existing one iff the existing bytes are a prefix of it), steps/
with the same semantics per file, conversation.db as a consistent snapshot
taken through sqlite's backup API and replaced whenever the transcript
advanced, and summary.json, the summaries row, replaced when it changed. The
model a step ran on sits inside the step database's protobuf payloads and is
not decoded here - #634 describes that record; model_rows says so.
"""
import json
import sqlite3
import sys
import tempfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

SELF = 'src/main/cli/agent/gemini/harness.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))
from transport import LIVE, STAGE, STORE, Log, Relation, Session, fact, may_replace, outcome, place_tree, project_key, relate, strings  # noqa: E402

PROVIDER = 'gemini'
TRANSCRIPTS = ('transcript.jsonl', 'transcript_full.jsonl')
SUMMARY_COLUMNS = ('conversation_id', 'title', 'preview', 'step_count', 'last_modified_time',
                   'workspace_uris', 'status', 'source', 'project_id', 'agent_name',
                   'last_user_input_time')
MODEL_UNDECODED = '(undecoded: the step database is protobuf - #634)'


def _summaries(mount: Path) -> dict[str, dict]:
    """The summaries rows by session id, read from the live database read-only."""
    db = mount / 'conversation_summaries.db'
    if not db.is_file():
        return {}
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        rows = con.execute(f'select {", ".join(SUMMARY_COLUMNS)} from conversation_summaries').fetchall()
    finally:
        con.close()
    return {r[0]: dict(zip(SUMMARY_COLUMNS, r)) for r in rows}


def _project(summary: dict) -> str:
    """The store's project key from the first workspace uri; a session with no
    workspace files under no-workspace."""
    try:
        uris = json.loads(summary.get('workspace_uris') or '[]')
    except ValueError:
        uris = []
    first = uris[0] if uris else ''
    return project_key(first.removeprefix('file://')) if first.startswith('file://') else 'no-workspace'


def _brain(mount: Path, session_id: str) -> Path:
    return mount / 'brain' / session_id


def _logs(brain: Path) -> Path:
    return brain / '.system_generated' / 'logs'


def _size(paths: list[Path]) -> int:
    return sum(p.stat().st_size for p in paths if p.is_file())


def live_sessions(mount: Path) -> list[Session]:
    out = []
    for session_id, summary in sorted(_summaries(mount).items()):
        brain = _brain(mount, session_id)
        transcript = _logs(brain) / TRANSCRIPTS[0]
        if not transcript.is_file():
            continue
        db = mount / 'conversations' / f'{session_id}.db'
        out.append(Session(PROVIDER, session_id, _project(summary), brain,
                           summary.get('title') or '(untitled)',
                           _size([_logs(brain) / t for t in TRANSCRIPTS] + [db]),
                           transcript.stat().st_mtime))
    return out


def held_sessions(machine_dir: Path) -> list[Session]:
    out = []
    for proj in sorted(d for d in machine_dir.iterdir() if d.is_dir()):
        for s in sorted(d for d in proj.iterdir() if d.is_dir()):
            summary_file = s / 'summary.json'
            if not summary_file.is_file():
                continue
            summary = json.loads(summary_file.read_text())
            transcript = s / TRANSCRIPTS[0]
            out.append(Session(PROVIDER, s.name, proj.name, s, summary.get('title') or '(untitled)',
                               _size([s / t for t in TRANSCRIPTS] + [s / 'conversation.db']),
                               transcript.stat().st_mtime if transcript.is_file() else 0.0))
    return out


def written(session: Session) -> Iterator[str]:
    """Every string a tool call of the session carried as its arguments - the commands
    it ran, the files it wrote - in the record's order (#631); from the full transcript
    where the session has one, since the other truncates long fields."""
    logs = [d / t for t in reversed(TRANSCRIPTS) for d in (session.path, _logs(session.path))]
    log = next((p for p in logs if p.is_file()), None)
    if log is None:
        return
    with log.open() as f:
        for line in f:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            for call in record.get('tool_calls') or []:
                if isinstance(call, dict):
                    yield from strings(call.get('args'))


def _snapshot(db: Path) -> bytes:
    """A consistent copy of a live sqlite database (it may have a write-ahead
    log open): the backup API, never a file copy."""
    src = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        dst = sqlite3.connect(tmp.name)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return Path(tmp.name).read_bytes()


def _capture_session(mount: Path, session: Session, summary: dict, dest: Path, held: Path, log: Log) -> bool:
    """Mirror one session into <outbox>/<project>/<uuid>/, said into the log under its
    outcome by its address with each file's relation beneath (#857). Where the stage holds
    no copy, the held one under held is the baseline (#850): transcripts the store holds
    identical or ahead are not staged and nothing else of the unit is written, one that
    diverges from the held copy is a CONFLICT, as the promote would say, and one that
    extends it is written to the stage. Returns whether the session conflicted."""
    address = f'{session.project}/{session.id}/'
    facts: dict[str, object] = {}
    against_store = not dest.is_dir() and held.is_dir()
    base, base_root = (held, STORE) if against_store else (dest, STAGE)
    written = conflict = advanced = False
    for name in TRANSCRIPTS:
        src = _logs(session.path) / name
        if not src.is_file():
            continue
        data = src.read_bytes()
        existing = (base / name).read_bytes() if (base / name).is_file() else None
        relation = relate(data, existing)
        if may_replace(relation):
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            (dest / name).write_bytes(data)
            written = advanced = True
        conflict = conflict or relation is Relation.DIVERGED
        facts[name] = fact(relation, data, existing, LIVE, base_root)
    if against_store and not advanced:
        # the store holds every transcript level, or one diverged: nothing of the unit is
        # staged, so its record and its snapshot are not written either
        log.say('conflict' if conflict else 'kept', address, facts, 'session')
        return conflict
    placed = place_tree(session.path / 'steps', dest / 'steps', True, LIVE, STAGE)
    if placed is not None:
        facts['steps/'] = placed[1]
        conflict = conflict or placed[0] == 'conflict'
        written = written or placed[0] == 'wrote'
    db = mount / 'conversations' / f'{session.id}.db'
    if conflict:
        facts['conversation.db'] = 'withheld - a transcript conflicted; the record transports as a product'
    elif db.is_file() and (advanced or not (dest / 'conversation.db').is_file()):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / 'conversation.db').write_bytes(_snapshot(db))
        facts['conversation.db'] = 'snapshot written - the transcript advanced'
        written = True
    elif db.is_file():
        facts['conversation.db'] = 'snapshot kept - the transcript did not advance'
    rendered = json.dumps(summary, sort_keys=True, indent=2) + '\n'
    summary_file = dest / 'summary.json'
    existed = summary_file.is_file()
    if not conflict and (not existed or summary_file.read_text() != rendered):
        dest.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(rendered)
        facts['summary.json'] = 'updated' if existed else 'written'
        written = True
    log.say('conflict' if conflict else 'wrote' if written else 'kept', address, facts, 'session')
    return conflict


def capture(mount: Path, outbox: Path, held: Path, uuid8: str | None) -> Log:
    summaries = _summaries(mount)
    sessions = live_sessions(mount)
    if uuid8 is not None:
        matches = [s for s in sessions if s.id.startswith(uuid8)]
        if not matches:
            sys.exit(f'error: no session matching {uuid8!r} in {mount}')
        if len(matches) > 1:
            sys.exit(f'error: {uuid8!r} is ambiguous here - matches: ' + ', '.join(s.id[:8] for s in matches))
        sessions = matches
    log = Log(STAGE)
    for s in sessions:
        _capture_session(mount, s, summaries[s.id], outbox / s.project / s.id, held / s.project / s.id, log)
    return log


def model_rows(mount: Path) -> list[tuple[str, str, str, int]]:
    """One row per session: the model is held undecoded, the records counted are
    the transcript's steps."""
    rows = []
    for s in live_sessions(mount):
        transcript = _logs(s.path) / TRANSCRIPTS[0]
        steps = sum(1 for _ in transcript.open(errors='replace'))
        rows.append((s.project, s.id[:8], MODEL_UNDECODED, steps))
    return rows
