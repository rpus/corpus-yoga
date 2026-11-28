"""
stage.py (corpus-yoga stage) - the room's stage, stage/, as the cache has its noun.

    corpus-yoga stage                   # status: the input, the output, the cache, each orphan, the rehearsal record, the units' counts
    corpus-yoga stage clean             # remove what the status names: each orphan, each duplicate of a held unit, each incomplete unit,
                                        # and stage whole once no unit stays staged
    corpus-yoga stage promote           # every pipeline's promote, in turn, never halting (issues/1203)

The tier (src/main/tier.py, src/main/corpus.py), laid out as the checkout is (issues/1163):
data/input is what the captures write; data/output, cache and logs are what the last rehearsal's
run derived, replaced whole by the next; rehearsal.json is
the record, one file, what the last rehearsal saw and judged (src/main/rehearsal.py, issues/815).
The per-unit relations stay with each capturing noun's bare status and with bare
corpus-yoga pipeline; this face counts them against the record. The janitor clears its
tier as corpus-yoga cache clean clears its own: every staged unit identical to the held
one, a duplicate, already promoted; every unit with nothing under it or lacking a member its record lists,
incomplete; and every entry under stage that is neither the input, the output, the cache, the
logs nor the record, an orphan of an earlier layout. All but the input serve the staged units:
while one stays staged they are the rehearsal's to replace, and once none does the janitor
removes stage whole (issues/1127). A unit that is unlicensed or would lose is evidence of
another kind and is never the janitor's.

The janitor's faces are src/main/cleaner.py's, the one loop every clean verb runs (issues/837):
this noun names its entries - each orphan, duplicate and incomplete unit, keyed by its
address with its kind, its words and its size beneath - and the loop says and takes them.
An entry is removed as it stands at the act, not as it stood at the naming: a directory
that gained a file while being emptied is emptied again.

The promote runs `corpus-yoga <pipeline> promote` for every pipeline bare corpus-yoga pipeline
lists (src/main/<pipeline>/pipeline.json), --all where the verb declares it, each in turn and
each to its own verdict, relayed as it says it. A promote that leaves units staged - refused,
unlicensed, incomplete - exits 1 and the next runs anyway; the verdict names it and is DONE,
since what it left is the stage's to say. One that exits otherwise reached no verdict, and the
promote is NOT DONE. A noun with no pipeline, forge, is not run.
"""
import subprocess
import sys
from pathlib import Path
from declared_parser import command_parser
import cleaner  # the one loop every clean verb runs (issues/837)
import corpus
import facts  # the one face a sentence is said through (issues/909)
import spell
import tier

SELF = 'src/main/cli/stage/stage.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

KINDS = corpus.JANITOR_KINDS   # each kind of entry, and its plural - one home, which the standing says too (issues/988)


def _unit(unit: corpus.Unit) -> str | None:
    try:
        corpus.remove(unit)
    except OSError as e:
        return (e.strerror or str(e)).lower()
    return None


def _size(unit: corpus.Unit) -> str:
    return corpus.human(sum(corpus.size_of(corpus.STAGED / m) for m in unit.members if (corpus.STAGED / m).exists()))


def entries() -> list[cleaner.Entry]:
    """Everything the janitor acts on, in the order it acts, each with its kind, its address,
    its facts and the act. The one list both faces walk - the dry run is the apply with the
    act elided, so the two cannot disagree."""
    out: list[cleaner.Entry] = []
    for e in corpus.orphans():
        name = e.relative_to(REPO).as_posix()
        out.append(cleaner.Entry('orphan', name, {'orphan': facts.phrase('neither the input, the output, the cache, the logs nor the record'), 'size': corpus.human(corpus.size_of(e))},
                                 lambda e=e: corpus.dispose(e)))
    remaining = []
    if corpus.STAGED.is_dir():
        for unit in corpus.units(corpus.STAGED):
            if corpus.redundant(unit):
                out.append(cleaner.Entry('duplicate', unit.address.as_posix(), {'duplicate': facts.phrase('identical to the held unit'), 'size': _size(unit)},
                                         lambda unit=unit: _unit(unit)))
            elif unit.missing:
                # its record says what it lacks, so what it is is decidable on sight (issues/721)
                out.append(cleaner.Entry('incomplete unit', unit.address.as_posix(),
                                         {'incomplete unit': facts.phrase('missing {missing}', missing=', '.join(unit.missing)), 'size': _size(unit)},
                                         lambda unit=unit: _unit(unit)))
            else:
                remaining.append(unit)
    if corpus.spent(remaining):
        stage = tier.STAGE
        out.append(cleaner.Entry('spent stage', stage.relative_to(REPO).as_posix() if stage.is_relative_to(REPO) else str(stage),
                                 {'spent stage': facts.phrase('no unit is staged - its input, output, cache, logs and rehearsal record serve none'),
                                  'size': corpus.human(corpus.size_of(stage))},
                                 corpus.dispose_spent))
    return out


def clean() -> int:
    return cleaner.clean('stage', entries(), KINDS)


def promotes() -> list[str]:
    """Each pipeline's promote, as typed: --all where the verb declares it."""
    return [spell.line(name, 'promote', all=True) if spell.takes(name, 'promote', 'all') else spell.line(name, 'promote')
            for name in sorted(corpus.pipelines()) if (corpus.CLI_ROOT / name / 'promote.json').is_file()]


def promote(runner=subprocess.run) -> int:
    lines, left, lost = promotes(), [], []
    for line in lines:      # each command's launcher echoes it as its log's header
        code = runner([str(REPO / 'corpus-yoga'), *line.split()[1:]], cwd=REPO).returncode
        if code == 1:
            left.append(line)
        elif code != 0:
            lost.append(line)
    ran = ', '.join(lines)
    if lost:
        facts.report(None, facts.act('stage', 'promote') + ': NOT DONE - ' + facts.phrase('{lost} reached no verdict; ran {ran}', lost=', '.join(lost), ran=ran))
        return 1
    words = facts.phrase('ran {ran}', ran=ran) + ('; ' + facts.phrase('{left} left units staged, as its verdict says', left=', '.join(left)) if left else '')
    facts.report(None, facts.act('stage', 'promote') + ': DONE - ' + words)
    return 0


def main() -> int:
    args = command_parser('stage').parse_args()
    if args.verb == 'clean':
        return clean()
    if args.verb == 'promote':
        return promote()
    return corpus.stage_status()


if __name__ == '__main__':
    sys.exit(main())
