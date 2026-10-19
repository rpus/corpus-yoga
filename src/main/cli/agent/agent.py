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
ext/mnt/<provider>/code/machine-transport/<machine> per the registry
(rsc/provider/providers.csv, #636, #853), the address its units have under
tmp/stage/input and data/input -
HARNESS-OWNED state the provider expires at will. Each shape is one adapter,
src/main/cli/agent/<provider>/harness.py, keeping the contract transport.py
states (#633); this driver knows no shape. Transported agents live in the
STORE, data/input/<provider>/code/machine-transport - a directory inside
data/input, the iCloud tree each room links as data/ by hand, which capture
creates on its first run - keyed <machine>/<project>/..., the project
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
of it, only ever by a user's explicit verb, never a pipeline's, and serves
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
    corpus-yoga agent list-drafters           # src/main/cli/agent/drafters.py: main's Signatures against the sessions held
    corpus-yoga agent mount
    corpus-yoga agent capture --provider <provider> --id <uuid-prefix>
    corpus-yoga agent capture --provider <provider>
    corpus-yoga agent install   --id <uuid-prefix> --from <machine|dir>
    corpus-yoga agent capture --all
    corpus-yoga agent install   --all --from <machine|dir>
    corpus-yoga agent demerge

capture takes --provider <name> (every session of one provider), --provider
<name> --id <uuid-prefix> (one of them, by uuid prefix, exactly one) or --all;
install takes --id or --all: a NAMED agent, a named provider's totality,
or the named TOTALITY — git push --all /
pull --all, safe because each per-session placement independently lands on
the lattice (silence / fast-forward / ahead / loud CONFLICT), and the memory
component moves ONCE either way (mirrored out; merged in under a single
marker block, so `install --all --from <machine>` is still one demerge). What is never
accepted is an INFERENCE: no recency guessing, no automatic choice. What install
would write is the agent noun's status, per peer store held (#881), totality or
not.

The endpoint asymmetry is the model, not an accident: capture takes NO
destination — it pushes this machine's own ref, the only legal one
(single-writer branches). install must NAME its source ref:
a peer machine under claude's store, or a directory. The two are distinguished by SHAPE, never by lookup: a bare token
is a machine, a path-shaped token (containing '/') is a directory — so meaning
never depends on the CWD.

capture writes to the store immediately (it is not precious).
install and demerge write into this machine's projects root — harness-owned state —
and the agent noun's status says what each would write before it is asked. Exit 1
on any CONFLICT.

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
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from pathlib import Path
from types import ModuleType

SELF = 'src/main/cli/agent/agent.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

sys.path.insert(0, str(REPO / 'src'))  # declared_parser — modules both tiers import
sys.path.insert(0, str(REPO / 'src' / 'main'))  # machine.py owns the machine binding
import tier  # noqa: E402 — the tiers, one home (#702)
import facts  # noqa: E402 - the one printer of a status's facts (#753)
import corpus  # noqa: E402 - the stage report, and the type of a staged unit
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))  # the transport contract
from machine import bound_machine  # noqa: E402
from declared_parser import command_parser  # noqa: E402
import provider as registry  # noqa: E402
import transport  # noqa: E402

if TYPE_CHECKING:                 # named for the status's shape; imported where it is used
    import drafters


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
    data/input is the iCloud tree each room links as data/ by hand; the
    provider's store inside it is a directory this verb creates, being what it
    is declared to write. None where data/input is absent: a sweep states the
    skip and what to do rather than stopping between providers."""
    medium = tier.DATA / 'input'
    if not medium.is_dir():
        print(f'{provider}: {medium.relative_to(REPO)} is missing - link data/ to the shared iCloud tree '
              '(corpus-yoga status shows the convention), then run this again; skipped', file=sys.stderr)
        return None
    # the outbox is the stage twin of the store, tmp/stage/input/...: a capture writes it,
    # and reads of the store only the held unit at the address it would write, the baseline
    # where the stage holds no copy (L10, #850); corpus-yoga agent promote relates each
    # staged session to the held one and writes what extends it (#687)
    out = tier.TMP_STAGE_INPUT / transport.store(provider).relative_to(tier.DATA / 'input') / bound_machine()
    out.mkdir(parents=True, exist_ok=True)
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


@dataclass
class Session:
    """A session in the census: its title as the adapter reads it, its size, its last write."""
    title: str
    size: str
    last_write: str


@dataclass
class Mount:
    """A live store this room does not mount: which rows cannot appear, and what makes them."""
    standing: str
    remedy: facts.Command


Sessions = dict[str, dict[str, dict[str, dict[str, Session]]]]   # by where - local, then each machine - provider, project and id


@dataclass
class Census:
    sessions: Sessions | str
    mounts: dict[str, Mount] | None = None    # by path


def list_agents() -> Census:
    """The sidebar-independent census: every session in each served provider's
    live store and in each machine's dir of that provider's store, dressed with
    its title as the adapter reads it - derived on demand, never stored (L5).
    Framing on stderr; data lines on stdout (pipeable)."""
    rows: list[tuple[transport.Session, str]] = []
    absent: dict[str, Mount] = {}
    for row, mount_path, adapter in served():
        provider = row['provider']
        if mount_path.is_dir():
            rows += [(s, 'local') for s in adapter.live_sessions(mount_path)]
        else:
            # a census that silently omits a side is a lie of absence: say which rows
            # cannot appear and how to make them appear
            absent[mount_path.relative_to(REPO).as_posix()] = Mount(
                f'absent - no local {provider} rows', facts.Command('corpus-yoga agent mount', 'would mount it'))
        store = transport.store(provider)
        if store.is_dir():
            for machine in sorted(p for p in store.iterdir() if p.is_dir()):
                rows += [(s, machine.name) for s in adapter.held_sessions(machine)]
    # the facts (#753): each session under where it is and its provider - its title, size
    # and last write - the local store first, then each machine's held copies
    where_order = ['local'] + sorted({w for _s, w in rows if w != 'local'})
    sessions: Sessions = {}
    for where in where_order:
        for s, w in rows:
            if w == where:
                t = datetime.fromtimestamp(s.mtime).strftime('%Y-%m-%d %H:%M')
                sessions.setdefault(where, {}).setdefault(s.provider, {}).setdefault(s.project, {})[s.id[:8]] = Session(
                    s.title, f'{s.size / 1e6:.1f}M', t)
    return Census(sessions or 'none', absent or None)


@dataclass
class Peer:
    """A peer machine's store held here, and what corpus-yoga agent install would write from it
    into this machine's live store (#881): the install's facts by outcome, read dry."""
    would_write: dict | str
    remedy: facts.Command


@dataclass
class Merge:
    """A project's latest merge record in its memory, which corpus-yoga agent demerge would undo (#881)."""
    latest: str
    remedy: facts.Command = facts.Command('corpus-yoga agent demerge', 'would undo it')


def peers_and_merges() -> tuple[dict[str, Peer] | str, dict[str, Merge] | str]:
    """What the two writes into the live store would do, read dry (#881): per peer machine
    held under claude's store, the install of all its sessions; per project, the latest
    merge record. The verbs act; the status says what they would do."""
    row = registry.provider('claude')
    projects, adapter = registry.mount(row), transport.adapter('claude')
    if projects is None or adapter is None or not projects.is_dir():
        return 'none - the claude store is not mounted', 'none - the claude store is not mounted'
    peers: dict[str, Peer] = {}
    store = transport.store('claude')
    for machine in (sorted(p for p in store.iterdir() if p.is_dir()) if store.is_dir() else []):
        if machine.name == registry.machine():
            continue
        log = adapter.install_all(machine, projects, False, machine.name)
        peers[machine.name] = Peer(log.facts() or 'nothing - the store holds no session of it',
                                   facts.Command(f'corpus-yoga agent install --from {machine.name} --all', 'would write them'))
    merges = {proj.name: Merge(label) for proj in sorted(d for d in projects.glob('-Users-*') if d.is_dir())
              if (label := adapter.latest_merge(proj)) is not None}
    return peers or 'none - no peer machine held', merges or 'none - no merge record'


@dataclass
class Status:
    sessions: Sessions | str
    mounts: dict[str, Mount] | None
    drafters: 'drafters.Brief | None'                     # said under its ref and head
    staged: dict[str, corpus.Staged]
    install: dict[str, Peer] | str = 'none'               # per peer store held, what install would write (#881)
    merges: dict[str, Merge] | str = 'none'               # per project, what demerge would undo (#881)

    def facts(self) -> dict:
        brief = self.drafters
        if brief is None:                 # no machine binding: the drafters cannot be read against one (#758)
            unbound = {'binding': 'absent', 'remedy': {'echo <declared-machine-name> > machine-name.txt': 'binds it, to a name rsc/machine/machines.csv declares'}}
            return {'sessions': self.sessions, 'mounts': self.mounts, 'drafters': unbound, 'staged': self.staged, 'install': self.install, 'merges': self.merges}
        return {'sessions': self.sessions, 'mounts': self.mounts, f'drafters on {brief.ref} @ {brief.head}': brief, 'staged': self.staged,
                'install': self.install, 'merges': self.merges}


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


def capture(uuid8: str | None, provider: str | None) -> int:
    """The extent, named: --all is every session of every served provider whose
    mount is present, each into its own store; --provider <name> is every
    session of that provider; --provider <name> --id <uuid-prefix> is one of
    them. A session is named within its provider, as the browser capture names
    a conversation within its provider - a uuid's shape does not say whose it is.
    The log is facts nested by outcome under each provider's address (#857), then
    next:, then the one verdict."""
    names = [row['provider'] for row, _, _ in served()]
    if provider is not None and provider not in names:
        sys.exit(f'error: {provider!r} is not a provider the agent verb serves - served: ' + ', '.join(names))
    if uuid8 is not None and provider is None:
        sys.exit('error: --id names a session within a provider - say which with --provider')
    targets = [(row, mount_path, adapter) for row, mount_path, adapter in served()
               if mount_path.is_dir() and (provider is None or row['provider'] == provider)]
    if not targets:
        sys.exit('error: no live store mounted - corpus-yoga agent mount creates the symlinks')
    if uuid8 is not None:
        row, mount_path, adapter = targets[0]
        matches = [s for s in adapter.live_sessions(mount_path) if s.id.startswith(uuid8)]
        if not matches:
            sys.exit(f'error: no {provider} session matching {uuid8!r} in {mount_path.relative_to(REPO)}')
        if len(matches) > 1:
            # one session can sit under two projects (the fork a repository rename leaves),
            # so more of the uuid resolves nothing: name each record with its project, and
            # the act that takes them all - --id names one session
            sys.exit(f'error: {uuid8!r} names {len(matches)} records: '
                     + ', '.join(f'{s.project}/{s.id}' for s in matches)
                     + f" - --id names one session; to capture every record, take the provider's totality: --provider {row['provider']}")
    out: dict[str, object] = {}
    logs: list[transport.Log] = []
    for row, mount_path, adapter in targets:
        name = row['provider']
        outbox = own_outbox(name)
        if outbox is None:
            continue
        log = adapter.capture(mount_path, outbox, transport.store(name) / bound_machine(), uuid8)
        logs.append(log)
        out[str(registry.address(row))] = log.facts() or f'nothing - {transport.LIVE} holds no session'
    # what an act reports (#801): its facts by outcome, next: - what the room can do after
    # the capture, as the store's status names it - and the verdict
    facts.report(out, corpus.room_next(), transport.verdict('agent capture', logs))
    return sum(log.conflicts for log in logs)

def _claude() -> tuple[Path, ModuleType]:
    """install and demerge write into Claude Code's projects root: the one
    adapter that vouches for a write into a live store."""
    row = registry.provider('claude')
    mount_path, adapter = registry.mount(row), transport.adapter('claude')
    assert mount_path is not None and adapter is not None
    if not mount_path.is_dir():
        sys.exit(f'error: {mount_path.relative_to(REPO)} missing - corpus-yoga agent mount creates the symlink')
    return mount_path, adapter


def mount() -> int:
    """The live agent stores mounted at the address their units have under every tier
    root, ext/mnt/<provider>/code/machine-transport/<machine> (#636, #853): one symlink
    per declared provider whose live store this machine holds, the target from the
    registry row. The links it would create are corpus-yoga agent's status (#881); this
    creates them. A link at a retired address is rsc/migration/636.sh's or
    rsc/migration/853.sh's."""
    if registry.machine() == 'unbound':
        facts.report(None, corpus.room_next(), 'agent mount: NOT DONE - machine-name.txt binds no machine, and the mount carries the machine; corpus-yoga status says how to bind one')
        return 1
    verdict = 0
    present = created = 0
    for row in registry.providers():
        live = registry.live_store(row)
        target = registry.mount(row)
        if live is None or target is None:
            print(f'{row["provider"]}: observes no live store - nothing to mount')
            continue
        shown = target.relative_to(REPO)
        if not live.is_dir():
            print(f'{shown}: {row["live_store"]} absent on this machine - nothing to mount')
            continue
        if target.is_symlink() and target.resolve() == live.resolve():
            print(f'{shown} → {row["live_store"]} (present)')
            present += 1
            continue
        if target.exists() or target.is_symlink():
            print(f'{shown}: exists and is not the link to {row["live_store"]} - not touched; remove it by hand')
            verdict = 1
            continue
        created += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(live)
        print(f'{shown} → {row["live_store"]} (created)')
    # what an act reports (#801): next: and the verdict, the last line
    did = f'did create {created}, present {present}'
    facts.report(None, corpus.room_next(), f'agent mount: {"NOT DONE" if verdict else "DONE"} - {did}' + ('; a link at another target is not touched' if verdict else ''))
    return verdict


def main() -> int:
    # Whole surface declared (#476, #477); the keyword collision on --from
    # (dest) is the tree's one surviving override. The --id|--all
    # exclusivity is the declared 1/-class, enforced at parse — bare noun stays
    # the census: subparsers are not required.
    args = command_parser('agent', overrides={
        'install': {'--from': {'dest': 'source'}},
    }).parse_args()

    if args.verb is None:
        # bare noun → one shape (#759): the census (local + store sessions), the sessions
        # main names as drafters against it (#631), the stage's units of the agent's captures
        census = list_agents()
        import drafters
        import machine
        brief = drafters.brief() if machine.BINDING.exists() else None     # an unbound room reads what needs no machine (#758)
        report = corpus.report_facts('agent')
        peers, merges = peers_and_merges()
        facts.say(Status(census.sessions, census.mounts, brief, report.staged, peers, merges))
        return 0
    if args.verb == 'mount':
        return mount()
    if args.verb == 'list-models':
        return model_census()
    if args.verb == 'list-drafters':
        import drafters
        return drafters.report()
    if args.verb == 'capture':
        return 1 if capture(args.id, args.provider) else 0
    if args.verb == 'promote':
        return corpus.promote('agent', corpus.extent('agent', args.provider, args.all, args.id))

    projects, claude = _claude()
    if args.verb == 'demerge':
        # every local project's memory, newest merge each, all-or-nothing per
        # project (a markerless folder demerges to silence)
        rc = 0
        for proj in sorted(d for d in projects.glob('-Users-*') if d.is_dir()):
            print(f'{proj.name}:')
            rc = max(rc, 1 if claude.demerge(proj) else 0)
        # what an act reports (#876): next: and the verdict; what it would undo is the status's (#881)
        facts.report(None, corpus.room_next(),
                     f'agent demerge: {"NOT DONE" if rc else "DONE"} - did undo the latest merge of each project above'
                     + ('; a conflict left one in place' if rc else ''))
        return rc

    bundle = peer_bundle(args.source)
    # the twin-dressing and marker label: the source's ADDRESS — the origin machine's
    # name as it stands under claude's store (or the directory's own name for a path)
    machine = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in bundle.name) or 'incoming'
    if args.all:
        log = claude.install_all(bundle, projects, True, machine)
    else:
        session = claude.pick_session(bundle, args.id)
        log = claude.install_move(session.parent, projects, session, True, machine)
    # the log is facts nested by outcome under the bundle's address (#857), then next:, then
    # the one verdict; what an install would write is corpus-yoga agent's status (#881)
    out: dict[str, object] = {(bundle.relative_to(REPO).as_posix() if bundle.is_relative_to(REPO) else str(bundle)):
                              log.facts() or f'nothing - the bundle holds no session'}
    facts.report(out, corpus.room_next(), transport.verdict('agent install', [log]))
    return 1 if log.conflicts else 0


if __name__ == '__main__':
    sys.exit(main())
