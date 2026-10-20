"""
tail.py - the usr gate's failing stages as facts (issues/724, issues/755): each failing stage, and
beneath it each failure said once - atoms that differ only by the datum they name under
one heading, the atom's words with the datum's place marked, carrying their count and the
datums by name - so that a stage of many units refused for one reason reads as one reason
and the names, and a datum refused for a reason of its own stands under its own heading.

stdin: one row per atom, `<stage>\\t<line>`, as src/main/cli/pipeline/pipeline.sh reads them
from each failing section. stdout: `failing:` at the narration depth, through the printer.
"""
import re
import sys
from pathlib import Path

SELF = 'src/main/cli/pipeline/tail.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main'))
import facts  # noqa: E402

UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
# a datum's name as the atoms carry it: a bulk-export batch, a capture or session by uuid
DATUM = re.compile(rf'data-{UUID}-\d{{10}}-[0-9a-f]{{8}}|{UUID}')
PLACE = '<datum>'


def grouped(rows: list[tuple[str, str]]) -> dict:
    """The failing stages as facts: by stage, each heading - the atom with its datum's place
    marked - with its count and the datums beneath, in the order first seen."""
    out: dict[str, dict] = {}
    for stage, line in rows:
        found = DATUM.search(line)
        heading = DATUM.sub(PLACE, line, count=1) if found else line
        entry = out.setdefault(stage, {}).setdefault(heading, {'count': 0, 'datums': []})
        entry['count'] += 1
        if found and found.group(0) not in entry['datums']:
            entry['datums'].append(found.group(0))
    for stage in out.values():
        for entry in stage.values():
            if not entry['datums']:
                del entry['datums']
    return out


def main() -> int:
    rows = [(stage, atom) for stage, atom in (line.split('\t', 1) for line in sys.stdin.read().splitlines() if '\t' in line)]
    print('\n'.join(facts.lines({'failing': grouped(rows)}, facts.depth())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
