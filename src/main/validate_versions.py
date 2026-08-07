#!/usr/bin/env python
"""
Validate one JSON file against versioned schemas, one log per datum-version pair.

Two faces:
  <input_file> <schema_dir> <log_dir> <label>          every version in the
      directory, then the family roll-up: status summary and matrix.md.
  --pair <input_file> <schema_file> <log_dir> <label>  exactly one pair — the
      dispatchable atom (#395): quiet, writes (or skips) that pair's log only.
"""

import glob
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

from validate import validate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ — shared modules live at its root
from validation_matrix import write_matrix  # noqa: E402


def _digest(path):
    """sha256 of the file's bytes — the content key (#367): identical bytes are
    current from any tree; clocks are labels, never ordering."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _log_current(log_out, input_digest, schema_digest):
    """True iff the existing log records exactly this datum × schema BY CONTENT:
    lines 2-3 carry the pair's digests. No clock is consulted, so a fresh
    worktree's birth-mtimes cannot fake staleness (#367). An old-format log
    (no digest) is not current and revalidates once — the stated migration
    cost. The log IS the memoisation."""
    try:
        with open(log_out) as fh:
            next(fh)
            input_line = next(fh)
            schema_line = next(fh)
    except (OSError, StopIteration):
        return False
    return input_line.rstrip().endswith(f'sha256 {input_digest}') and \
        schema_line.rstrip().endswith(f'sha256 {schema_digest}')


def _current_log_verdicts(schemas, ran, log_dir):
    """version -> (modelled, status line, log path), read from the CURRENT logs —
    the memo's own records, for every version not validated this run. The log's
    fourth line is the verdict (stamp, input, schema, then the result)."""
    out = {}
    for schema_path in schemas:
        version = os.path.splitext(os.path.basename(schema_path))[0]
        if version in ran:
            continue
        log_out = os.path.join(log_dir, f'{version}.log')
        try:
            with open(log_out) as fh:
                lines = [line.rstrip('\n') for line in fh]
        except OSError:
            continue
        modelled = any(line == 'Valid!' for line in lines)
        status = lines[3] if len(lines) > 3 else '(log records no verdict)'
        out[version] = (modelled, status, log_out)
    return out


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

    with open(log_out, 'w') as f:
        f.write(datetime.now().astimezone().replace(microsecond=0).isoformat() + '\n')
        f.write(f'{input_file}: {input_lines} lines, {input_bytes} bytes · sha256 {input_digest}\n')
        f.write(f'{schema_path}: {schema_bytes} bytes · sha256 {schema_digest}\n')
        for line in result:
            f.write(line + '\n')

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
    if _log_current(log_out, input_digest, _digest(schema_path)):
        return
    _validate_one(input_file, schema_path, log_out, input_digest)


def validate_versions(input_file, schema_dir, log_dir, label):
    os.makedirs(log_dir, exist_ok=True)
    schemas = sorted(glob.glob(os.path.join(schema_dir, 'v*.json')))
    if not schemas:
        print(f'  {label}: no versioned schemas found in {schema_dir}', file=sys.stderr)
        return
    skipped = 0
    ran = {}   # version -> (status, log_path) for the versions validated this run
    input_digest = _digest(input_file)   # once per datum; per-version below
    for schema_path in schemas:
        version = os.path.splitext(os.path.basename(schema_path))[0]
        log_out = os.path.join(log_dir, f'{version}.log')

        if _log_current(log_out, input_digest, _digest(schema_path)):
            skipped += 1
            continue

        ran[version] = (_validate_one(input_file, schema_path, log_out, input_digest), log_out)

    # The expectation is "the datum is modelled by some version" (normally the
    # frontier); older versions failing is ordinary schema history. So the happy
    # paths get one line each and no log pointers; only a datum NO version models
    # gets the full per-version statuses with their logs — that is the case
    # someone must act on.
    valid   = [v for v, (s, _) in ran.items() if s == 'Valid!']
    invalid = [v for v, (s, _) in ran.items() if s != 'Valid!']
    if not ran:
        # A skip relays the verdict of the logs it trusts (#361): "current" states
        # the logs' freshness, never the datum's health, and a warm run must not
        # show a cleaner face than its own cache — a datum whose current logs
        # record no Valid! gets the cold path's FAIL, read from the memo.
        current = _current_log_verdicts(schemas, ran, log_dir)
        if not current or any(m for m, _, _ in current.values()):
            print(f'  {label}: {skipped}/{len(schemas)} version(s) current — skipped')
        else:
            print(f'  FAIL: {label}: {skipped}/{len(schemas)} version(s) current — '
                  'still unmodelled by any:')
            for version, (_, status, log_out) in current.items():
                print(f'  {label} ({version}): {status[:80]}{"…" if len(status) > 80 else ""}')
                print(f'    → {log_out}')
            print('    → see: rsc/schema/WORKFLOW.md  # the data has outgrown the latest version — mint the next')
    elif valid:
        print(f'  {label}: modelled by {", ".join(valid)}'
              + (f'; not by {", ".join(invalid)}' if invalid else '')
              + (f'; {skipped} current — skipped' if skipped else ''))
    else:
        # Every version validated THIS RUN failed — but the denominator of
        # "NOT modelled" is ALL versions: a skipped-current log still records
        # its verdict, and a datum those logs model is healthy. A new REQUIRED
        # field revalidates every old capture against the new version alone, which
        # against the wrong denominator reads as a FAIL storm over modelled data.
        current_valid = [v for v, (m, _, _) in
                         _current_log_verdicts(schemas, ran, log_dir).items() if m]
        if current_valid:
            print(f'  {label}: modelled by {", ".join(current_valid)} (current — skipped); '
                  f'not by the newly validated {", ".join(invalid)}')
        else:
            print(f'  FAIL: {label}: NOT modelled by any of the {len(schemas)} version(s)'
                  + (f' ({len(ran)} validated now, {skipped} current)' if skipped else '')
                  + ':')
            for version, (status, log_out) in ran.items():
                print(f'  {label} ({version}): {status[:80]}{"…" if len(status) > 80 else ""}')
                print(f'    → {log_out}')
            print('    → see: rsc/schema/WORKFLOW.md  # the data has outgrown the latest version — mint the next')

    # Validation owns the datum's machine-local matrix: re-render matrix.md from the
    # logs just written, so it can never lag them. The datum dir is the parent of the
    # 'validation' component of log_dir (which may nest further, e.g. projects/<uuid>).
    # Announce it only when something was (re)validated — an all-current datum's
    # matrix is unchanged and its path is not news.
    p = Path(log_dir).resolve()
    while p.name != 'validation' and p != p.parent:
        p = p.parent
    if p.name == 'validation':
        mfile = write_matrix(p.parent, Path(schema_dir).resolve().parent)
        if mfile and ran:
            print(f'  matrix: {os.path.relpath(mfile)}')


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == '--pair':
        validate_pair(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif len(sys.argv) == 5 and sys.argv[1] != '--pair':
        validate_versions(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f'Usage: {sys.argv[0]} <input_file> <schema_dir> <log_dir> <label>')
        print(f'       {sys.argv[0]} --pair <input_file> <schema_file> <log_dir> <label>')
        sys.exit(1)
