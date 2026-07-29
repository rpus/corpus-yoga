#!/usr/bin/env python
"""
agent.py — CAPTURE agents into the store; RECEIVE them from peer machines.

The calculus (rsc/CALCULUS.md): an agent is the product session × memory;
the underlying operation is TRANSPORT — identity-preserving cp, componentwise,
with each component's class semantics enforced — and capture is that operation
pointed homeward: live projects root → the store. A session is append-only, so a copy supersedes an
existing one iff the existing bytes are a PREFIX of it; anything else is a
loud CONFLICT. A memory folder is a set of one-fact-per-file documents whose
NAMES are dressing (the fact is the identity) plus one index: on receive a
novel leaf copies in, an identical one skips, one the incoming EXTENDS is
superseded in place (an appendix), and true divergence keeps BOTH — the
incoming fact re-dressed as <stem>.<machine>.md with its [[links]] following —
while MEMORY.md unions by novelty-append. Nothing is overwritten silently
(L6), nothing is lost (L4), and reconciliation of diverged facts remains a
human act — recorded in-folder rather than blocking the transport ("hone,
not clone": the twins are the fork, made visible). Re-running either
direction on an unchanged pair is silence (L1).

Machines and projects: transported agents live in the STORE — data/input/claude/code/machine-transport,
a hand-made symlink on each machine to the same medium — keyed
<machine>/<project>/<session>.jsonl + <machine>/<project>/<session-uuid>/ (the
eponymous workspace: subagent transcripts and persisted tool-results the log
REFERENCES, moved with log semantics per file) + <machine>/<project>/memory/.
Provenance is spatial and sender-declared: capture takes no destination —
it mirrors EVERY project in the projects root into data/input/claude/code/machine-transport/<own
machine>/, the machine read from the rooted machine-name.txt binding, which
rsc/machine/machines.csv must declare — and receive --from names the peer machine(s) whose sessions
to merge, the twin-dressing and marker label coming from that ADDRESS rather
than the receiver's assertion. An outbox is single-writer by construction, so
capture MIRRORS each project's memory (updated in place, absentees
removed); every merge subtlety lives in receive, where two agents actually
meet.

The projects root is ext/claude-code-projects (link_projects.sh's symlink to the Claude Code
projects folder) — HARNESS-OWNED state that Anthropic expires at will. The
doctrine: capture is the one READER of it — sweep early, sweep often; receive is the one WRITER of it, and only ever by a user's
explicit --apply, never a pipeline's. The pipelines source from the store,
which the repo owns and the medium carries.

data/input/claude/code/machine-transport is a git ORIGIN in all but name, and exactly so for append-only
artifacts: a session log contains every prior state of itself as a byte
prefix, so the latest copy IS the whole history and place_log's prefix check
is a fast-forward gate — no commit chain needed, a dumb file store suffices.
Each machine's dir is a single-writer branch (a machine pushes only its own ref);
capture is a fast-forward-only push ('destination is ahead' is the refused
stale force-push); receive is fetch-plus-merge, dry-run first; two machines
extending the same session are diverged branches, refused until a human
merges. And memory/ is the actual REPOSITORY of the pair — the component
where real merges happen: the marker block in MEMORY.md is the merge commit
(it records what came in and licenses demerge, the exact revert), diverged
facts persist as machine-dressed twin branches, and the index unions like a
tree merge. The session is history; the memory is the repo.

Received merges are DETECTABLE and INVERTIBLE: a receive that changes the
memory writes a marker block into MEMORY.md — begin/end comments wrapping the
unioned index lines, plus one act line per file action with content hash and
lengths — and `demerge` undoes the LATEST block exactly (delete the additions,
truncate the appendices, drop the block), all-or-nothing, refusing loudly if
anything was edited since the merge: the record licenses the undo (L3). This
is what makes safe VISITS possible — an agent received while the host is away
extracts by transporting itself home, and the host demerges the residue.

    yoga agent
    yoga agent list-models
    yoga agent capture --session <uuid8> [--to <scratch-dir>]
    yoga agent receive   --session <uuid8> --from <machine|dir> [--apply]
    yoga agent capture --all [--to <scratch-dir>]
    yoga agent receive   --all --from <machine|dir> [--apply]
    yoga agent demerge [--apply]

capture and receive each take --session <uuid8> (matches by uuid prefix,
exactly one) or --all: a NAMED agent or the named TOTALITY — git push --all /
pull --all, safe because each per-session placement independently lands on
the lattice (silence / fast-forward / ahead / loud CONFLICT), and the memory
component moves ONCE either way (mirrored out; merged in under a single
marker block, so `receive --all --from <machine>` is still one demerge). What is never
accepted is an INFERENCE: no recency guessing, no automatic choice. receive
stays dry-run by default regardless — --apply is the write gate, totality or
not.

The endpoint asymmetry is the model, not an accident: capture takes NO
destination — it pushes this machine's own ref, the only legal one
(single-writer branches) — so --to is purely a scratch/test escape hatch and
takes a bare directory, never a machine name. receive must NAME its source ref:
a peer machine under data/input/claude/code/machine-transport, or (the same scratch affordance, symmetric) a
directory. The two are distinguished by SHAPE, never by lookup: a bare token
is a machine, a path-shaped token (containing '/') is a directory — so meaning
never depends on the CWD.

capture writes to the store immediately (it is not precious).
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
import contextlib
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / 'ext' / 'claude-code-projects'
AGENTS_DIR = REPO / 'data' / 'input' / 'claude' / 'code' / 'machine-transport'

sys.path.insert(0, str(REPO / 'src'))  # argparse_help — modules both tiers import
sys.path.insert(0, str(REPO / 'src' / 'main'))  # machine.py owns the machine binding
from machine import bound_machine  # noqa: E402
from argparse_help import enrich  # noqa: E402


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _sha_lines(text: str) -> str:
    """Line-canonical hash (trailing-newline-insensitive) — used where the
    hashed content is reconstructed from splitlines at demerge time."""
    return _sha('\n'.join(text.splitlines()))


def own_outbox() -> Path:
    """The remote this machine writes: data/input/claude/code/machine-transport/<its machine-name.txt binding>.
    data/input/claude/code/machine-transport itself is hand-made; the machine's subdirectory inside it is ours."""
    if not AGENTS_DIR.is_dir():
        sys.exit('error: data/input/claude/code/machine-transport missing — hand-make it as a symlink to the '
                 'shared store (one subdirectory per machine name, projects nested within)')
    out = AGENTS_DIR / bound_machine()
    out.mkdir(exist_ok=True)
    return out


def peer_bundle(name: str) -> Path:
    """A source for receive: a MACHINE NAME or a DIRECTORY, distinguished by shape,
    never by lookup — machines are names (bare tokens, resolved under data/input/claude/code/machine-transport,
    loud error if absent), places are paths (anything containing '/' or starting
    '~'; a scratch dir beside you is spelled ./like-this). A bare token never
    consults the CWD, so what a command means cannot depend on where you stand
    (the old heuristic tried the CWD first: a local folder named like a machine
    silently shadowed the machine's directory under data/input/claude/code/machine-transport)."""
    if '/' in name or name.startswith('~'):
        return Path(name).expanduser()
    machine = AGENTS_DIR / name
    if not machine.is_dir():
        machines = sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir()) if AGENTS_DIR.is_dir() else []
        sys.exit(f"error: no data/input/claude/code/machine-transport/{name}/ — machines present: "
                 f"{', '.join(machines) or '(none)'} "
                 f"(a directory source is path-shaped: ./{name})")
    return machine


def pick_session(root: Path, uuid8: str) -> Path:
    """The session to move, by IDENTITY: the --session uuid prefix must match
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
                 + ', '.join(s.stem[:8] for s in matches))
    return matches[0]


def place_log(data: bytes, dest: Path, apply: bool) -> tuple[str, str]:
    """Append-only placement — the five-state prefix lattice: new (absent →
    written) / identical (L1 silence) / extends (existing is a strict prefix:
    the fast-forward, superseded in place) / ahead (incoming is the prefix: a
    stale stash never truncates — the refused force-push, so replaying old
    transports is idempotent) / conflict (neither prefixes the other: diverged
    twins, loud, nothing written, human merge). Successive stashes from one
    source ratchet new → extends → … → identical; divergence is unreachable
    from a single well-behaved writer. Returns (kind, detail): the lattice
    state plus the byte counts for extends. The lattice is direction-blind;
    the SENTENCE is not — wording is the caller's, via word_placement."""
    if not dest.exists():
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        return 'new', ''
    have = dest.read_bytes()
    if have == data:
        return 'identical', ''
    if data[:len(have)] == have:
        if apply:
            dest.write_bytes(data)
        return 'extends', f'{len(have)} → {len(data)} bytes'
    if have[:len(data)] == data:
        return 'ahead', ''
    return 'conflict', ''


def word_placement(kind: str, detail: str, src: str, dest: str) -> str:
    """One lattice state as one sentence, both sides NAMED — noun extends noun
    (user specification, 2026-07-11): the opposition is local/remote, never a
    pronoun without an antecedent, never a metonym. A machine name is an ADDRESS
    (which remote), not a side — both sides of a transport belong to the same
    machine, so the name lives in the header/tail, not in the relation."""
    return {
        'new':       f'nothing in {dest} yet — written',
        'identical': f'{src} and {dest} hold identical bytes — no-op',
        'extends':   f'{src} extends {dest} ({detail}) — {dest} copy superseded',
        'ahead':     f'{dest} is ahead of {src} — no-op',
        'conflict':  f'✗ CONFLICT: {src} and {dest} diverged — {dest} copy left in place',
    }[kind]


def place_session(src: Path, dest: Path, apply: bool) -> tuple[str, str]:
    return place_log(src.read_bytes(), dest, apply)


def move_workspace(src_ws: Path, dest_ws: Path, apply: bool,
                   src_label: str, dest_label: str) -> tuple[int, bool, bool]:
    """The session's eponymous workspace (subagent transcripts, persisted
    tool-results — files the session log REFERENCES) rides along. The
    filesystem, checked here and now, is the only oracle — no reconstruction
    of what "ever existed": a destination folder that is absent takes the
    workspace wholesale as a unit; one that is present (however it came to be)
    merges with log semantics per file — new / identical / prefix-superseded;
    divergence a loud CONFLICT, worded with both sides named (src_label /
    dest_label). Returns (conflicts, wrote, eventful): wrote is
    bytes-changed-at-destination; eventful adds anything else worth eyes
    (ahead files, conflicts) — L1 silence is neither."""
    if not src_ws.is_dir():
        return 0, False, False
    files = sorted(p for p in src_ws.rglob('*') if p.is_file() and p.name != '.DS_Store')
    if not dest_ws.exists():
        print(f'  workspace {src_ws.name}/: nothing in {dest_label} yet — '
              f'written whole ({len(files)} file(s))')
        if apply:
            for f in files:
                dest = dest_ws / f.relative_to(src_ws)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        return 0, True, True
    tally = {'new': 0, 'identical': 0, 'extends': 0, 'ahead': 0}
    conflicts = 0
    for f in files:
        rel = f.relative_to(src_ws)
        kind, detail = place_log(f.read_bytes(), dest_ws / rel, apply)
        if kind == 'conflict':
            print(f'  workspace/{rel}: {word_placement(kind, detail, src_label, dest_label)}')
            conflicts += 1
        else:
            tally[kind] += 1
    print(f'  workspace {src_ws.name}/: '
          + ', '.join(f'{n} {k}' for k, n in tally.items() if n)
          + (f', {conflicts} CONFLICT(S)' if conflicts else '')
          if any(tally.values()) or conflicts else
          f'  workspace {src_ws.name}/: empty')
    wrote = bool(tally['new'] or tally['extends'])
    return conflicts, wrote, wrote or bool(conflicts or tally['ahead'])


def merge_memory(src_dir: Path, dest_dir: Path, apply: bool, machine: str) -> int:
    """Memory-folder merge — RECEIVE only, where two agents actually meet
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


def list_agents() -> int:
    """The sidebar-independent census: every session in this machine's project
    and in each machine's store dir under data/input/claude/code/machine-transport, dressed with its LAST
    ai-title record — the title history rides the log, so this works
    identically on live and transported sessions, and the dressing is derived on demand,
    never stored (L5). Framing on stderr; data lines on stdout (pipeable)."""
    rows = []

    def scan(where: str, d: Path) -> None:
        for f in sorted(d.glob('*.jsonl')):
            title = '(untitled)'
            for line in f.open(errors='replace'):
                if '"ai-title"' in line:
                    try:
                        title = json.loads(line).get('aiTitle') or title
                    except ValueError:
                        continue
            st = f.stat()
            rows.append((f.stem[:8], where, st.st_size, st.st_mtime, title))

    for proj in sorted(d for d in PROJECTS.glob('-Users-*') if d.is_dir()):
        scan('local', proj)
    if AGENTS_DIR.is_dir():
        for machine in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
            for proj in sorted(d for d in machine.glob('-Users-*') if d.is_dir()):
                scan(machine.name, proj)
    print(f'{"uuid8":<8}  {"where":<14}  {"size":>7}  {"last-write":<16}  title', file=sys.stderr)
    for u8, where, size, mtime, title in rows:
        t = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        print(f'{u8}  {where:<14}  {size / 1e6:6.1f}M  {t}  {title}')
    return 0


def model_census() -> int:
    """Aggregate message.model over every "type":"assistant" record across ALL
    coding sessions in this machine's projects root — every project, main
    sessions and their subagents. The copies under data/input/claude/code/machine-transport are of sessions
    counted here (or in their origin machine), so they are not counted. The model is a
    per-RECORD fact, so a mid-session switch — elective /model or forced
    fallback — shows as a mixed session; '<synthetic>' rows are harness-authored
    records (no model spoke). Framing on stderr; data lines on stdout
    (pipeable), derived on demand, never stored (L5)."""
    rows = []
    total = Counter()
    for proj in sorted(p for p in PROJECTS.iterdir() if p.is_dir()):
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
                total[model] += 1
        rows += [(proj.name, b, buckets[b]) for b in sorted(buckets)]
    print(f'{"project":<52}  {"session":<9}  {"model":<22}  {"records":>7}', file=sys.stderr)
    for proj_name, bucket, counts in rows:
        for model, n in counts.most_common():
            print(f'{proj_name:<52}  {bucket:<9}  {model:<22}  {n:>7}')
    for model, n in total.most_common():
        print(f'{"(total)":<52}  {"":<9}  {model:<22}  {n:>7}')
    return 0


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
    receive, where two agents meet. Returns eventful (anything beyond L1
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
    kind, detail = place_session(session, dest_proj / session.name, apply=True)
    conflicts = 1 if kind == 'conflict' else 0
    ws_narration = io.StringIO()
    with contextlib.redirect_stdout(ws_narration):
        ws_conflicts, ws_wrote, ws_eventful = move_workspace(
            src_proj / session.stem, dest_proj / session.stem, apply=True,
            src_label='local', dest_label='remote')
    conflicts += ws_conflicts
    wrote = ws_wrote or kind in ('new', 'extends')
    eventful = wrote or bool(conflicts) or ws_eventful or kind != 'identical'
    if eventful or not quiet_noop:
        print(f'capture → {label}: {session.name}')
        print(f'  session: {word_placement(kind, detail, "local", "remote")}')
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


def _receive_session(bundle_proj: Path, dest_proj: Path, session: Path, apply: bool, machine: str) -> int:
    print(f'receive ← {machine}/{bundle_proj.name}: {session.name}')
    kind, detail = place_session(session, dest_proj / session.name, apply)
    print(f'  session: {word_placement(kind, detail, "remote", "local")}')
    ws_conflicts, _, _ = move_workspace(bundle_proj / session.stem, dest_proj / session.stem, apply,
                                        src_label='remote', dest_label='local')
    return (1 if kind == 'conflict' else 0) + ws_conflicts


def receive_all(bundle: Path, dest_root: Path, apply: bool, machine: str) -> int:
    """git pull --all from one peer: every session in every project the machine
    transported (and each project's memory, merged once per project — one
    marker block, one demerge, per project). The same lattice safety as
    capture --all, plus receive's own guard: dry-run unless --apply. This
    is the ONE deliberate writer of the harness-owned projects root — never
    run by any pipeline, only by a user's explicit command."""
    projects = sorted(d for d in bundle.glob('-Users-*') if d.is_dir())
    if not projects:
        print(f'error: no projects in {bundle}', file=sys.stderr)
        return 1
    conflicts = total = 0
    for proj in projects:
        for s in sorted(proj.glob('*.jsonl')):
            total += 1
            conflicts += _receive_session(proj, dest_root / proj.name, s, apply, machine)
        if (proj / 'memory').is_dir():
            conflicts += merge_memory(proj / 'memory', dest_root / proj.name / 'memory', apply, machine)
    print(f'{"DONE" if apply else "dry run — pass --apply to write into the projects root"}'
          f' — {total} session(s)' + (f', {conflicts} CONFLICT(S)' if conflicts else ''))
    return conflicts


def receive_move(bundle_proj: Path, dest_root: Path, session: Path, apply: bool, machine: str) -> int:
    conflicts = _receive_session(bundle_proj, dest_root / bundle_proj.name, session, apply, machine)
    conflicts += merge_memory(bundle_proj / 'memory', dest_root / bundle_proj.name / 'memory', apply, machine)
    print('DONE' if apply else 'dry run — pass --apply to write into the projects root')
    return conflicts


def main() -> int:
    ap = argparse.ArgumentParser(description='capture agents into the store; receive from peer machines (session × memory)')
    # bare noun → the census (status); not required, and there is no `list` verb (bare IS it)
    sub = ap.add_subparsers(dest='direction')
    t = sub.add_parser('capture')
    t.add_argument('--session')
    t.add_argument('--all', action='store_true')
    t.add_argument('--to', metavar='SCRATCH_DIR')
    r = sub.add_parser('receive')
    r.add_argument('--from', dest='source', required=True, metavar='MACHINE|DIR')
    r.add_argument('--session')
    r.add_argument('--all', action='store_true')
    r.add_argument('--apply', action='store_true')
    d = sub.add_parser('demerge')
    d.add_argument('--apply', action='store_true')
    sub.add_parser('list-models')
    enrich(ap, 'agent')
    args = ap.parse_args()

    if args.direction is None:
        return list_agents()   # bare noun → the census (local + store sessions), read-only status

    if not PROJECTS.is_dir():
        sys.exit(f'error: {PROJECTS.relative_to(REPO)} missing — src/main/code-agents/link_projects.sh creates the symlink')

    if args.direction == 'list-models':
        return model_census()

    if args.direction == 'demerge':
        # every local project's memory, newest merge each, all-or-nothing per
        # project (a markerless folder demerges to silence)
        rc = 0
        for proj in sorted(d for d in PROJECTS.glob('-Users-*') if d.is_dir()):
            print(f'{proj.name}:')
            rc = max(rc, 1 if demerge(proj, args.apply) else 0)
        return rc

    if args.direction in ('capture', 'receive') and bool(args.session) == args.all:
        ap.error(f'{args.direction}: name --session <uuid8> or --all — an agent or the totality, never an inference')

    if args.direction == 'capture':
        if args.to:
            outbox = Path(args.to).expanduser()
            outbox.mkdir(parents=True, exist_ok=True)
        else:
            outbox = own_outbox()
        if args.all:
            return 1 if capture_all(PROJECTS, outbox) else 0
        session = pick_session(PROJECTS, args.session)
        return 1 if capture_move(session.parent, outbox, session) else 0

    bundle = peer_bundle(args.source)
    # the twin-dressing and marker label: the source's ADDRESS — the origin machine's
    # name as it stands under data/input/claude/code/machine-transport (or the directory's own name for a path)
    machine = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in bundle.name) or 'incoming'
    if args.all:
        return 1 if receive_all(bundle, PROJECTS, args.apply, machine) else 0
    session = pick_session(bundle, args.session)
    return 1 if receive_move(session.parent, PROJECTS, session, args.apply, machine) else 0


if __name__ == '__main__':
    sys.exit(main())
