"""
atoms.py - a bulk export's atoms, the measure by which one export's content survives
whole in another's (#743).

A bulk export is a synchronised snapshot of four components, licensed as five because a
conversation carries two kinds of content: conversations (message uuids per conversation),
summaries (the fingerprint of each conversation's summary, a per-snapshot oracle reading
that only an identical reading covers), memories (field and canonical value per account),
projects (each doc's uuid and content fingerprint, and the envelope's fingerprint, per
project) and users (the canonical user object per user). Envelope timestamps are excluded
throughout: the measure claims retained DATA, not byte equality.

The value of an export under a root is {component: the (unit key, atom) pairs it holds
that no deposit holds} - a memory state deposited byte-identical in data/output/memories
and a summary reading deposited verbatim in data/output/markdown/claude/chat/summaries
are kept whatever becomes of the export, so they count for nothing an export must still
hold. One export is held whole within another when every component's pairs are a subset
of the other's. This is the one home of the atoms: corpus.py's measure table loads it,
and src/main/pipeline/chat-export/supersede.py reads through it until #744 retires it.
"""
import hashlib
import json
import sys
from pathlib import Path

SELF = 'src/main/pipeline/chat-export/atoms.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import tier  # noqa: E402 - the tiers, one home (#702)

MEMORIES_DEPOSIT = 'data/output/memories'
SUMMARIES_DEPOSIT = 'data/output/markdown/claude/chat/summaries'


def canon(value) -> str:
    """Canonical form of a bounded JSON value - the atom carries the value itself, so set
    equality is exact string equality, with no fingerprint and no collision caveat. Right
    for the bounded components: memory fields, user objects."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def fingerprint(value) -> str:
    """Content fingerprint of an arbitrary JSON value - for atoms over unbounded content
    (project doc bodies, summaries), where carrying the value would make atom sets as
    large as the corpus."""
    return hashlib.sha256(canon(value).encode()).hexdigest()[:16]


def _conversations(export: Path) -> list:
    path = export / 'conversations.json'
    if not path.is_file():
        return []
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else []


def conversations(export: Path) -> dict:
    """{conversation uuid: (name, {message uuids})}."""
    return {c['uuid']: (c.get('name') or c['uuid'], {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')})
            for c in _conversations(export) if c.get('uuid')}


def summaries(export: Path) -> dict:
    """{conversation uuid: (name, {the summary's fingerprint})} - an empty summary is no unit."""
    return {c['uuid']: (c.get('name') or c['uuid'], {fingerprint(c['summary'])})
            for c in _conversations(export) if c.get('uuid') and c.get('summary')}


def memories(export: Path) -> dict:
    """{account uuid: ('memories', {(field, canonical value)})} - both eras carry one account's
    object, the pre-manifest export in a single-element array, the manifest era bare."""
    path = export / 'memories.json'
    if not path.is_file():
        return {}
    data = json.loads(path.read_text())
    return {m.get('account_uuid', '?'): ('memories', {(k, canon(v)) for k, v in m.items() if k != 'account_uuid'})
            for m in (data if isinstance(data, list) else [data])}


def projects(export: Path) -> dict:
    """{project uuid: (name, {('doc', doc uuid, fingerprint), ('meta', '', fingerprint)})}."""
    out = {}
    folder = export / 'projects'
    for f in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        p = json.loads(f.read_text())
        atoms = {('doc', d['uuid'], fingerprint([d.get('filename'), d.get('content')])) for d in p.get('docs', [])}
        atoms.add(('meta', '', fingerprint([p.get('name'), p.get('description'), p.get('prompt_template')])))
        out[p.get('uuid', f.stem)] = (p.get('name', f.stem), atoms)
    return out


def users(export: Path) -> dict:
    """{user uuid: (name, {the canonical user object})}."""
    path = export / 'users.json'
    if not path.is_file():
        return {}
    return {u.get('uuid', '?'): (u.get('full_name', 'user'), {canon(u)}) for u in json.loads(path.read_text())}


COMPONENTS = (('conversations', conversations), ('summaries', summaries), ('memories', memories),
              ('projects', projects), ('users', users))


def memories_deposited(export: Path, deposits: Path) -> Path | None:
    """The deposit byte-identical to the export's memory state, or None - the unconditional
    licence: a copy that outlives every export."""
    path = export / 'memories.json'
    if not path.is_file() or not deposits.is_dir():
        return None
    text = path.read_text()
    return next((f for f in sorted(deposits.glob('*.json')) if f.read_text() == text), None)


def summaries_deposited(deposits: Path) -> set[str]:
    """The fingerprints of every deposited summary reading - the summaries' unconditional
    licence, since a deposit outlives every export and every capture refresh."""
    if not deposits.is_dir():
        return set()
    return {fingerprint(f.read_text()) for f in deposits.glob('*/*.md') if f.name != 'index.md'}


def data_root(root: Path) -> Path:
    """The data root whose deposits license a unit under root: the checkout's for the store
    and for the stage, whose exports are judged against the deposits that will hold them;
    the parent of any other root, so a scratch root carries its own."""
    return tier.DATA if root in (tier.DATA / 'input', tier.TMP_STAGE_INPUT) else root.parent


def value(root: Path, unit) -> dict | None:
    """The export's atoms under root, per component, less what the deposits hold - the
    measure table's value for the `atoms` measure. None where the export holds no
    conversations.json, which no measure can read."""
    export = root / unit.path
    if not (export / 'conversations.json').is_file():
        return None
    deposits = data_root(root)
    out = {}
    for name, read in COMPONENTS:
        pairs = frozenset((key, atom) for key, (_name, atoms) in read(export).items() for atom in atoms)
        if name == 'memories' and memories_deposited(export, deposits / Path(MEMORIES_DEPOSIT).relative_to('data')):
            pairs = frozenset()
        if name == 'summaries':
            held = summaries_deposited(deposits / Path(SUMMARIES_DEPOSIT).relative_to('data'))
            pairs = frozenset(p for p in pairs if p[1] not in held)
        out[name] = pairs
    return out


def leq(a: dict, b: dict) -> bool:
    """a is held whole within b: every component's undeposited pairs are among b's."""
    return all(pairs <= b.get(name, frozenset()) for name, pairs in a.items())


def words(a: dict, b, unit) -> str:
    """Per component, what the measure read: the pairs a holds beyond the deposits, and
    how many of them the other does not hold."""
    parts = []
    for name, pairs in a.items():
        missing = len(pairs - (b or {}).get(name, frozenset()))
        parts.append(f'{name} {len(pairs)}' + (f' ({missing} not in the other)' if missing else '') if pairs
                     else f'{name} none beyond the deposits')
    return ', '.join(parts)
