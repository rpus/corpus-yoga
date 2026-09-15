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
from datetime import datetime
from pathlib import Path

SELF = 'src/main/cli/agent/gemini/harness.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))
from transport import Relation, Session, move_workspace, place_log, project_key, word_placement  # noqa: E402

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


def _capture_session(mount: Path, session: Session, summary: dict, dest: Path,
                     quiet_noop: bool = False) -> tuple[int, bool, bool]:
    """Mirror one session into <outbox>/<project>/<uuid>/. Returns (conflicts,
    wrote, eventful) as the claude adapter's capture does."""
    lines = []
    conflicts, wrote, eventful = 0, False, False
    advanced = False
    for name in TRANSCRIPTS:
        src = _logs(session.path) / name
        if not src.is_file():
            continue
        relation, detail = place_log(src.read_bytes(), dest / name, apply=True)
        lines.append(f'  {name}: {word_placement(relation, detail, "local", "remote")}')
        if relation is Relation.DIVERGED:
            conflicts += 1
        if relation in (Relation.ABSENT, Relation.EXTENDS):
            wrote = True
            advanced = True
        if relation is not Relation.IDENTICAL:
            eventful = True
    steps_narration = []
    if (session.path / 'steps').is_dir():
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            c, w, e = move_workspace(session.path / 'steps', dest / 'steps', apply=True,
                                     src_label='local', dest_label='remote')
        conflicts += c
        wrote = wrote or w
        eventful = eventful or e
        steps_narration = buf.getvalue().splitlines()
    db = mount / 'conversations' / f'{session.id}.db'
    if conflicts:
        lines.append('  conversation.db: WITHHELD - transcript CONFLICT above; the record transports as a product')
    elif db.is_file() and (advanced or not (dest / 'conversation.db').is_file()):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / 'conversation.db').write_bytes(_snapshot(db))
        lines.append('  conversation.db: snapshot written (the transcript advanced)')
        wrote = eventful = True
    elif db.is_file():
        lines.append('  conversation.db: snapshot kept (the transcript did not advance)')
    rendered = json.dumps(summary, sort_keys=True, indent=2) + '\n'
    summary_file = dest / 'summary.json'
    existed = summary_file.is_file()
    if not conflicts and (not existed or summary_file.read_text() != rendered):
        dest.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(rendered)
        lines.append('  summary.json: ' + ('updated' if existed else 'written'))
        wrote = eventful = True
    if eventful or not quiet_noop:
        print(f'capture → {dest.parent.parent.name}/{session.project}: {session.id}')
        for line in lines + steps_narration:
            print(line)
    return conflicts, wrote, eventful


def capture(mount: Path, outbox: Path, uuid8: str | None) -> int:
    summaries = _summaries(mount)
    sessions = live_sessions(mount)
    if uuid8 is not None:
        matches = [s for s in sessions if s.id.startswith(uuid8)]
        if not matches:
            sys.exit(f'error: no session matching {uuid8!r} in {mount}')
        if len(matches) > 1:
            sys.exit(f'error: {uuid8!r} is ambiguous here - matches: ' + ', '.join(s.id[:8] for s in matches))
        sessions = matches
    if not sessions:
        print(f'error: no sessions under {mount}', file=sys.stderr)
        return 1
    conflicts, written, quiet = 0, 0, []
    for s in sessions:
        c, wrote, eventful = _capture_session(mount, s, summaries[s.id], outbox / s.project / s.id,
                                              quiet_noop=uuid8 is None)
        conflicts += c
        written += 1 if wrote else 0
        if not eventful:
            quiet.append(s.id[:8])
    if quiet:
        print(f'{len(quiet)} session(s) identical in local and remote: {", ".join(quiet)}')
    if conflicts:
        print(f'DONE — effect: {written} of {len(sessions)} session(s) written, {conflicts} CONFLICT(S); '
              f'postcondition: remote ({outbox.name}) does NOT yet hold everything local holds')
    elif written:
        print(f'DONE — effect: {written} of {len(sessions)} session(s) written; '
              f'postcondition: remote ({outbox.name}) holds everything local holds')
    else:
        print(f'DONE — no effect: remote ({outbox.name}) already held everything local holds')
    return conflicts


def model_rows(mount: Path) -> list[tuple[str, str, str, int]]:
    """One row per session: the model is held undecoded, the records counted are
    the transcript's steps."""
    rows = []
    for s in live_sessions(mount):
        transcript = _logs(s.path) / TRANSCRIPTS[0]
        steps = sum(1 for _ in transcript.open(errors='replace'))
        rows.append((s.project, s.id[:8], MODEL_UNDECODED, steps))
    return rows
