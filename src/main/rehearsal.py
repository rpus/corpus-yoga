#!/usr/bin/env python
"""
rehearsal.py - the stage's rehearsal record, tmp/stage/rehearsal (#815): one file, what the
last rehearsal saw and judged, whole.

    rehearsal.py begin <stamp>          # before the run: the extent, every staged unit's digests, under the scratch tiers
    rehearsal.py end <stamp> <exit>     # after the run: the record, reduced from the extent and the scratch's verdicts, written whole

A rehearsal is corpus-yoga pipeline rehearse (src/main/cli/pipeline/rehearse.sh): the
checkout's own code run with CORPUS_YOGA_REHEARSAL=<stamp>, which the tier contract
(src/main/tier.py) resolves to the scratch tiers, tmp/stage/scratch, replaced whole by each
run - data/input a link to tmp/stage/input, data/output the preview, tmp/cache the
validation. What the run leaves there is grist; the record is what a reader reads: the
anchor (the stamp, the commit and how many files were changed in the tree, the Signature,
the command), the run's exit, and under `units` every staged unit the run began over, by
its address - its digests then, the digest a step recorded of its source where one
converted it, and each family's verdict as the validation step wrote it
(src/main/validation_verdict.py), with the validator's whole output where it refused. The
record appears only whole, written beside its address and renamed into place, so that no
reader finds half a judgement; the next rehearsal replaces it whole. Its shape is
src/main/rehearsal.schema.json, held on every write and every read: what does not
validate is not a record, and the reader says so.

A unit's standing to the record is decidable from it (src/main/corpus.py, `verdict`):
absent from `units`, unseen by the rehearsal; present with other digests than it has now,
changed since; present with no verdict, seen and not judged; else judged, valid or
refused, by the rehearsal the record names.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

SELF = 'src/main/rehearsal.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import provider  # noqa: E402
import tier  # noqa: E402
import validation_verdict as verdicts  # noqa: E402

RECORD = tier.TMP_STAGE_REHEARSAL
SCHEMA = REPO / 'src' / 'main' / 'rehearsal.schema.json'
EXTENT = tier.TMP_STAGE_SCRATCH / 'extent.json'      # what begin writes and end reads: the units as the run began
COMMAND = 'corpus-yoga pipeline rehearse'
MIGRATION = 'rsc/migration/815.sh --apply'          # removes the stamped directories of the layout before #815


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.as_posix()


def faults(record) -> list[str]:
    """What keeps the object from being a record: each schema error in words, at its
    place; none where it validates."""
    import jsonschema
    validator = jsonschema.Draft4Validator(json.loads(SCHEMA.read_text()))
    return [f'{"/".join(str(p) for p in e.absolute_path) or "(root)"}: {e.message}'
            for e in sorted(validator.iter_errors(record), key=lambda e: [str(p) for p in e.absolute_path])]


_read: dict[Path, dict | str | None] = {}


def read(path: Path = RECORD) -> dict | str | None:
    """The record, loaded and validated; None where there is none; in words, why what
    stands at its address is not one. Read once a process."""
    if path not in _read:
        _read[path] = _load(path)
    return _read[path]


def _load(path: Path) -> dict | str | None:
    if path.is_dir():
        return f'{_rel(path)} is a directory, the layout before #815 - {MIGRATION} removes it; then {COMMAND} judges the stage'
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text())
    except ValueError as e:
        return f'{_rel(path)} is not a record - {e}; {COMMAND} remakes it'
    bad = faults(record)
    if bad:
        return f'{_rel(path)} is not a record - {bad[0]}; {COMMAND} remakes it'
    return record


def write(record: dict, path: Path = RECORD) -> None:
    """The record, whole: written beside its address, then renamed into place."""
    part = path.with_name(path.name + '.part')
    part.write_text(json.dumps(record, indent=1) + '\n')
    os.replace(part, path)
    _read.pop(path, None)


def extent(units, digests: Callable) -> dict[str, dict]:
    """Every staged unit as the run begins, by its address: its digests."""
    return {unit.address.as_posix(): {'digests': sorted(digests(unit))} for unit in units}


def _latest(records: list[Path]) -> Path:
    return max(records, key=lambda f: int(''.join(c for c in f.name.split('.')[0] if c.isdigit()) or 0))


def reduce(stamp: str, commit: str, dirty: int, signature: str, exit_code: int, seen: dict[str, dict],
           units, cache_of: Callable, family_of: Callable) -> dict:
    """The record: the anchor, the run's exit, and each unit of the extent with the verdicts
    the run wrote under its cache address - the latest version per family, the family named
    as the pipeline declares it, and the validator's output where it refused."""
    by_address = {unit.address.as_posix(): unit for unit in units}
    out: dict[str, dict] = {}
    for address, was in sorted(seen.items()):
        entry: dict = {'digests': was['digests'], 'verdicts': {}}
        unit = by_address.get(address)
        cache = cache_of(unit) if unit is not None else None
        if cache is not None and cache.is_dir():
            source = cache / 'source.sha256'
            if source.is_file():
                entry['source'] = source.read_text().strip()
            by_leaf: dict[str, list[Path]] = {}
            for rec in (cache / 'validation').rglob(f'v*{verdicts.SUFFIX}'):
                by_leaf.setdefault(rec.parent.relative_to(cache / 'validation').as_posix(), []).append(rec)
            for leaf, recs in sorted(by_leaf.items()):
                latest = _latest(recs)
                record = verdicts.read(latest)
                if record is None:
                    continue
                one = {key: record[key] for key in ('version', 'datum_sha256', 'schema_sha256', 'verdict', 'reason', 'at')}
                if record['verdict'] != 'valid':
                    log = latest.with_name(f'{record["version"]}.log')
                    one['output'] = log.read_text() if log.is_file() else ''
                entry['verdicts'][family_of(unit, leaf)] = one
        out[address] = entry
    return {'stamp': stamp, 'commit': commit, 'dirty': dirty, 'signature': signature, 'command': COMMAND,
            'exit': exit_code, 'units': out}


def _git(*words: str) -> str:
    return subprocess.run(['git', '-C', str(REPO), *words], capture_output=True, text=True).stdout.strip()


def begin(stamp: str) -> int:
    import corpus
    units = corpus.units(corpus.STAGE) if corpus.STAGE.is_dir() else []
    EXTENT.parent.mkdir(parents=True, exist_ok=True)
    EXTENT.write_text(json.dumps({'stamp': stamp, 'units': extent(units, corpus.own_digests)}, indent=1) + '\n')
    print(f'rehearse: {len(units)} unit(s) staged as the run begins - their digests are {_rel(EXTENT)}')
    return 0


def end(stamp: str, exit_code: int) -> int:
    import corpus
    seen = json.loads(EXTENT.read_text()) if EXTENT.is_file() else None
    if not isinstance(seen, dict) or seen.get('stamp') != stamp:
        print(f'rehearse: NOT DONE - {_rel(EXTENT)} is not the extent of rehearsal {stamp}; no record written')
        return 1
    units = corpus.units(corpus.STAGE) if corpus.STAGE.is_dir() else []
    record = reduce(stamp, _git('rev-parse', '--short', 'HEAD') or '(no git)', len(_git('status', '--porcelain').splitlines()),
                    provider.signature(), exit_code, seen['units'], units, lambda u: u.cache, corpus.family_of)
    bad = faults(record)
    if bad:
        print(f'rehearse: NOT DONE - the record does not validate against {_rel(SCHEMA)} - {bad[0]}; no record written')
        return 1
    write(record)
    judged = sum(1 for unit in record['units'].values() if unit['verdicts'])
    print(f'rehearse: {_rel(RECORD)} - rehearsal {stamp} saw {len(record["units"])} unit(s), judged {judged}')
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == 'begin':
        return begin(argv[1])
    if len(argv) == 3 and argv[0] == 'end':
        return end(argv[1], int(argv[2]))
    print(f'usage: {SELF} begin <stamp> | end <stamp> <exit>', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
