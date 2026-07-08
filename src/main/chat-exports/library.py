#!/usr/bin/env python
"""
library.py — uuid-keyed resolution of the durable artifact library.

lib/artifacts/downloaded/ outlives any one export batch, so its directories are
keyed by identity with presentation as dressing: <ordinal>-<slug>-<uuid8>, where
<uuid8> (the first 8 hex digits of the conversation uuid) is the resolution key
and <ordinal>-<slug> is the batch's canonical presentation name — carried for
humans (listings read and sort in conversation order) but never trusted by
machines: ordinals renumber whenever the corpus changes, so dir_for() REFRESHES
the dressing to the current numbering every time a consumer touches the dir.
A dir whose conversation is absent from the current corpus (deleted live) keeps
whatever dressing it last had — or none — the absence of a current number being
itself a signal. Ordinals and slugs contain no hyphens (slug() maps
non-alphanumerics to '_'), so the final hyphen always delimits the uuid8.

Resolution is always by uuid8 suffix (glob "*-<uuid8>"), never by dressing: a
conversation renamed or renumbered simply gets fresh dressing on next touch.

As a CLI, normalises a library holding earlier naming vintages — the original
"<ordinal>-<slug>" (no uuid: resolved by unique slug against the batch corpus)
and the uuid8-prefix "<uuid8>-<slug>" — renaming each dir to canonical and
MERGING when two vintages turn out to be the same conversation (files moved
across, byte-identical duplicates dropped, differing files reported as
CONFLICTs and left in place). Dry-run by default:

    src/run_python_script.sh src/main/chat-exports/library.py \
      gen/chat-exports/<batch>/json [--root lib/artifacts/downloaded] [--apply]

The vintages themselves are data: rsc/naming/library_dir_vintages.csv.
"""
import re
import shutil
import sys
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[3] / 'lib' / 'artifacts' / 'downloaded'


def assert_uuid8_unique(uuids) -> None:
    """The census the dressing scheme rests on: uuid8 (32 bits) is an identity
    key only while no two conversations share a prefix — a property to VERIFY
    against the population, never to purchase from probability (user law,
    2026-07-08; the check is O(n), the failure it prevents is two
    conversations' artifacts silently interleaved in one dir). Exits loudly,
    naming the full colliding uuids — a collision means the scheme needs
    longer prefixes, not a shrug."""
    by_u8: dict[str, set[str]] = {}
    for u in uuids:
        by_u8.setdefault(u[:8], set()).add(u)
    clashes = {u8: us for u8, us in by_u8.items() if len(us) > 1}
    if clashes:
        lines = [f'  {u8}: ' + ', '.join(sorted(us)) for u8, us in sorted(clashes.items())]
        sys.exit('error: uuid8 prefix collision — the library dressing scheme cannot '
                 'key these conversations:\n' + '\n'.join(lines))


def find(uuid: str, root: Path = LIBRARY) -> Path | None:
    """The existing library dir for this conversation, or None. Recognises the
    canonical suffix form AND the short-lived 2026-07-05 uuid8-PREFIX vintage
    ("<uuid8>-<slug>"), so a library pulled at that vintage heals on first touch
    (dir_for renames whatever find returns) instead of silently duplicating —
    the exact bug uuid-keying exists to prevent. (No false positives either way:
    an ordinal prefix is 2-3 digits, never 8 hex + '-'; a slug tail would have
    to equal this conversation's uuid8 exactly.)"""
    if not root.is_dir():
        return None
    hits = sorted(root.glob(f'*-{uuid[:8]}')) or sorted(root.glob(f'{uuid[:8]}-*'))
    return hits[0] if hits else None


def dir_for(uuid: str, dressing: str, root: Path = LIBRARY) -> Path:
    """The library dir for this conversation, renamed to carry the CURRENT
    presentation dressing (the batch's "<ordinal>-<slug>" name) if it exists
    under stale dressing; else the path a new one should be created at."""
    canonical = root / f'{dressing}-{uuid[:8]}'
    existing = find(uuid, root)
    if existing is None:
        return canonical
    if existing != canonical:
        existing.rename(canonical)  # dressing refresh — identity (the suffix) unchanged
    return canonical


# ── CLI: normalise a library holding earlier naming vintages ──────────────────

REPO = Path(__file__).resolve().parents[3]


def _vintages() -> list[dict]:
    """The library's naming-format history AS DATA, not as commented conditionals:
    rsc/naming/library_dir_vintages.csv (id, status, pattern, note), in match
    priority order. Identification cites vintage ids from this table."""
    import csv
    with open(REPO / 'rsc' / 'naming' / 'library_dir_vintages.csv') as f:
        return list(csv.DictReader(f))


def _corpus(json_dir: Path):
    """From a batch's atomised pieces: uuid8 -> current canonical dressing, and
    slug -> [uuid8, ...] (for resolving the uuid-less ancient vintage)."""
    import json
    dressing_by_u8, u8s_by_slug = {}, {}
    uuids = []
    for f in sorted(json_dir.glob('*.json')):
        head, _, slugpart = f.stem.partition('-')
        if not head.isdigit():
            continue  # empty-<uuid8> stubs carry no slug identity
        uuid = json.loads(f.read_text())['uuid']
        uuids.append(uuid)
        u8 = uuid[:8]
        dressing_by_u8[u8] = f.stem
        u8s_by_slug.setdefault(slugpart, []).append(u8)
    assert_uuid8_unique(uuids)  # dressing_by_u8 would otherwise overwrite silently
    return dressing_by_u8, u8s_by_slug


def _identify(name: str, u8s_by_slug) -> tuple[str | None, str]:
    """(uuid8 or None, reason) — by matching the vintages table in priority order.
    Vintages carrying a u8 group resolve by identity; the slug-only vintage
    resolves by unique slug against the corpus; anything else is unknown."""
    for v in _vintages():
        m = re.match(v['pattern'], name)
        if not m:
            continue
        u8 = m.groupdict().get('u8')
        if u8:
            return u8, f"{v['id']} ({v['status']})"
        cands = u8s_by_slug.get(m.group('slug'), [])
        if len(cands) == 1:
            return cands[0], f"{v['id']}, slug-resolved"
        return None, f"{v['id']}: slug matches {len(cands)} conversation(s)"
    return None, 'matches no vintage in rsc/naming/library_dir_vintages.csv'


def _merge(src: Path, dest: Path, apply: bool) -> int:
    """Move src's files into dest; drop byte-identical duplicates; report and
    keep differing files (CONFLICT). Returns the conflict count."""
    conflicts = 0
    for f in sorted(p for p in src.rglob('*') if p.is_file() and p.name != '.DS_Store'):
        rel = f.relative_to(src)
        target = dest / rel
        if not target.exists():
            print(f'      move {rel}')
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                f.rename(target)
        elif target.read_bytes() == f.read_bytes():
            print(f'      identical {rel} — dropping duplicate')
            if apply:
                f.unlink()
        else:
            print(f'      ✗ CONFLICT {rel} — differs from {dest.name}; left in place')
            conflicts += 1
    if apply and not conflicts:
        shutil.rmtree(src)  # only .DS_Store-class residue can remain
    return conflicts


def _normalise(root: Path, json_dir: Path, apply: bool) -> int:
    dressing_by_u8, u8s_by_slug = _corpus(json_dir)
    problems = 0
    claimed: set[str] = set()  # canonical names claimed this run (dry-run merge prediction)
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        u8, how = _identify(d.name, u8s_by_slug)
        if u8 is None:
            print(f'  ! {d.name}: {how} — left alone')
            problems += 1
            continue
        # canonical: current dressing when the conversation is in the corpus;
        # a departed conversation keeps its slug, dressing-less (no false number)
        dressing = dressing_by_u8.get(u8)
        stem = d.name.rsplit('-', 1)[0] if how == 'suffix' else d.name.split('-', 1)[-1]
        canonical = root / (f'{dressing}-{u8}' if dressing else f'{stem}-{u8}')
        if d == canonical:
            claimed.add(canonical.name)
            continue
        if canonical.exists():
            print(f'  {d.name} ({how}) same conversation as {canonical.name} — merging')
            problems += _merge(d, canonical, apply)
        elif canonical.name in claimed:
            print(f'  {d.name} ({how}) same conversation as {canonical.name} — '
                  f'would merge (file-level plan on --apply)')
        else:
            print(f'  {d.name} ({how}) -> {canonical.name}')
            if apply:
                d.rename(canonical)
        claimed.add(canonical.name)
    print('APPLIED' if apply else 'dry run — pass --apply to normalise')
    return problems


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='normalise library dir naming across vintages')
    ap.add_argument('json_dir', help="a batch's atomised json/ (the corpus for slug/ordinal resolution)")
    ap.add_argument('--root', default=str(LIBRARY))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    sys.exit(1 if _normalise(Path(args.root), Path(args.json_dir), args.apply) else 0)
