"""
tail.py - the usr gate's failing stages as facts (issues/724, issues/755, issues/952): each failing
stage, and beneath it each refused subject by its name - an atom is `FAIL: <subject>:
<fault>`, the subjects refused for one fault joined as one key - and beneath the name
the fault in words, with the facts the atom carried beneath it where it carried any, so
that a stage of many units refused for one reason reads as one reason and the names, a
datum refused for a reason of its own stands under its own name, and no line is a
placeholder.

stdin: one row per line, `<stage>\\t<line>`, as src/main/cli/pipeline/pipeline.sh reads them
from each failing section - an atom's line, or beneath it a fact's `<key>: <value>` line
indented. stdout: `failing:` at the narration depth, through the printer.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/pipeline/tail.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main'))
import facts  # noqa: E402

ATOM = 'FAIL: '


def atoms(rows: list[tuple[str, str]]) -> dict[str, list[tuple[str, str, dict[str, str]]]]:
    """By stage, each atom as its subject, its fault and its facts: a row that begins with
    whitespace is a fact of the atom before it, `<key>: <value>`; any other row is an atom,
    its subject the words before its first `: ` once the FAIL mark is dropped, the fault the
    rest - the atom whole where it holds no such pair."""
    out: dict[str, list[tuple[str, str, dict[str, str]]]] = {}
    for stage, line in rows:
        if line[:1].isspace() and out.get(stage):
            key, _, value = line.strip().partition(': ')
            out[stage][-1][2][key] = value
            continue
        head = line[len(ATOM):] if line.startswith(ATOM) else line
        subject, pair, fault = head.partition(': ')
        out.setdefault(stage, []).append((subject, fault, {}) if pair else (head, '', {}))
    return out


def grouped(rows: list[tuple[str, str]]) -> dict:
    """The failing stages as facts: by stage, each subject by its name - the names of the
    subjects refused for one fault with one set of facts joined as one key, in the order
    first seen - and beneath the name the fault, with its facts beneath where it has any."""
    out: dict[str, dict] = {}
    for stage, found in atoms(rows).items():
        by_fault: dict[tuple[str, tuple[tuple[str, str], ...]], list[str]] = {}
        for subject, fault, facts_of in found:
            names = by_fault.setdefault((fault, tuple(facts_of.items())), [])
            if subject not in names:
                names.append(subject)
        out[stage] = {', '.join(names): ({fault: dict(facts_of)} if facts_of else fault) if fault else {}
                      for (fault, facts_of), names in by_fault.items()}
    return out


def main() -> int:
    rows = [(stage, atom) for stage, atom in (line.split('\t', 1) for line in sys.stdin.read().splitlines() if '\t' in line)]
    print('\n'.join(facts.lines({'failing': grouped(rows)}, facts.depth())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
