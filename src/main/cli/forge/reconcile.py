#!/usr/bin/env python
"""reconcile.py — the forge's declared merge settings against the live ones.

stdin is the live repository json (gh api repos/{owner}/{repo}); argv[1] is
src/main/cli/forge/forge.csv. One row per declared setting, OK or DRIFT, each
DRIFT carrying its own gh remedy. forge.sh relays the rows verbatim; the
judgment lives in the csv, never in a wrapper — and this face runs in the
venv like every .py (#478), never under a PATH python.
"""
import csv
import json
import sys
from pathlib import Path

SELF = 'src/main/cli/forge/reconcile.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], \
    f'{_file} is not at its declared address {SELF}'


def norm(value) -> str:
    return 'true' if value is True else 'false' if value is False else str(value)


def main() -> None:
    live = json.load(sys.stdin)
    slug = live.get('full_name') or '{owner}/{repo}'
    for row in csv.DictReader(open(sys.argv[1])):
        key, want = row['setting'], row['value']
        got = norm(live.get(key))
        if got == want:
            print('OK', key, want, '', sep='\t')
        else:
            flag = '-F' if want in ('true', 'false') else '-f'
            print('DRIFT', key, 'declared ' + want + ', live ' + got,
                  'gh api -X PATCH repos/' + slug + ' ' + flag + ' ' + key + '=' + want,
                  sep='\t')


if __name__ == '__main__':
    main()
