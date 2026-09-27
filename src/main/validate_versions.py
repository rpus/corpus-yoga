#!/usr/bin/env python
"""
Validate one JSON file against versioned schemas, one log and one verdict record per
datum-version pair. The record (src/main/verdict.py, #701) is what every reader reads - the
skip path here, the matrix, the audit, the stage's survey; the log is the inspection's
grist and no reader parses it.

Two faces:
  <input_file> <schema_dir> <log_dir> <label>          every version in the
      directory, then the family roll-up: status summary and matrix.md.
  --pair <input_file> <schema_file> <log_dir> <label>  exactly one pair — the
      dispatchable atom (#395): quiet, writes (or skips) that pair's log only.
"""

import glob
import re
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

from validate import validate
from validate_inspection import inspect_failure

SELF = 'src/main/validate_versions.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ — shared modules live at its root
from validation_matrix import family_root, write_matrix  # noqa: E402
import verdict  # noqa: E402


def _digest(path):
    """sha256 of the file's bytes — the content key (#367): identical bytes are
    current from any tree; clocks are labels, never ordering."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _record_current(log_out, input_digest, schema_digest):
    """True iff the verdict record beside the log judges exactly this datum × schema BY
    CONTENT: its two digests. No clock is consulted, so a fresh worktree's birth-mtimes
    cannot fake staleness (#367). A log with no record - one written before #701 - is
    not current and revalidates once, the stated migration cost. The record IS the
    memoisation."""
    log_dir, version = os.path.dirname(log_out), os.path.splitext(os.path.basename(log_out))[0]
    return verdict.current(verdict.read(verdict.path_for(log_dir, version)), input_digest, schema_digest)


def _validate_one(input_file, schema_path, log_out, input_digest):
    """Validate the pair and write its log; returns the verdict line. The log's
    first lines are the contract every reader relies on: stamp, datum line and
    schema line (each ending 'sha256 <digest>'), then the verdict."""
    input_bytes = os.path.getsize(input_file)
    schema_bytes = os.path.getsize(schema_path)
    schema_digest = _digest(schema_path)

    with open(input_file) as fh:
        input_lines = fh.read().count('\n')

    result = validate(input_file, schema_path)
    body = list(result)
    if result[0] != 'Valid!':
        # The failure inspection is part of the log, one author (#396); an
        # inspection crash must not cost the verdict already in hand.
        try:
            body += inspect_failure(input_file, schema_path, result)
        except Exception as e:  # noqa: BLE001 — any inspection failure is non-fatal
            body.append(f'(inspection failed: {e})')

    at = datetime.now().astimezone().replace(microsecond=0).isoformat()
    with open(log_out, 'w') as f:
        f.write(at + '\n')
        f.write(f'{input_file}: {input_lines} lines, {input_bytes} bytes · sha256 {input_digest}\n')
        f.write(f'{schema_path}: {schema_bytes} bytes · sha256 {schema_digest}\n')
        for line in body:
            f.write(line + '\n')
    # the verdict as data, beside the log, the one thing a reader reads (#701)
    verdict.write(os.path.dirname(log_out), os.path.splitext(os.path.basename(log_out))[0],
                  input_file, input_digest, input_bytes, input_lines,
                  schema_path, schema_digest, result[0] == 'Valid!', result[0], at)

    return result[0]


def validate_pair(input_file, schema_path, log_dir, label):
    """The single-pair face (#395): one datum, one schema version, one log —
    the dispatchable atom. Quiet: a current log is a task already done, and
    every verdict is stated by the family roll-up (directory face) afterwards.
    label is carried for the contract's symmetry; the log needs no label."""
    del label
    os.makedirs(log_dir, exist_ok=True)
    version = os.path.splitext(os.path.basename(schema_path))[0]
    log_out = os.path.join(log_dir, f'{version}.log')
    input_digest = _digest(input_file)
    if _record_current(log_out, input_digest, _digest(schema_path)):
        return
    _validate_one(input_file, schema_path, log_out, input_digest)


def validate_versions(input_file, schema_dir, log_dir, label):
    """The directory face: the datum against its family's LATEST version - the
    latest version is the schema, the rest is history (#557) - one log, one verdict.
    Older vN.log files a previous run left beside it are history too: nothing
    here reads or writes them."""
    os.makedirs(log_dir, exist_ok=True)
    schemas = sorted(glob.glob(os.path.join(schema_dir, 'v*.json')),
                     key=lambda f: [int(x) for x in re.findall(r'\d+', os.path.basename(f))])
    if not schemas:
        print(f'  {label}: no versioned schemas found in {schema_dir}', file=sys.stderr)
        return
    schema_path = schemas[-1]
    version = os.path.splitext(os.path.basename(schema_path))[0]
    log_out = os.path.join(log_dir, f'{version}.log')
    input_digest = _digest(input_file)
    ran = False
    if _record_current(log_out, input_digest, _digest(schema_path)):
        status = _record_status(log_out)
        note = ' (current — skipped)'
    else:
        status = _validate_one(input_file, schema_path, log_out, input_digest)
        ran = True
        note = ''
    if status == 'Valid!':
        print(f'  {label}: validates at {version}{note}')
    else:
        print(f'  FAIL: {label}: does not validate at latest {version}{note}: '
              f'{status[:80]}{"…" if len(status) > 80 else ""}')
        print(f'    → {log_out}')
        print('    → see: rsc/schema/WORKFLOW.md  # the data has outgrown the latest version — mint the next')

    # Validation owns the datum's machine-local matrix: re-render matrix.md from the
    # records just written, so it can never lag them. The datum dir is the parent of the
    # 'validation' component of log_dir (which may nest further, e.g. projects/<uuid>).
    # Announce it only when something was (re)validated — an all-current datum's
    # matrix is unchanged and its path is not news.
    p = Path(log_dir).resolve()
    while p.name != 'validation' and p != p.parent:
        p = p.parent
    if p.name == 'validation':
        mfile = write_matrix(p.parent, family_root(Path(schema_dir).resolve()))
        if mfile and ran:
            print(f'  matrix: {os.path.relpath(mfile)}')


def _record_status(log_out):
    """The verdict a current record holds, in the validator's own words: 'Valid!', or its
    first line of error."""
    log_dir, version = os.path.dirname(log_out), os.path.splitext(os.path.basename(log_out))[0]
    record = verdict.read(verdict.path_for(log_dir, version))
    assert record is not None, log_out   # current implies a record
    return 'Valid!' if record['verdict'] == 'valid' else record['reason']


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == '--pair':
        validate_pair(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif len(sys.argv) == 5 and sys.argv[1] != '--pair':
        validate_versions(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f'Usage: {sys.argv[0]} <input_file> <schema_dir> <log_dir> <label>')
        print(f'       {sys.argv[0]} --pair <input_file> <schema_file> <log_dir> <label>')
        sys.exit(1)
