"""
verdict.py - a validation's verdict as data: one record per (datum, version), written by
the validation step where it judges and read by every consumer of a verdict - the skip
path, the matrix, the audit, the stage's survey (#701). The log beside it is the
inspection's grist, which no reader parses: a datum's content has no way to state its
own verdict.

    <log_dir>/<version>.verdict.json
    {"datum": ..., "datum_sha256": ..., "datum_bytes": N, "datum_lines": N,
     "schema": ..., "schema_sha256": ..., "version": "vN",
     "verdict": "valid" | "invalid", "reason": <the validator's first line>, "at": <stamp>}
"""
import json
from pathlib import Path

SUFFIX = '.verdict.json'


def path_for(log_dir, version: str) -> Path:
    return Path(log_dir) / f'{version}{SUFFIX}'


def write(log_dir, version: str, datum: str, datum_digest: str, datum_bytes: int, datum_lines: int,
          schema: str, schema_digest: str, valid: bool, reason: str, at: str) -> Path:
    p = path_for(log_dir, version)
    p.write_text(json.dumps({
        'datum': str(datum), 'datum_sha256': datum_digest, 'datum_bytes': datum_bytes, 'datum_lines': datum_lines,
        'schema': str(schema), 'schema_sha256': schema_digest, 'version': version,
        'verdict': 'valid' if valid else 'invalid', 'reason': reason, 'at': at}, indent=2) + '\n')
    return p


def read(path) -> dict | None:
    """The record, or None where there is none or it is not a record."""
    try:
        record = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or record.get('verdict') not in ('valid', 'invalid'):
        return None
    return record


def current(record: dict | None, datum_digest: str, schema_digest: str) -> bool:
    """Whether the record judges exactly this datum against exactly this schema, by content."""
    return bool(record) and record['datum_sha256'] == datum_digest and record['schema_sha256'] == schema_digest


def symbol(record: dict | None) -> str:
    if record is None:
        return '?'
    return '✓' if record['verdict'] == 'valid' else '✗'
