"""
latest.py - the one reading of "the latest" for a directory of versions, the main
tier's (the gate imports what it checks): a house schema family holds v*.json files and the latest is the
highest number; an upstream reference project (rsc/reference/<project>/) holds
one lineage directory named as upstream names it (a date, a draft) whose
schema.json is the reference, and the latest is the last by name. The latest is
the schema and the rest history (issues/557), so either directory normally holds one.
"""

import json
import re
from pathlib import Path

SELF = 'src/main/latest.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

REFERENCE_FILE = 'schema.json'


def versions(directory: Path) -> list[Path]:
    """Every v*.json in directory, ascending by version number."""
    return sorted(directory.glob('v*.json'),
                  key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])


def lineages(directory: Path) -> list[Path]:
    """Every lineage directory in a reference project, ascending by name."""
    return sorted(d for d in directory.iterdir() if d.is_dir() and (d / REFERENCE_FILE).is_file()) \
        if directory.is_dir() else []


def reference_file(directory: Path):
    """The reference a project's pointers resolve against (issues/1069): the witness of the
    lineage its derivation declares, src/main/<project>/derivation.json, where one does; else
    the latest lineage's schema.json; None when the directory holds no lineage."""
    declared = REPO / 'src' / 'main' / directory.name / 'derivation.json'
    if declared.is_file() and directory.resolve() == (REPO / 'rsc' / 'reference' / directory.name).resolve():
        derivation = json.loads(declared.read_text())
        return REPO / derivation['witness'].replace('<lineage>', derivation['lineage'])
    found = lineages(directory)
    return found[-1] / REFERENCE_FILE if found else None


def latest_file(directory: Path):
    """The latest version file of a schema family, or a reference project's reference
    (reference_file); None when the directory holds neither."""
    found = versions(directory) if directory.is_dir() else []
    if found:
        return found[-1]
    return reference_file(directory)
