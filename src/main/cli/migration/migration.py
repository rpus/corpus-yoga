#!/usr/bin/env python
"""
migration.py (corpus-yoga migration) - the moves a rename owes this machine's local roots
(#820): rsc/migration holds them, one guarded script per causing issue over the steps of
rsc/migration/step.sh, and this noun says them and takes them.

    corpus-yoga migration                 # status: each script - the steps it would take, none, or that it halted and on what
    corpus-yoga migration sync            # each script with steps and how many: the dry run, the apply with the act elided
    corpus-yoga migration sync --apply    # run each of them with --apply, its own lines relayed as it takes its steps

A script run bare prints each step it would take and takes none, prints nothing where
nothing is owed, and halts, exit 1, where a from and a to both stand - nothing chooses.
The status is those three states, read by running every script bare: a script with
steps carries the sync as its remedy, a halted one the reader's own act. The sync names
each script with steps and how many - the steps themselves are the status's to say, and
the script's own lines say them as it takes them - runs each with --apply, relays its
lines, re-reads the status beneath them, and ends with the verdict - DONE only when every
pending step was taken.
Its log, tmp/logs/migration/sync/<stamp>.log, opens with the Signature triad as every
verb's log does.
"""
import subprocess
import sys
import time
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
import provider  # noqa: E402
import tier  # noqa: E402

SCRIPTS = REPO / 'rsc' / 'migration'
SYNC = facts.Command('corpus-yoga migration sync --apply', 'takes them')
HALTED = facts.Act('resolve by hand what it names')


@dataclass
class Script:
    """A script's state: the steps it would take, or that it halted and what it said."""
    steps: list[str] | None = None
    halted: list[str] | None = None
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


def status_facts() -> Status:
    out: dict[str, Script | str] = {}
    pending = halted = 0
    for script in scripts():
        name = script.relative_to(REPO).as_posix()
        code, lines = run(script)
        if code != 0:
            halted += 1
            out[name] = Script(halted=lines, remedy=HALTED)
        elif lines:
            pending += 1
            out[name] = Script(steps=lines, remedy=SYNC)
        else:
            out[name] = 'none pending'
    return Status(out, f'{len(out)} script(s) - {pending} with steps pending, {halted} halted')


class Log:
    """The sync's own log (the declaration says so): every line said is written there too."""

    def __init__(self, apply: bool) -> None:
        self.file = None
        if not apply:
            return
        stamp = time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())
        path = tier.TMP / 'logs' / 'migration' / 'sync' / f'{stamp}.log'
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('w')
        head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
        self.say(f'migration sync - {stamp} - {provider.signature()} - {head or "(no git)"}')
        self.say('corpus-yoga migration sync --apply')
        self.say('')

    def say(self, line: str = '') -> None:
        print(line)
        if self.file:
            self.file.write(line + '\n')
            self.file.flush()


def sync(apply: bool) -> int:
    """One list of the scripts with steps; the flag decides only whether each is run with
    --apply after it is named. The status re-read is the certified state after the act,
    beneath the lines and above the verdict, which is the last line."""
    log = Log(apply)
    before = status_facts()
    owed = {name: s for name, s in before.scripts.items() if isinstance(s, Script) and s.steps}
    halted = {name: s.halted or [] for name, s in before.scripts.items() if isinstance(s, Script) and s.halted}
    steps = sum(len(s.steps or []) for s in owed.values())
    taken = 0
    failed: list[str] = []
    for name, script in owed.items():
        n = len(script.steps or [])
        log.say(f'  {name}: {n} step(s)' + ('' if apply else ' - --apply takes them'))
        if not apply:
            continue
        code, lines = run(REPO / name, apply=True)
        for line in lines:
            log.say(f'    {line}')
        if code == 0:
            taken += len(script.steps or [])
        else:
            failed.append(name)
    for name, lines in halted.items():
        log.say(f'  {name} halted - {"; ".join(lines)}')
    if not apply:
        log.say(f'migration sync: would run {len(owed)} script(s), {steps} step(s)' + (' (--apply runs them)' if steps else '')
                + (f'; {len(halted)} halted, the reader\'s' if halted else ''))
        return 0
    log.say('')
    for line in facts.lines(facts.plain(status_facts())):
        log.say(line)
    log.say('')
    undone = failed + list(halted)
    if undone:
        log.say(f'migration sync: NOT DONE - took {taken} of {steps} step(s); NOT taken ' + ', '.join(undone))
    else:
        log.say(f'migration sync: DONE - took {taken} step(s) of {len(owed)} script(s)')
    return 1 if undone else 0


def main() -> int:
    args = command_parser('migration').parse_args()
    if args.verb == 'sync':
        return sync(bool(args.apply))
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
