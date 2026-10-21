#!/usr/bin/env python
"""
migration.py (corpus-yoga migration) - the moves a rename owes this machine's local roots
(issues/820): rsc/migration holds them, one guarded script per causing issue over the steps of
rsc/migration/step.sh, and this noun says them and takes them.

    corpus-yoga migration                 # status: each script - how many steps it would take, none, or that it halted and on what
    corpus-yoga migration sync            # each script with steps and how many: the dry run, the apply with the act elided
    corpus-yoga migration sync            # run each of them, its own lines relayed as it takes its steps; the status says what it would take

A script run bare prints each step it would take and takes none, prints nothing where
nothing is owed, and halts, exit 1, where a from and a to both stand - nothing chooses.
The status is those three states, read by running every script bare: a script with
steps is said with how many and carries the sync as its remedy, a halted one with what it
said and the reader's own act. The steps themselves are the script's to say - it is the
declaration of its moves, and prints them bare - so no status restates them. The sync
names each script with steps and how many, runs each, relays its lines as it
takes them, re-reads the status beneath, and ends with the verdict - DONE only when every
pending step was taken.
Its record, tmp/logs/migration/sync/<stamp>.log, is the launcher's tee of the whole verb,
header included (issues/708); the declaration's x rows are what make the verb enacting.
"""
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/migration/migration.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
import facts  # noqa: E402
import tier  # noqa: E402

SCRIPTS = REPO / 'rsc' / 'migration'
SYNC = facts.Command('corpus-yoga migration sync', facts.phrase('would take them'))
HALTED = facts.Act(facts.phrase('resolve by hand what it names'))


@dataclass
class Script:
    """A script's state: how many steps it would take, or that it halted and what it said."""
    steps: str | None = None
    halted: str | None = None
    remedy: facts.Command | facts.Act | None = None


@dataclass
class Status:
    scripts: dict[str, Script | str]      # by path: its steps, what it halted on, or none pending
    migration: str                        # the verdict


def scripts() -> list[Path]:
    return sorted(SCRIPTS.glob('[0-9]*.sh'))


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
    for name, (code, lines) in seen.items():
        if code != 0:
            halted += 1
            out[name] = Script(halted='; '.join(lines), remedy=HALTED)
        elif lines:
            pending += 1
            out[name] = Script(steps=facts.phrase('{n} pending - the script run bare says them', n=len(lines)), remedy=SYNC)
        else:
            out[name] = facts.phrase('none pending')
    return Status(out, facts.phrase('{n} script(s) - {pending} with steps pending, {halted} halted', n=len(out), pending=pending, halted=halted))


class Log:
    """What the sync says, line by line. The record of the act is the launcher's tee of the
    whole verb (issues/708), tmp/logs/migration/sync/<stamp>.log, header included; nothing is
    written here."""

    def __init__(self, apply: bool) -> None:
        self.apply = apply

    def say(self, line: str = '') -> None:
        print(line)


def sync() -> int:
    """One list of the scripts with steps, each run after it is named (issues/881: what it would
    take is the bare status's). Then what an act reports (issues/801): now:, and the verdict as
    the last line."""
    log = Log(True)
    seen = survey()
    owed = {name: lines for name, (code, lines) in seen.items() if code == 0 and lines}
    halted = {name: '; '.join(lines) for name, (code, lines) in seen.items() if code != 0}
    steps = sum(len(lines) for lines in owed.values())
    taken = 0
    failed: list[str] = []
    for name, pending in owed.items():
        log.say(f'  {name}: ' + facts.phrase('{n} step(s)', n=len(pending)))
        code, lines = run(REPO / name, apply=True)
        for line in lines:
            log.say(f'    {line}')
        if code == 0:
            taken += len(pending)
        else:
            failed.append(name)
    for name, words in halted.items():
        log.say(f'  {name}: ' + facts.phrase('halted - {words}', words=words))
    undone = failed + list(halted)
    verdict = ('migration sync: NOT DONE - ' + facts.phrase('took {taken} of {steps} step(s); NOT taken {undone}', taken=taken, steps=steps, undone=', '.join(undone)) if undone
               else 'migration sync: DONE - ' + facts.phrase('took {taken} step(s) of {n} script(s)', taken=taken, n=len(owed)))
    for line in facts.report_lines(None, verdict):   # the effect, or handed up to the launcher's reply (issues/896)
        log.say(line)
    return 1 if undone else 0


def main() -> int:
    args = command_parser('migration').parse_args()
    if args.verb == 'sync':
        return sync()
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
