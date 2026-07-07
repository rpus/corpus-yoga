#!/usr/bin/env python
"""
compare_batches.py — do later bulk exports SUPERSEDE earlier ones?

A bulk export is a synchronised snapshot of FOUR components: conversations,
memories, projects, users. The same unprejudiced supersession processing is
applied to each — no component is assumed append-only, mutable, or static;
whether an earlier batch's data survives into the later one is an empirical
finding per component per batch pair, and the deletability verdict is simply
their conjunction.

The uniform model: each component atomises to {unit key: set of atoms}, and a
unit is superseded iff its atoms are a subset of its later self's. Atoms are
the format's content identities — uuid'd immutable constituents where the
format provides them, content fingerprints where it doesn't:

  conversations  unit = conversation uuid;  atoms = message uuids
                 (read from the RAW atomised json/ pieces — format-agnostic,
                 so an old batch's schema vintage is irrelevant)
  memories       unit = account uuid;       atoms = fingerprint per memory field
  projects       unit = project uuid;       atoms = (doc uuid, content fingerprint)
                 per doc, plus a fingerprint of the prompt/name/description
  users          unit = user uuid;          atoms = fingerprint of the user object

Envelope timestamps (created_at/updated_at) are excluded throughout:
supersession claims retained DATA, not byte equality of snapshots.

Per unit, against the LATEST batch:
  subset     — every atom present in the unit's later self
  ORPHANED   — the unit is absent from the latest export: unique data here
  DIVERGENT  — the unit exists later but atoms are missing there: unique data here

Overall: the latest snapshot is SUFFICIENT (earlier batches deletable) iff every
component of every earlier batch is fully superseded — validation matrices are
machine-local and die with their data, and the committed CHANGELOG narratives
keep the history. One component holding unique data (e.g. a rewritten memory
document) makes the earlier batch NOT deletable, however completely the others
are superseded.

Usage:
  src/run_python_script.sh src/main/chat-exports/compare_batches.py \
    [--chat-exports-gen gen/chat-exports] [--chat-exports ext/chat-exports]

Requires the batches' atomised json/ (written by the chat-exports pipeline);
memories/projects/users are read from the batch's gen/ archive copies (written
by archive_components.py; ext/ raw fallback for gen dirs predating that step).
Exit 0 iff the latest snapshot is sufficient.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def batch_time(name):
    m = re.search(r'-(\d{10})-[0-9a-f]+-batch', name)
    if m:
        return datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', name)
    if m:
        return datetime(*map(int, m.groups()), tzinfo=timezone.utc)
    return None


def _fp(value):
    """Content fingerprint of an arbitrary JSON value."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False)
                          .encode()).hexdigest()[:16]


# ── component atomisers: batch -> {unit key: (display name, set of atoms)} ────

def units_conversations(gen_dir, ext_dir):
    units = {}
    for f in sorted((gen_dir / 'json').glob('*.json')):
        c = json.load(f.open())
        u = c.get('uuid')
        if u:
            units[u] = (f.stem, {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')})
    return units


def _component_path(gen_dir, ext_dir, *rel):
    """Prefer the batch's gen/ archive copy (written by archive_components.py);
    fall back to the raw ext/ batch dir for gen dirs predating the archive step."""
    archived = gen_dir.joinpath(*rel)
    return archived if archived.exists() else ext_dir / rel[-1]


def units_memories(gen_dir, ext_dir):
    path = _component_path(gen_dir, ext_dir, 'memories', 'memories.json')
    if not path.exists():
        return {}
    units = {}
    for m in json.loads(path.read_text()):
        key = m.get('account_uuid', '?')
        atoms = {(field, _fp(value)) for field, value in m.items() if field != 'account_uuid'}
        units[key] = ('memories', atoms)
    return units


def units_projects(gen_dir, ext_dir):
    units = {}
    proj_dir = _component_path(gen_dir, ext_dir, 'projects')
    for f in sorted(proj_dir.glob('*.json')) if proj_dir.is_dir() else []:
        p = json.loads(f.read_text())
        # uniform (kind, constituent id, fingerprint) atoms; the envelope has exactly
        # one constituent, so its id slot is empty
        atoms = {('doc', d['uuid'], _fp([d.get('filename'), d.get('content')]))
                 for d in p.get('docs', [])}
        atoms.add(('meta', '', _fp([p.get('name'), p.get('description'), p.get('prompt_template')])))
        units[p.get('uuid', f.stem)] = (p.get('name', f.stem), atoms)
    return units


def units_users(gen_dir, ext_dir):
    path = _component_path(gen_dir, ext_dir, 'users', 'users.json')
    if not path.exists():
        return {}
    return {u.get('uuid', '?'): (u.get('full_name', 'user'), {_fp(u)})
            for u in json.loads(path.read_text())}


COMPONENTS = [('conversations', units_conversations),
              ('memories', units_memories),
              ('projects', units_projects),
              ('users', units_users)]


def compare_component(earlier, latest):
    """Classify each earlier unit against the latest; return (subset, details)."""
    subset = 0
    details = []
    for key, (name, atoms) in sorted(earlier.items()):
        if key not in latest:
            details.append(f'    ORPHANED {name} ({key}): {len(atoms)} atom(s) absent from latest')
        elif atoms <= latest[key][1]:
            subset += 1
        else:
            missing = len(atoms - latest[key][1])
            details.append(f'    DIVERGENT {name} ({key}): {missing} atom(s) present here, missing in latest')
    return subset, details


# ── captures cross-check (conversations only: that is what the capture source has) ─

def load_captures(captures_dir):
    """{conversation uuid: set of message uuids} (+ names) from <uuid>/<uuid>.json captures."""
    convs, names = {}, {}
    for d in sorted(captures_dir.iterdir()):
        j = d / f'{d.name}.json' if d.is_dir() else None
        if j and j.exists():
            c = json.load(j.open())
            u = c.get('uuid', d.name)
            convs[u] = {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')}
            names[u] = c.get('name', '')
    return convs, names


def compare_vs_captures(latest, latest_convs, latest_names, captures_dir):
    """Directional per-conversation supersession between the latest bulk export and the
    live-capture corpus (the data frontier). Informational: capture-ahead is the normal
    post-snapshot direction; capture-stale names conversations to recapture in place;
    an anomaly (unique messages on BOTH sides) wants investigation."""
    caps, cap_names = load_captures(captures_dir)
    shared = set(latest_convs) & set(caps)
    in_sync = ahead = 0
    stale, anomalies = [], []
    for u in sorted(shared):
        b, c = latest_convs[u][1], caps[u]
        if b == c:
            in_sync += 1
        elif b < c:
            ahead += 1
        elif c < b:
            stale.append(u)
        else:
            anomalies.append(u)
    export_only = sorted(set(latest_convs) - set(caps))
    capture_only = sorted(set(caps) - set(latest_convs))
    noteworthy = stale or anomalies or export_only
    print(('WARN: ' if noteworthy else '')
          + f'{latest.name} vs captures: {len(shared)} shared — {in_sync} in-sync, '
          f'{ahead} capture-ahead, {len(stale)} capture-stale, {len(anomalies)} anomalies; '
          f'{len(export_only)} export-only (no local capture), '
          f'{len(capture_only)} capture-only (absent from this export)')
    # Each mismatched conversation is its own WARN: line — the top-level RUNME
    # gathers WARN: (and "→ run:") lines verbatim into its tail, so the NAMES
    # reach the part of the log that gets read, not just the counts.
    for u in export_only:
        print(f'WARN: export-only {latest_convs[u][0]} ({u}) — no capture of it here; to capture:')
        print(f'    → run: src/main/browser-captures/safari_capture.sh --agent claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in capture_only:
        print(f'  capture-only {cap_names.get(u, "")!r} ({u}): in the captures, absent from this export')
    for u in stale:
        print(f'WARN: capture-stale {cap_names.get(u, "")!r} ({u}) — the export holds '
              f'{len(latest_convs[u][1] - caps[u])} message(s) the capture lacks — to recapture:')
        print(f'    → run: src/main/browser-captures/safari_capture.sh --agent claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in anomalies:
        print(f'WARN: anomaly {cap_names.get(u, "")!r} ({u}) — unique messages on both sides — investigate')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat-exports-gen', default='gen/chat-exports',
                    help='gen root holding <batch>/json/ atomised pieces')
    ap.add_argument('--chat-exports', default='ext/chat-exports',
                    help='ext root holding the raw batch dirs (memories/projects/users)')
    ap.add_argument('--captures', default=None,
                    help='ext/browser-captures/claude — also compare the latest batch '
                         'against the live-capture corpus, per conversation (informational)')
    args = ap.parse_args()

    root = Path(args.chat_exports_gen)
    ext_root = Path(args.chat_exports)
    batches = sorted((d for d in root.glob('data-*') if (d / 'json').is_dir()),
                     key=lambda d: (batch_time(d.name) or datetime.min.replace(tzinfo=timezone.utc)))
    unparseable = [d.name for d in batches if batch_time(d.name) is None]
    for n in unparseable:
        print(f'warning: cannot parse a time from batch name {n} — ordering may be wrong', file=sys.stderr)
    if not batches:
        print(f'no export dirs with atomised json/ under {root} — nothing to compare')
        return 0

    latest = batches[-1]
    latest_units = {name: fn(latest, ext_root / latest.name) for name, fn in COMPONENTS}
    if len(batches) < 2:
        print(f'1 export dir with atomised json/ under {root} — no earlier exports to compare')
    else:
        print(f'latest: {latest.name} — ' + ', '.join(
            f'{len(latest_units[name])} {name}' for name, _ in COMPONENTS))

    sufficient = True
    for b in batches[:-1]:
        ext_dir = ext_root / b.name
        superseded, holding, details = [], [], []
        for name, fn in COMPONENTS:
            earlier = fn(b, ext_dir)
            _, component_details = compare_component(earlier, latest_units[name])
            (superseded if not component_details else holding).append(name)
            details += component_details
        # One line per batch: the verdict and which components block deletion.
        # The unit/atom counts are mechanism — the details below carry the
        # specifics for exactly the components that hold unique data.
        if not holding:
            print(f'{b.name} → SUPERSEDED (every component a subset of the latest)')
        else:
            print(f'WARN: {b.name} is NOT superseded — its {", ".join(holding)} hold(s) unique data'
                  + (f' ({", ".join(superseded)} superseded)' if superseded else ''))
            for line in details:
                print(line)
        sufficient = sufficient and not holding

    if len(batches) >= 2:
        print('verdict: the newest export '
              + ('supersedes every earlier export dir — they are deletable' if sufficient else
                 'does NOT supersede the earlier export dir(s) — they hold unique data (lines above)'))

    if args.captures and Path(args.captures).is_dir():
        compare_vs_captures(latest, latest_units['conversations'], None, Path(args.captures))

    return 0 if sufficient else 1


if __name__ == '__main__':
    sys.exit(main())
