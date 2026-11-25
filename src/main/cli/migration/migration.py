"""
migration.py (corpus-yoga migration) - the moves a rename owes this machine's local roots
(issues/820): rsc/migration holds them, one guarded script per causing issue over the steps of
rsc/migration/step.sh, and this noun says them and takes them.

    corpus-yoga migration                 # status: each script - the steps it would take, none, or that it halted and on what
    corpus-yoga migration apply            # each script with steps and how many: the dry run, the apply with the act elided
    corpus-yoga migration apply            # run each of them, its own lines relayed as it takes its steps; the status says what it would take

A script run bare prints each step it would take and takes none, prints nothing where
nothing is owed, and halts, exit 1, where a from and a to both stand - nothing chooses.
The scripts have one order, merge order (issues/1094): the order in which main's history
first holds each, and among those one commit first holds, their issue numbers' - each is
written against the layout the scripts before it leave. The status is those three states,
read by running every script bare against the room as it stands, not as the scripts before
it would leave it; a script after one that halts is said as waiting on it. a script with
steps is said with each step's line as the script prints it, and carries the apply as its
act; a halted one with the steps before the halt and what it said there. The lines are the
script's own, relayed, never restated: the checkout runs corpus-yoga commands only, so the
status is where a reader sees what the apply would take. The apply
names each script with steps and how many, runs each, relays its lines as it
takes them, re-reads the status beneath, and ends with the verdict - DONE only when every
pending step was taken. The apply runs every script with --apply in merge order, whatever
its bare run said - a script's steps can arise from the one before it - and runs none after
the first that halts.
Its record, logs/migration/apply/<stamp>.log, is the launcher's tee of the whole verb,
header included (issues/708); the declaration's x rows are what make the verb enacting.
"""
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from declared_parser import command_parser
import facts
import spell

SELF = 'src/main/cli/migration/migration.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

SCRIPTS = REPO / 'rsc' / 'migration'


@dataclass
class Script:
    """A script's state: the steps it would take, each as its line, and where it halted, what it
    said there - a finding, which no verb clears, since no step chooses between a from and a to
    (issues/1058) - or the halted script before it that it waits on."""
    steps: list[str] | None = None
    waiting: str | None = None
    halted: facts.Finding | None = None
    act: facts.Would | None = None


@dataclass
class Status:
    scripts: dict[str, Script | str]      # by path: its steps, what it halted on, or none pending
    migration: str                        # the verdict


def scripts() -> list[Path]:
    """Every script, in merge order: by the position in main's history of the commit that first
    holds it - a script no commit holds yet, last - then by its issue number."""
    history = subprocess.run(['git', 'rev-list', '--reverse', 'HEAD'], capture_output=True, text=True, cwd=REPO).stdout.split()
    position = {sha: index for index, sha in enumerate(history)}
    def first(script: Path) -> int:
        added = subprocess.run(['git', 'log', '--diff-filter=A', '--format=%H', '--', script.relative_to(REPO).as_posix()],
                               capture_output=True, text=True, cwd=REPO).stdout.split()
        return position.get(added[-1], len(history)) if added else len(history)
    return sorted(SCRIPTS.glob('[0-9]*.sh'), key=lambda script: (first(script), int(script.stem)))


def run(script: Path, apply: bool = False) -> tuple[int, list[str]]:
    """The script run - bare, or with --apply: its exit and its lines."""
    done = subprocess.run([str(script)] + (['--apply'] if apply else []), capture_output=True, text=True, cwd=REPO)
    return done.returncode, (done.stdout + done.stderr).strip().splitlines()


def survey() -> dict[str, tuple[int, list[str]]]:
    """Every script run bare, by its path: its exit and its lines."""
    return {script.relative_to(REPO).as_posix(): run(script) for script in scripts()}


def status_facts(seen: dict[str, tuple[int, list[str]]] | None = None) -> Status:
    seen = survey() if seen is None else seen
    out: dict[str, Script | str] = {}
    pending = halted = 0
    stop: str | None = None
    for name, (code, lines) in seen.items():
        if stop is not None:
            out[name] = Script(waiting=facts.phrase('on {script}, which halts', script=stop))
        elif code != 0:
            stop = name
            halted += 1
            out[name] = Script(steps=lines[:-1] or None,
                               halted=facts.Finding(lines[-1].removeprefix('FAIL: ') if lines else facts.phrase('it exits {code}', code=code)))
        elif lines:
            pending += 1
            out[name] = Script(steps=lines, act=facts.Would(spell.line('migration', 'apply'), {name: len(lines)}))
        else:
            out[name] = facts.phrase('none pending')
    return Status(out, facts.phrase('{n} script(s) - {pending} with steps pending, {halted} halted', n=len(out), pending=pending, halted=halted))


class Log:
    """What the apply says, line by line. The record of the act is the launcher's tee of the
    whole verb (issues/708), logs/migration/apply/<stamp>.log, header included; nothing is
    written here."""

    def __init__(self, apply: bool) -> None:
        self.apply = apply

    def say(self, line: str = '') -> None:
        print(line)


def apply() -> int:
    """Every script run with --apply in merge order (issues/1094), each named with the steps it
    took, up to the first that halts, which is named with what it said and ends the run. Then
    what an act reports (issues/801): the verdict as the last line."""
    log = Log(True)
    order = [script.relative_to(REPO).as_posix() for script in scripts()]
    taken = 0
    for index, name in enumerate(order):
        code, lines = run(REPO / name, apply=True)
        if code != 0:
            for line in lines[:-1]:
                log.say(f'  {name}: {line}')
            log.say(f'  {name}: ' + facts.phrase('halted - {words}', words=lines[-1].removeprefix('FAIL: ') if lines else facts.phrase('it exits {code}', code=code)))
            taken += len(lines) - 1 if lines else 0
            rest = order[index + 1:]
            verdict = facts.act('migration', 'apply') + ': NOT DONE - ' + facts.phrase('took {taken} step(s); {script} halts, and {n} script(s) after it wait on it',
                                                                                         taken=taken, script=name, n=len(rest))
            break
        for line in lines:
            log.say(f'  {name}: {line}')
        taken += len(lines)
    else:
        verdict = facts.act('migration', 'apply') + ': DONE - ' + facts.phrase('took {taken} step(s) of {n} script(s)', taken=taken, n=len(order))
    for line in facts.report_lines(None, verdict):   # the effect, or handed up to the launcher's reply (issues/896)
        log.say(line)
    return 0 if verdict.startswith(facts.act('migration', 'apply') + ': DONE') else 1


def main() -> int:
    args = command_parser('migration').parse_args()
    if args.verb == 'apply':
        return apply()
    facts.say_standing(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
