#!/usr/bin/env python
"""
agent.py — CAPTURE agents into the store; RECEIVE them from peer machines;
MOUNT the live stores - for every declared provider with a harness adapter (#633).

The calculus (rsc/CALCULUS.md): an agent is the product session × memory;
the underlying operation is TRANSPORT — identity-preserving cp, componentwise,
with each component's class semantics enforced — and capture is that operation
pointed homeward: live projects root → the store. A session is append-only, so a copy supersedes an
existing one iff the existing bytes are a PREFIX of it; anything else is a
loud CONFLICT. A memory folder is a set of one-fact-per-file documents whose
NAMES are dressing (the fact is the identity) plus one index: on install a
novel leaf copies in, an identical one skips, one the incoming EXTENDS is
superseded in place (an appendix), and true divergence keeps BOTH — the
incoming fact re-dressed as <stem>.<machine>.md with its [[links]] following —
while MEMORY.md unions by novelty-append. Nothing is overwritten silently
(L6), nothing is lost (L4), and reconciliation of diverged facts remains a
human act — recorded in-folder rather than blocking the transport ("hone,
not clone": the twins are the fork, made visible). Re-running either
direction on an unchanged pair is silence (L1).

Providers and harnesses: a provider's harness (Claude Code for claude,
Antigravity for gemini) keeps a live session store of its own shape, mounted at
ext/mnt/agent/<provider> per the registry (rsc/provider/providers.csv, #636) -
HARNESS-OWNED state the provider expires at will. Each shape is one adapter,
src/main/cli/agent/<provider>/harness.py, keeping the contract transport.py
states (#633); this driver knows no shape. Transported agents live in the
STORE, data/input/<provider>/code/machine-transport - a hand-made symlink on
each machine to the same medium - keyed <machine>/<project>/..., the project
being Claude Code's encoding of the workspace path in every provider's store.
For claude that is <project>/<session>.jsonl + <project>/<session-uuid>/ (the
eponymous workspace: subagent transcripts and persisted tool-results the log
REFERENCES, moved with log semantics per file) + <project>/memory/; for gemini
<project>/<uuid>/ with the transcripts, the steps, a snapshot of the step
database and the summaries row (the gemini adapter's header states it).
Provenance is spatial and sender-declared: capture takes no destination - it
mirrors every session of every served provider into that provider's store
under <own machine>/, the machine read from the rooted machine-name.txt
binding, which rsc/machine/machines.csv must declare - and install --from
names the peer machine whose sessions to merge, the twin-dressing and marker
label coming from that ADDRESS rather than the receiver's assertion. An
outbox is single-writer by construction, so capture MIRRORS each project's
memory (updated in place, absentees removed); every merge subtlety lives in
install, where two agents actually meet. The doctrine: capture is the one
READER of a live store - sweep early, sweep often; install is the one WRITER
of it, only ever by a user's explicit --apply, never a pipeline's, and serves
claude alone: writing into Antigravity's databases is no transport this verb
vouches for. The pipelines source from the store, which the repo owns and the
medium carries.

A provider's store is a git ORIGIN in all but name, and exactly so for append-only
artifacts: a session log contains every prior state of itself as a byte
prefix, so the latest copy IS the whole history and place_log's prefix check
is a fast-forward gate — no commit chain needed, a dumb file store suffices.
Each machine's dir is a single-writer branch (a machine pushes only its own ref);
capture is a fast-forward-only push ('destination is ahead' is the refused
stale force-push); install is fetch-plus-merge, dry-run first; two machines
extending the same session are diverged branches, refused until a human
merges. And memory/ is the actual REPOSITORY of the pair — the component
where real merges happen: the marker block in MEMORY.md is the merge commit
(it records what came in and licenses demerge, the exact revert), diverged
facts persist as machine-dressed twin branches, and the index unions like a
tree merge. The session is history; the memory is the repo.

Installed merges are DETECTABLE and INVERTIBLE: an install that changes the
memory writes a marker block into MEMORY.md — begin/end comments wrapping the
unioned index lines, plus one act line per file action with content hash and
lengths — and `demerge` undoes the LATEST block exactly (delete the additions,
truncate the appendices, drop the block), all-or-nothing, refusing loudly if
anything was edited since the merge: the record licenses the undo (L3). This
is what makes safe VISITS possible — an agent installed while the host is away
extracts by transporting itself home, and the host demerges the residue.

    corpus-yoga agent
    corpus-yoga agent list-models
    corpus-yoga agent mount [--apply]
    corpus-yoga agent capture --session <uuid8> [--to <scratch-dir>]
    corpus-yoga agent capture --provider <provider> [--to <scratch-dir>]
    corpus-yoga agent install   --session <uuid8> --from <machine|dir> [--apply]
    corpus-yoga agent capture --all [--to <scratch-dir>]
    corpus-yoga agent install   --all --from <machine|dir> [--apply]
    corpus-yoga agent demerge [--apply]

capture takes --session <uuid8> (matches by uuid prefix, exactly one), --provider
<name> (every session of one provider) or --all; install takes --session or --all:
a NAMED agent, a named provider's totality, or the named TOTALITY — git push --all /
pull --all, safe because each per-session placement independently lands on
the lattice (silence / fast-forward / ahead / loud CONFLICT), and the memory
component moves ONCE either way (mirrored out; merged in under a single
marker block, so `install --all --from <machine>` is still one demerge). What is never
accepted is an INFERENCE: no recency guessing, no automatic choice. install
stays dry-run by default regardless — --apply is the write gate, totality or
not.

The endpoint asymmetry is the model, not an accident: capture takes NO
destination — it pushes this machine's own ref, the only legal one
(single-writer branches) — so --to is purely a scratch/test escape hatch and
takes a bare directory, never a machine name - each provider's sessions land
under <scratch-dir>/<provider>/. install must NAME its source ref:
a peer machine under claude's store, or (the same scratch affordance, symmetric) a
directory. The two are distinguished by SHAPE, never by lookup: a bare token
is a machine, a path-shaped token (containing '/') is a directory — so meaning
never depends on the CWD.

capture writes to the store immediately (it is not precious).
install and demerge are dry-run by default and only --apply writes into this
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
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

SELF = 'src/main/cli/agent/agent.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

sys.path.insert(0, str(REPO / 'src'))  # declared_parser — modules both tiers import
sys.path.insert(0, str(REPO / 'src' / 'main'))  # machine.py owns the machine binding
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))  # the transport contract
from machine import bound_machine  # noqa: E402
from declared_parser import command_parser  # noqa: E402
import provider as registry  # noqa: E402
import transport  # noqa: E402


def served() -> list[tuple[dict, Path, ModuleType]]:
    """Every declared provider the verb serves: its row, its mount and its
    adapter - a provider without an adapter is declared and not served, and a
    served provider whose mount is absent is named where a census or capture
    would otherwise omit it in silence."""
    out = []
    for row in registry.providers():
        mount_path = registry.mount(row)
        adapter = transport.adapter(row['provider'])
        if mount_path is not None and adapter is not None:
            out.append((row, mount_path, adapter))
    return out


def own_outbox(provider: str) -> Path | None:
    """The remote this machine writes for a provider:
    data/input/<provider>/code/machine-transport/<its machine-name.txt binding>.
    The store itself is hand-made; the machine's subdirectory inside it is ours.
    None where the store is absent: a sweep states the skip and its remedy
    rather than stopping between providers."""
    store = transport.store(provider)
    if not store.is_dir():
        print(f'{provider}: {store.relative_to(REPO)} missing — hand-make it as a symlink to the '
              'shared store (one subdirectory per machine name, projects nested within); skipped',
              file=sys.stderr)
        return None
    out = store / bound_machine()
    out.mkdir(exist_ok=True)
    return out


def peer_bundle(name: str) -> Path:
    """A source for install: a MACHINE NAME or a DIRECTORY, distinguished by shape,
    never by lookup — machines are names (bare tokens, resolved under claude's store,
    loud error if absent), places are paths (anything containing '/' or starting
    '~'; a scratch dir beside you is spelled ./like-this). A bare token never
    consults the CWD, so what a command means cannot depend on where you stand."""
    if '/' in name or name.startswith('~'):
        return Path(name).expanduser()
    store = transport.store('claude')
    machine = store / name
    if not machine.is_dir():
        machines = sorted(d.name for d in store.iterdir() if d.is_dir()) if store.is_dir() else []
        sys.exit(f"error: no {store.relative_to(REPO)}/{name}/ — machines present: "
                 f"{', '.join(machines) or '(none)'} "
                 f"(a directory source is path-shaped: ./{name})")
    return machine


def list_agents() -> int:
    """The sidebar-independent census: every session in each served provider's
    live store and in each machine's dir of that provider's store, dressed with
    its title as the adapter reads it - derived on demand, never stored (L5).
    Framing on stderr; data lines on stdout (pipeable)."""
    rows: list[tuple[transport.Session, str]] = []
    for row, mount_path, adapter in served():
        provider = row['provider']
        if mount_path.is_dir():
            rows += [(s, 'local') for s in adapter.live_sessions(mount_path)]
        else:
            # a census that silently omits a side is a lie of absence: say which rows
            # cannot appear and how to make them appear
            print(f'note: {mount_path.relative_to(REPO)} absent — no local {provider} rows '
                  '→ run: corpus-yoga prerequisites sync --apply', file=sys.stderr)
        store = transport.store(provider)
        if store.is_dir():
            for machine in sorted(p for p in store.iterdir() if p.is_dir()):
                rows += [(s, machine.name) for s in adapter.held_sessions(machine)]
    print(f'{"uuid8":<8}  {"provider":<8}  {"where":<14}  {"size":>7}  {"last-write":<16}  title', file=sys.stderr)
    for s, where in rows:
        t = datetime.fromtimestamp(s.mtime).strftime('%Y-%m-%d %H:%M')
        print(f'{s.id[:8]}  {s.provider:<8}  {where:<14}  {s.size / 1e6:6.1f}M  {t}  {s.title}')
    return 0


def model_census() -> int:
    """The model per session across every served provider's live store, as each
    adapter reads its records - the copies in the stores are of sessions
    counted here (or on their origin machine), so they are not counted. A
    provider whose record holds the model undecoded says so in the model
    column. Framing on stderr; data lines on stdout (pipeable), derived on
    demand, never stored (L5)."""
    print(f'{"provider":<8}  {"project":<52}  {"session":<9}  {"model":<22}  {"records":>7}', file=sys.stderr)
    for row, mount_path, adapter in served():
        if not mount_path.is_dir():
            continue
        for project, session, model, n in adapter.model_rows(mount_path):
            print(f'{row["provider"]:<8}  {project:<52}  {session:<9}  {model:<22}  {n:>7}')
    return 0


def capture(uuid8: str | None, to: str | None, provider: str | None) -> int:
    """Three named extents, one per call: --session <uuid8> is one session,
    found across every served provider; --provider <name> is every session of
    that provider; --all is every session of every served provider whose mount
    is present - each provider into its own store."""
    if provider is not None and provider not in [row['provider'] for row, _, _ in served()]:
        sys.exit(f'error: {provider!r} is not a provider the agent verb serves — served: '
                 + ', '.join(row['provider'] for row, _, _ in served()))
    targets = [(row, mount_path, adapter) for row, mount_path, adapter in served()
               if mount_path.is_dir() and (provider is None or row['provider'] == provider)]
    if not targets:
        sys.exit('error: no live store mounted — corpus-yoga agent mount --apply creates the symlinks')
    if uuid8 is not None:
        matches = [(row, mount_path, adapter, s) for row, mount_path, adapter in targets
                   for s in adapter.live_sessions(mount_path) if s.id.startswith(uuid8)]
        if not matches:
            sys.exit(f'error: no session matching {uuid8!r} in any live store')
        if len(matches) > 1:
            sys.exit(f'error: {uuid8!r} is ambiguous — matches: '
                     + ', '.join(f'{s.provider}/{s.id[:8]}' for _, _, _, s in matches))
        targets = [matches[0][:3]]
    conflicts = 0
    for row, mount_path, adapter in targets:
        name = row['provider']
        if to:
            outbox = Path(to).expanduser() / name
            outbox.mkdir(parents=True, exist_ok=True)
        else:
            outbox = own_outbox(name)
            if outbox is None:
                continue
        print(f'── {name}: {mount_path.relative_to(REPO)} → {outbox.relative_to(REPO) if outbox.is_relative_to(REPO) else outbox}')
        conflicts += adapter.capture(mount_path, outbox, uuid8)
    return conflicts


def _claude() -> tuple[Path, ModuleType]:
    """install and demerge write into Claude Code's projects root: the one
    adapter that vouches for a write into a live store."""
    row = registry.provider('claude')
    mount_path, adapter = registry.mount(row), transport.adapter('claude')
    assert mount_path is not None and adapter is not None
    if not mount_path.is_dir():
        sys.exit(f'error: {mount_path.relative_to(REPO)} missing — corpus-yoga agent mount --apply creates the symlink')
    return mount_path, adapter


def mount(apply: bool) -> int:
    """The live agent stores mounted under ext/mnt/agent/<provider> (#636): one
    symlink per declared provider whose live store this machine holds, the target
    from the registry row. A dry run states every move as data - each provider
    accounted for, and every link at a retired address (rsc/naming/mount_vintages.csv)
    named as an orphan with its rm - and --apply creates the links. Orphans are
    named, never removed: the disposal is the reader's act."""
    root = registry.MOUNT_ROOT
    verdict = 0
    for row in registry.providers():
        live = registry.live_store(row)
        target = root / row['provider']
        shown = target.relative_to(REPO)
        if live is None:
            print(f'{shown}: {row["provider"]} observes no live store - nothing to mount')
            continue
        if not live.is_dir():
            print(f'{shown}: {row["live_store"]} absent on this machine - nothing to mount')
            continue
        if target.is_symlink() and target.resolve() == live.resolve():
            print(f'{shown} → {row["live_store"]} (present)')
            continue
        if target.exists() or target.is_symlink():
            print(f'{shown}: exists and is not the link to {row["live_store"]} - not touched; remove it by hand')
            verdict = 1
            continue
        if apply:
            root.mkdir(parents=True, exist_ok=True)
            target.symlink_to(live)
            print(f'{shown} → {row["live_store"]} (created)')
        else:
            print(f'{shown} → {row["live_store"]} (would create; --apply creates it)')
    for rel, vintage_id in registry.retired_mounts():
        print(f'orphan: {rel} (mount vintage {vintage_id}, rsc/naming/mount_vintages.csv) - rm {rel}')
    return verdict


def main() -> int:
    # Whole surface declared (#476, #477); the keyword collision on --from
    # (dest) is the tree's one surviving override. The --session|--all
    # exclusivity is the declared 1/-class, enforced at parse — bare noun stays
    # the census: subparsers are not required.
    args = command_parser('agent', overrides={
        'install': {'--from': {'dest': 'source'}},
    }).parse_args()

    if args.verb is None:
        return list_agents()   # bare noun → the census (local + store sessions), read-only status
    if args.verb == 'mount':
        return mount(args.apply)
    if args.verb == 'list-models':
        return model_census()
    if args.verb == 'capture':
        return 1 if capture(args.session, args.to, args.provider) else 0

    projects, claude = _claude()
    if args.verb == 'demerge':
        # every local project's memory, newest merge each, all-or-nothing per
        # project (a markerless folder demerges to silence)
        rc = 0
        for proj in sorted(d for d in projects.glob('-Users-*') if d.is_dir()):
            print(f'{proj.name}:')
            rc = max(rc, 1 if claude.demerge(proj, args.apply) else 0)
        return rc

    bundle = peer_bundle(args.source)
    # the twin-dressing and marker label: the source's ADDRESS — the origin machine's
    # name as it stands under claude's store (or the directory's own name for a path)
    machine = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in bundle.name) or 'incoming'
    if args.all:
        return 1 if claude.install_all(bundle, projects, args.apply, machine) else 0
    session = claude.pick_session(bundle, args.session)
    return 1 if claude.install_move(session.parent, projects, session, args.apply, machine) else 0


if __name__ == '__main__':
    sys.exit(main())
