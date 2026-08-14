#!/usr/bin/env python
"""flip.py — the flip's one edit: every 'aims to complete #N' becomes 'closes #N'.

stdin is the PR body as reviewed; stdout is the armed body, nothing else
rewritten (.github/PULL_REQUEST_TEMPLATE.md holds the grammar; the flip
performs this on the reviewer's word only). Runs in the venv like every .py
(#478), never under a PATH python.
"""
import re
import sys
from pathlib import Path

SELF = 'src/main/cli/forge/flip.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], \
    f'{_file} is not at its declared address {SELF}'

sys.stdout.write(re.sub(r'aims to complete #([0-9]+)', r'closes #\1', sys.stdin.read()))
