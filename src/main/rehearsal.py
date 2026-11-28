"""
rehearsal.py - the stage's rehearsal record, stage/rehearsal.json (issues/815): one file, what the
last rehearsal saw and judged, whole.

    rehearsal.py begin <stamp>          # before the run: the extent, every staged unit's digests, under the stage's tmp
    rehearsal.py end <stamp> <exit>     # after the run: the record, reduced from the extent and the stage's verdicts, written whole

A rehearsal is corpus-yoga pipeline run --stage-rehearsal (src/main/cli/pipeline/rehearse.sh): the
checkout's own code run with CORPUS_YOGA_REHEARSAL=<stamp>, which the tier contract
(src/main/tier.py) resolves to the stage as its root, laid out as the checkout is - data/input
what the captures wrote, data/output the preview, cache the validation, the last two replaced
whole by each run. What the run leaves there is grist; the record is what a reader reads: the
anchor (the stamp, the commit and how many files were changed in the tree, the Signature,
the command), the run's exit, and under `units` every staged unit the run began over, by
its address - its digests then, the digest a step recorded of its source where one
converted it, and each family's verdict as the validation step wrote it
(src/main/validation_verdict.py), with the validator's whole output where it refused. The
record appears only whole, written beside its address and renamed into place, so that no
reader finds half a judgement; the next rehearsal replaces it whole. Its shape is
src/main/rehearsal.schema.json, held on every write and every read: what does not
validate is not a record, and the reader says so.

A rehearsal is done when it has written its record and judged every unit it saw that a
family judges, whatever the verdicts (issues/1145): what they found is the stage's to say, and
the exit of the run it wraps - the usr gate, red wherever a datum is invalid - a fact of its
line and of the record.

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
import facts
import spell
import provider
import tier
import validation_verdict as verdicts

REPO = tier.REPO

RECORD = tier.STAGE_REHEARSAL
SCHEMA = REPO / 'src' / 'main' / 'rehearsal.schema.json'
EXTENT = tier.STAGE_TMP / 'extent.json'      # what begin writes and end reads: the units as the run began
COMMAND = spell.line('pipeline', 'run', stage_rehearsal=True)


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.as_posix()


def faults(record) -> list[str]:
    """What keeps the object from being a record: each schema error in words, at its
    place; none where it validates."""
    import jsonschema
    validator = jsonschema.Draft4Validator(json.loads(SCHEMA.read_text()))
    return [facts.plain_words(f'{"/".join(str(p) for p in e.absolute_path) or "(root)"} - {e.message}')   # said by the printer (issues/1149)
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
        return f'{_rel(path)} is a directory, not a record - {COMMAND} remakes it'
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
                one.update({key: record.get(key) for key in ('path', 'schema_path', 'rule', 'holds')})   # the fault as data (issues/952, issues/1141); null before it was recorded
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
    units = corpus.whole()                 # the extent is the whole units: an incomplete one is passed over (issues/996)
    EXTENT.parent.mkdir(parents=True, exist_ok=True)
    EXTENT.write_text(json.dumps({'stamp': stamp, 'units': extent(units, corpus.own_digests)}, indent=1) + '\n')
    print(f'rehearse: {len(units)} unit(s) staged as the run begins - their digests are {_rel(EXTENT)}')
    return 0


def outcome(stamp: str, record: dict, owed: set[str], exit_code: int) -> tuple[int, str]:
    """The rehearsal's verdict and its exit (issues/1145): DONE, 0, where every unit the record saw
    that a family judges - owed, by address - holds a verdict, whatever it found; NOT DONE, 1,
    naming those that hold none. The exit of the run it wraps is said where it is not 0."""
    units = record['units']
    unjudged = sorted(address for address, unit in units.items() if address in owed and not unit['verdicts'])
    judged = sum(1 for unit in units.values() if unit['verdicts'])
    unowed = sum(1 for address in units if address not in owed)
    saw = (f'rehearsal {stamp} saw {len(units)} unit(s), judged {judged}'
           + (f', {unowed} judged by no family' if unowed else '') + f' - the record is {_rel(RECORD)}')
    ran = '' if exit_code == 0 else f'; the run exited {exit_code}'
    act = facts.act('pipeline', 'run')
    if unjudged:
        return 1, f'{act}: NOT DONE - {saw}{ran} - {len(unjudged)} unit(s) a family judges hold no verdict - {", ".join(unjudged)}'
    return 0, f'{act}: DONE - {saw}{ran}'


def end(stamp: str, exit_code: int) -> int:
    import corpus
    seen = json.loads(EXTENT.read_text()) if EXTENT.is_file() else None
    if not isinstance(seen, dict) or seen.get('stamp') != stamp:
        facts.report(None, facts.act('pipeline', 'run') + f': NOT DONE - {_rel(EXTENT)} is not the extent of rehearsal {stamp}; no record written')
        return 1
    units = corpus.whole()                 # an incomplete unit is passed over, never judged (issues/996)
    record = reduce(stamp, _git('rev-parse', '--short', 'HEAD') or '(no git)', len(_git('status', '--porcelain').splitlines()),
                    provider.signature(), exit_code, seen['units'], units, lambda u: u.cache, corpus.family_of)
    bad = faults(record)
    if bad:
        facts.report(None, facts.act('pipeline', 'run') + f': NOT DONE - the record does not validate against {_rel(SCHEMA)} - {bad[0]}; no record written')
        return 1
    write(record)
    # what an act reports (issues/801, issues/896): its effect and its record; the launcher replies
    # with now:, the room's standing now that the stage is judged
    code, line = outcome(stamp, record, {unit.address.as_posix() for unit in units if unit.families}, exit_code)
    facts.report(None, line)
    return code


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == 'begin':
        return begin(argv[1])
    if len(argv) == 3 and argv[0] == 'end':
        return end(argv[1], int(argv[2]))
    print(f'usage: {Path(__file__).resolve().relative_to(tier.REPO)} begin <stamp> | end <stamp> <exit>', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
