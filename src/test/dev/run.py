#!/usr/bin/env python
"""
run.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/dev/run.sh
    src/test/dev/run.sh --fix   # run all fix commands; stages nothing

As a git hook, install the wrapper:
    corpus-yoga test install-hook

Exits 0 if all checks pass, 1 if any fail.

Checks are grouped into two tiers, run in order - a commit's content, and nothing
else (issues/535: the corpus is the data gate's, corpus-yoga pipeline run):
    code    — repo code and documentation (required files, xref); deterministic on any clone
    schema  — committed schema artifacts (diagnostics, changelogs, joins, mcp currency);
              deterministic on any clone (mcp currency needs network)

Each check is declared once, beside its function in its subject's module under
src/test/dev/check/ (src/test/dev/gate.py's `check`): its tier, the names it reports and
the paths it reads. This runner derives its sections, its replay subjects and its expected
names from those declarations; every count is identical on every clone, and the log's head
line is the code+schema total. Machine state that SHOULD gate — the hook's own installation — is enforced by
the wrapper (run.sh), never by a tier.

Atomic diagnostic scripts live in src/test/dev/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/dev/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from gate import (
    write_check_logs,
    CHECKS,
    REPORT,
    REPORT_REL,
    REPO_ROOT,
    RSC,
    RSC_SCHEMA,
    SRC_TEST_DIAGNOSTICS,
    SRC_TEST_REPAIRS,
    _machine_anchor,
    _read_committed_xref,
)
import facts
import xref  # the gate's sibling, src/test/dev/xref.py
from tier import GATE_CHECK
import check
import pkgutil
import importlib

SELF = 'src/test/dev/run.py'
_file = Path(__file__).resolve()
assert any(p / SELF == _file for p in _file.parents), f'{_file} is not at its declared address {SELF}'

for _found in sorted(m.name for m in pkgutil.iter_modules(check.__path__)):
    importlib.import_module(f'check.{_found}')   # each subject's checks declare themselves as they load

# ── Incremental sections (issues/68) ────────────────────────────────────────────────
# A section re-runs only when its SUBJECT — the files it reads — has changed.
# Subjects are declared conservatively as repo-relative globs; 'TREE' means every
# tracked-or-untracked-unignored file. The two regenerated artifacts are excluded
# from every subject (they are outputs; nothing reads them — run.sh's comments are
# the authority), which is what makes run.sh's second run a total replay. The
# gate's own sources and the committed expectations are in EVERY subject, so a
# gate edit or an expectation edit re-runs everything. Escape hatch: --fresh.

GATE_SOURCES = ['src/test/dev/run.py', 'src/test/dev/gate.py', 'src/test/dev/check', 'src/test/dev/xref.py',
                'rsc/test/xref_expected_score']
ARTIFACTS = {'rsc/test/run.log', 'rsc/test/xref.csv'}
# the cache's own home: inside tmp/cache, which subject scans must skip -
# without this exclusion every run would dirty the sections that read it
CACHE_PREFIX = 'tmp/cache/test'
SCHEMA = ['rsc/schema']
MODEL = ['rsc/metamodel']   # the cross-family model: the table, its schema, the join, its kinds, the rejections

SUBJECTS: dict[str, list[str] | str] = {d.name: d.on for d in CHECKS if d.on is not None}   # each check's declared paths (issues/1023)

SECTION_CACHE = REPO_ROOT / 'tmp' / 'cache' / 'test' / 'sections.json'


def _tree_files():
    out = subprocess.run(['git', '-C', str(REPO_ROOT), 'ls-files', '--cached',
                          '--others', '--exclude-standard'],
                         capture_output=True, text=True)
    return [l for l in out.stdout.splitlines()
            if l and l not in ARTIFACTS and not l.startswith(CACHE_PREFIX)]


def subject_hash(spec) -> str:
    """Stat-hash (path, size, mtime_ns) of the subject's files — the make tradeoff:
    an mtime-preserving edit evades it, and --fresh exists. The gate's own sources
    ride every subject."""
    h = hashlib.sha256()
    if spec == 'TREE':
        rels = _tree_files()
    else:
        rels = []
        for g in [*GATE_SOURCES, *spec]:   # the gate's own sources expanded as a subject's are, its check modules among them
            root = REPO_ROOT / g
            if root.is_file():
                rels.append(g)
            elif root.is_dir():
                rels += [r for f in sorted(root.rglob('*'))
                         if f.is_file() and '__pycache__' not in f.parts
                         and not (r := str(f.relative_to(REPO_ROOT))).startswith(CACHE_PREFIX)
                         and r not in ARTIFACTS]
    for rel in sorted(set(rels)):
        f = REPO_ROOT / rel
        try:
            if rel.startswith(('tmp/', 'data/')):
                # tmp/ and data/ subjects are large and machine-local; their key
                # stays stat (size + mtime) as the DECLARED lawful difference
                # (issues/368): the tier is machine-local and never enters a committed
                # artifact, so a clock-faked miss costs a re-read, not a lie.
                st = f.stat()
                h.update(f'{rel}\0{st.st_size}\0{st.st_mtime_ns}\n'.encode())
            else:
                # Code and schema subjects key on CONTENT (issues/368): identical bytes
                # replay from any tree — a fresh worktree's birth-mtimes cannot
                # force a full run.
                h.update(f'{rel}\0'.encode())
                with open(f, 'rb') as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b''):
                        h.update(chunk)
                h.update(b'\n')
        except OSError:
            h.update(f'{rel}\0GONE\n'.encode())
    return h.hexdigest()


# ── Entry point ───────────────────────────────────────────────────────────────


@dataclass
class RunOnce:
    """One genuine pass over the check tier, plus its rendering — everything
    main()'s settle loop (issues/249) needs to compare against disk and, at the end,
    to write and print. Building this needs no knowledge of what is on disk;
    that comparison, and the decision whether to write, belong to main() alone."""
    committed_text:      str
    xref_csv_text:       str
    full_text:           str
    terminal_text:       str
    full_fix_lines:      list
    has_failures:        bool   # any failure at all — drives the exit code and --fix
    section_chunks:      dict   # each check's lines, by its name, for its own log (issues/1030)


def _run_once(allow_replay: bool) -> RunOnce:
    """Check (tree -> results, section-cache replay iff allow_replay), then render
    every surface from those results (issues/249's separation: a check computes, only
    render builds bytes). Writes NOTHING — not the committed artifacts, not even
    the machine-local log — because whether this run's bytes are new is a fact
    only main()'s settle loop can see, by comparing them against disk."""
    cache: dict = {}
    if allow_replay and SECTION_CACHE.exists():
        try:
            cache = json.loads(SECTION_CACHE.read_text())
        except (ValueError, OSError):
            cache = {}
    fresh_cache: dict = {}
    replayed: list[str] = []

    results = []
    # Two buffers: the committed rsc/test/run.log renders from results (identical
    # on any clone); the machine buffer holds the per-invocation body and the run's
    # anchor, written as the per-check report beside the record under tmp/logs/test/run/
    # (machine-facing) - a committed artifact never carries a machine fact.
    committed_buffer = io.StringIO()
    machine_buffer   = io.StringIO()
    cited_laws: dict[str, list[str]] = {}   # grammar law id -> the labels citing it
    check_types: list[str | None] = []     # per result: which TYPE of check it is an instance of

    def run(label, passed, detail=None, law=None, check=None):
        # `law` cites the law this fact enforces — a CLI grammar law from
        # src/main/cli/README.md (G<n>) or a corpus law from rsc/CALCULUS.md (L<n>), two
        # vocabularies because a check enforces either a surface law or a corpus one.
        # Space-separated when a check enforces more than one: accumulate's contract is
        # both L1 (re-deposit is silence) and L6 (a same-stamp mismatch is loud).
        # Recorded, not printed: the law checks read the citations to hold the documents
        # and the checks to each other, in both directions.
        results.append((label, passed, detail))
        # `check` is the check's TYPE — the thing a reader means by "a check". The label is
        # one INVOCATION of it, over one schema, command or conversation. Adding a schema
        # multiplies invocations and adds no check, which is why the committed expectation
        # is the set of types and not a count of lines.
        check_types.append(check)
        for cited in (law.split() if law else []):
            cited_laws.setdefault(cited, []).append(label)
        # One failure sigil (issues/530).
        mark = '✓' if passed else '✗'
        # per-INVOCATION, and only to the machine log: the committed body is grouped by
        # type (_by_type), so printing each instance there would defeat the point
        print(f'  {mark} {label}' + (f'\n      {detail}' if not passed and detail else ''),
              file=machine_buffer)

    # Each hint is deduplicated but remembers the tier it was raised in (the
    # committed log carries only deterministic-tier hints), every problem it
    # remedies — the tail prints problem statement(s) above each command; a bare
    # command with no statement of what it fixes is not a fix hint — and any
    # GUIDANCE: prose advice rendered as an indented note under the command and
    # NEVER passed to the --fix runner (prose is not executable).
    fix_hints:    list[str] = []
    fix_tier:     dict[str, str] = {}
    fix_problems: dict[str, list[str]] = {}
    fix_guidance: dict[str, list[str]] = {}

    def fix(hint: str, problem: str | None = None, guidance: str | None = None) -> None:
        if hint not in fix_tier:
            fix_hints.append(hint)
            fix_tier[hint] = current_tier[0] or 'schema'
            fix_problems[hint] = []
            fix_guidance[hint] = []
        if problem and problem not in fix_problems[hint]:
            fix_problems[hint].append(problem)
        if guidance and guidance not in fix_guidance[hint]:
            fix_guidance[hint].append(guidance)

    sections: list[str] = []
    tiers:    list[str] = []
    current_tier: list = [None]

    section_ms: dict[str, float] = {}
    section_chunks: dict[str, str] = {}

    def run_section(fn, label=None, tier='schema'):
        name = label or fn.__name__
        sys.stdout = machine_buffer
        if tier != current_tier[0]:
            current_tier[0] = tier
            print(f'\n# ════ {tier} tier {"═" * (66 - len(tier))}')   # a comment: the tier is a fold, not a section
        print(f'\n{name}: |')   # a section is a key with a literal block scalar, its lines beneath (issues/755)
        t0 = time.monotonic()
        sh = subject_hash(SUBJECTS[name]) if name in SUBJECTS else None
        entry = cache.get(name)
        if sh and entry and entry.get('hash') == sh:
            # REPLAY: the subject is unchanged, so the section's whole contribution —
            # results, types, law citations, fix hints, machine-log text — is the
            # recorded one. The committed log derives from results, so byte-stability
            # follows; a section that WROTE an artifact (xref) left it at its fixpoint.
            for label_, passed_, detail_ in entry['results']:
                results.append((label_, passed_, detail_))
            check_types.extend(entry['types'])
            for law_, labels_ in entry['laws'].items():
                cited_laws.setdefault(law_, []).extend(labels_)
            for hint_, problem_, guidance_ in entry['fix']:
                fix(hint_, problem_ or None, guidance_ or None)
            machine_buffer.write(entry['chunk'])
            section_chunks[name] = entry['chunk']
            n = len(entry['results'])
            sections.extend([name] * n)
            tiers.extend([tier] * n)
            fresh_cache[name] = entry
            replayed.append(name)
            section_ms[name] = (time.monotonic() - t0) * 1000
            return None
        before = len(results)
        laws_before = {k: len(v) for k, v in cited_laws.items()}
        fix_before = {h: (len(fix_problems[h]), len(fix_guidance[h])) for h in fix_hints}
        chunk_from = machine_buffer.tell()
        os.environ[GATE_CHECK] = f'{REPORT.stem}/{name}'   # an act the check runs is logged beneath it (issues/1030)
        try:
            ret = fn(run)
        finally:
            os.environ.pop(GATE_CHECK, None)
        section_chunks[name] = machine_buffer.getvalue()[chunk_from:]
        section_ms[name] = (time.monotonic() - t0) * 1000
        n = len(results) - before
        sections.extend([name] * n)
        tiers.extend([tier] * n)
        if sh:
            laws_delta = {k: v[laws_before.get(k, 0):] for k, v in cited_laws.items()
                          if len(v) > laws_before.get(k, 0)}
            fix_delta = []
            for h in fix_hints:
                pb, gb = fix_before.get(h, (0, 0))
                for pr in fix_problems[h][pb:]:
                    fix_delta.append((h, pr, ''))
                for gd in fix_guidance[h][gb:]:
                    fix_delta.append((h, '', gd))
                if h not in fix_before and not fix_problems[h] and not fix_guidance[h]:
                    fix_delta.append((h, '', ''))
            fresh_cache[name] = {
                'hash': sh,
                'results': [list(r) for r in results[before:]],
                'types': check_types[before:],
                'laws': laws_delta,
                'fix': fix_delta,
                'chunk': machine_buffer.getvalue()[chunk_from:],
            }
        return ret

    try:
        # every declared check, in its module's order; a check that reads what every other check
        # cited runs after them all, once the ledger is whole (issues/1023)
        returned: dict[str, object] = {}
        for declared in [d for d in CHECKS if not d.after_all] + [d for d in CHECKS if d.after_all]:
            if declared.after_all:
                returned[declared.name] = run_section(lambda run, _fn=declared.fn, _c=cited_laws: _fn(run, _c),
                                                      label=declared.name, tier=declared.tier)
            else:
                returned[declared.name] = run_section(declared.fn, tier=declared.tier)
        found = returned.get('check_xref')
        xref_rows = found if isinstance(found, list) else None




    finally:
        sys.stdout = sys.__stdout__

    # check_xref replayed: its subject (TREE) is unchanged, so it never ran and
    # xref_rows is None. The committed rsc/test/xref.csv is already at that
    # fixpoint — read it back rather than recomputing, so render still has a
    # table to write.
    if xref_rows is None:
        xref_rows = _read_committed_xref(RSC / 'test' / 'xref.csv')

    try:
        SECTION_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SECTION_CACHE.write_text(json.dumps(fresh_cache))
    except OSError:
        pass
    if replayed:
        print(f'  {len(replayed)} section(s) replayed unchanged '
              f'(code/schema subjects content-keyed, data subjects stat-keyed; '
              f'--fresh re-runs all)', file=sys.stderr)
    if os.environ.get('CORPUS_YOGA_GATE_TIMINGS'):
        for _n, _ms in sorted(section_ms.items(), key=lambda kv: -kv[1]):
            print(f'  {_ms:8.1f} ms  {_n}', file=sys.stderr)
        print(f'  {sum(section_ms.values()):8.1f} ms  TOTAL (sections)', file=sys.stderr)

    failures = [(n, d) for n, p, d in results if not p]

    # The one real judgment the old check_score held (pull/539 review, 2026-08-25:
    # "the code treats check_score as a check"): the run's check types match the
    # committed registry. A genuine, deterministic, code-tier check - counted,
    # gated, last in the table. The per-tier SUMMARY is not a check and lives in
    # the render as prose (_tier_fold), counted nowhere.
    expected_types = {name for declared in CHECKS for name in declared.says} | {'checks'}   # every name a check declares (issues/1023)
    seen_types = {t for t, tier in zip(check_types, tiers)
                  if t and tier in ('code', 'schema')} | {'checks'}   # itself included, stated

    print(f'\n── check_expectation {"─" * (74 - len("check_expectation"))}', file=machine_buffer)
    gone = sorted(expected_types - seen_types)
    added = sorted(seen_types - expected_types)
    for label, ok, detail in (
            ('checks: every declared check ran', not gone,
             f'declared but never reported - skipped, or its declaration outlived it: {", ".join(gone)}'
             if gone else None),
            ('checks: every check that ran is declared', not added,
             f'reported and declared by no check: {", ".join(added)} - declare it beside its function' if added else None)):
        results.append((label, ok, detail))
        check_types.append('checks')
        sections.append('check_expectation')
        tiers.append('code')
        print(f'  {"✓" if ok else "✗"} {label}'
              + (f'\n      {detail}' if not ok and detail else ''), file=machine_buffer)
        if not ok:
            failures.append((label, detail))

    # Per-tier counts, over EVERY result - so the table's sum IS the stated total.
    tier_counts: dict[str, list[int]] = {}
    for i, (_, p_, _) in enumerate(results):
        c = tier_counts.setdefault(tiers[i], [0, 0])
        c[0] += 1 if p_ else 0
        c[1] += 1
    det_got = sum(tier_counts.get(t, [0, 0])[0] for t in ('code', 'schema'))
    det_tot = sum(tier_counts.get(t, [0, 0])[1] for t in ('code', 'schema'))
    det     = f'{det_got}/{det_tot}'


    # ── report rendering ─────────────────────────────────────────────────────
    # Two renderings of one result set, split by determinism exactly as the tiers
    # are: the COMMITTED report (code+schema and their scores — byte-identical on
    # any clone; this script writes it to rsc/test/run.log itself) and the
    # FULL report (adds the run's anchor and the per-invocation body — printed to
    # stdout and written as the <stamp>.report beside the record under tmp/logs/test/run/).


    def _fix_lines(fail_list, hints):
        """Assemble the To-fix entries for a failure subset (no execution). Each
        entry is (problem statements, runnable command or None, guidance notes):
        a command is only intelligible under the ✗ it remedies; guidance is prose
        rendered under the command and NEVER executed; a None command (a failure
        with no repair/diagnostic script, only a prose detail) renders as ✗ +
        guidance alone. 'then: ' hints merge into the previous command line and
        contribute their problems and guidance to it."""
        fix_commands: list[str] = list(hints)
        problems: dict[str, list[str]] = {h: list(fix_problems.get(h, [])) for h in hints}
        guidance: dict[str, list[str]] = {h: list(fix_guidance.get(h, [])) for h in hints}
        prose_only: set[str] = set()   # keys that are advice, not commands

        def _add(cmd: str, problem: str | None = None, prose: bool = False) -> None:
            if cmd not in problems:
                fix_commands.append(cmd)
                problems[cmd] = []
                guidance[cmd] = []
                if prose:
                    prose_only.add(cmd)
            if problem and problem not in problems[cmd]:
                problems[cmd].append(problem)

        for name, detail in fail_list:
            parts = name.split(': ')
            if len(parts) == 3 and re.match(r'[a-z_]+\.[a-z_]+', parts[1]):
                diag = parts[1]
                schema_path = RSC_SCHEMA / parts[0] / f'{parts[2]}.json'
                repair     = SRC_TEST_REPAIRS     / f'{diag}.py'
                diagnostic = SRC_TEST_DIAGNOSTICS / f'{diag}.py'
                if repair.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif diagnostic.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif detail:
                    _add(detail, name, prose=True)   # a detail is advice, not a command

        lines: list[tuple[list[str], str | None, list[str]]] = []
        for cmd in fix_commands:
            ps, gs = problems.get(cmd, []), guidance.get(cmd, [])
            if cmd in prose_only:
                lines.append((list(ps), None, [cmd] + list(gs)))
            elif cmd.startswith('then: '):
                actual = cmd[len('then: '):]
                if lines and (prev_cmd := lines[-1][1]) is not None:
                    prev_ps, _, prev_gs = lines[-1]
                    # splice before any trailing '  # …' comment — appending after
                    # it would bury the follow-up inside the comment, silently
                    # unexecuted under --fix
                    base, sep, note = prev_cmd.partition('  # ')
                    merged = f'{base}; {actual}' + (f'  # {note}' if sep else '')
                    lines[-1] = (prev_ps + [p for p in ps if p not in prev_ps],
                                 merged,
                                 prev_gs + [g for g in gs if g not in prev_gs])
                else:
                    lines.append((list(ps), actual, list(gs)))
            else:
                actual = cmd[len('Run: '):] if cmd.startswith('Run: ') else cmd
                lines.append((list(ps), actual, list(gs)))
        return lines

    def _write_fixes(out, lines, mark):
        for ps, cmd, gs in lines:
            for p in ps[:3]:
                out.write(f'  {mark} {p}\n')
            if len(ps) > 3:
                out.write(f'  {mark} … and {len(ps) - 3} more like these\n')
            if cmd is not None:
                out.write(f'    {cmd}\n')
            for g in gs:
                out.write(f'      ↳ {g}\n')

    def _by_type(idxs) -> str:
        """The body, one line per CHECK rather than one per invocation — with failures
        enumerated beneath their type.

        The collapse is deliberately ASYMMETRIC. Fifty identical ticks say what one tick and
        a count say, so a passing type is one line; a failing type lists the instances that
        failed, and only those. The noise removed is the ✓s, which are the whole reason the
        ✗s were hard to find. The count carries what the old body could not: `(16/17)` is one
        command misbehaving, `(3/17)` is something structural.

        Every invocation stays in the per-check report (one stamped .report per run under tmp/logs/test/run/, beside the record),
        where evidence belongs; this is the file a human reads in a diff."""
        out, seen_section = io.StringIO(), None
        order: dict[tuple, list] = {}
        for i in idxs:
            order.setdefault((sections[i], check_types[i] or results[i][0]), []).append(i)
        for (section, ctype), members in order.items():
            if section != seen_section:
                seen_section = section
                out.write(f'\n{section}: |\n')
            failed = [i for i in members if not results[i][1]]
            mark = '✓' if not failed else '✗'
            n = len(members)
            count = f'  ({n - len(failed)}/{n})' if n > 1 else ''
            out.write(f'  {mark} {ctype}{count}\n')
            for i in failed:                      # only the failures are named
                label, _, detail = results[i]
                out.write(f'      {label}\n')
                if detail:
                    out.write(f'          {detail}\n')
        return out.getvalue()

    def _render(surface: str, full_report: str | None = None):
        """Render one report variant; returns (text, runnable fix lines) — results ->
        artifact bytes, a pure function of (results, surface) (issues/249). Three surfaces:
        'committed' is rsc/test/run.log (code+schema only, byte-identical on any
        clone); 'full' is the stamped .report under tmp/logs/test/run/ (adds the run's anchor and body);
        'terminal' drops the per-check ✓/✗ body, leaving header + tail, and points
        at the full report for detail — pass its already-rendered text as
        full_report, since the terminal has no body of its own to anchor its stage
        table into (issues/254). The tail is binary (issues/530, retiring the 2026-07-12
        advisory split): the FINAL word states what the hook does — FAIL with
        the failing sections and their remedies, or an explicit PASS."""
        committed_only = surface == 'committed'
        include_body   = surface != 'terminal'
        idxs       = list(range(len(results)))
        fail_idx   = [i for i in idxs if not results[i][1]]
        fail_sections = list(dict.fromkeys(sections[i] for i in fail_idx))
        out = io.StringIO()

        # The machine-facing log opens by anchoring its evidence (issues/365): room,
        # commit and dirty-state, like the usr gate's run log — both gates
        # uptier together. The committed surface stays machine-invariant by law
        # (L2) and never carries it; the anchor rides INSIDE the render so the
        # stamped machine-log line-anchors stay true.
        if surface == 'full':
            out.write(_machine_anchor() + '\n')

        if fail_idx:
            out.write(f'`src/test/dev/run.py`: code+schema {det} ('
                      f'{len(fail_sections)} section(s) failing)\n')
        else:
            out.write(f'run.py: code+schema {det}\n')

        out.write('\n')
        if include_body:
            out.write(_by_type(idxs))
            if not committed_only:
                out.write(machine_buffer.getvalue())
        else:
            out.write(f'full per-check report: {REPORT_REL}\n')

        # One row per STAGE — the same shape `corpus-yoga pipeline run` prints, so a reader of
        # either report answers the same question the same way: which stages ran, what
        # each found, and where to look. A stage here is a check_* section: not typeable
        # (unlike a pipeline stage), so the row anchors to the line instead of a command.
        stage_rows: dict[str, list[int]] = {}
        for i in idxs:
            stage_rows.setdefault(sections[i], []).append(i)

        # The anchor is computed against the bytes of the surface it names, never
        # against a surface's own text when that text has no banners to find (issues/254):
        # 'committed' and 'full' both just wrote the per-check body above, so they
        # anchor into themselves; 'terminal' wrote none, so it anchors into the full
        # report instead, naming the file it points into. Every stage in stage_rows
        # has a banner in its anchor source by construction — both are built from
        # the same idxs — so a direct lookup, never a zero-defaulting fallback, is
        # the honest form: a stage missing its banner is a bug to surface, not a
        # line number to fake.
        if surface == 'terminal':
            assert full_report is not None, 'terminal render needs the full report to anchor into'
            anchor_source, anchor_prefix = full_report, f'{REPORT_REL}:'
        else:
            anchor_source, anchor_prefix = out.getvalue(), ''
        banner_line: dict[str, int] = {}
        for line_number, text in enumerate(anchor_source.splitlines(), 1):
            opened = re.match(r'^(\w+): \|$', text)
            if opened:
                banner_line[opened.group(1)] = line_number
        anchors = {stage: f'{anchor_prefix}{banner_line[stage]}' for stage in stage_rows}

        # tier per stage, from the registrations (issues/538): every member invocation of a
        # stage shares one declared tier except check_score, whose rows summarise
        # tiers - a mixed stage prints the sorted union, still read off the data.
        stage_tier = {stage: '+'.join(sorted({tiers[i] for i in members}))
                      for stage, members in stage_rows.items()}
        # the stages as facts (issues/755): each with what it passed and failed, its tier and where
        # it begins - a line of this report, or of the full report the terminal points into
        stages = {stage: {'passes': len(members) - sum(1 for i in members if not results[i][1]),
                          'failures': sum(1 for i in members if not results[i][1]),
                          'tier': stage_tier[stage], 'line': anchors[stage]}
                  for stage, members in stage_rows.items()}
        out.write('\n' + '\n'.join(facts.lines({'stages': stages})) + '\n')

        # The per-tier fold - a SUMMARY, not a check (pull/539 review, 2026-08-25):
        # untiered prose, counted nowhere, derived here from the same results the
        # table counts, so the two cannot disagree.
        def _n_types(t):
            return len({ty for ty, tier in zip(check_types, tiers) if ty and tier == t})
        out.write(f'\nchecks[code+schema]: {len(seen_types)} types, {det} invocations passing\n')
        for t in ('code', 'schema'):
            got_, tot_ = tier_counts.get(t, [0, 0])
            out.write(f'checks[{t}]: {_n_types(t)} types, {got_}/{tot_} invocations passing\n')

        # Final: the gate's one verdict (issues/530 - no advisory tier stands between).
        lines: list[tuple[list[str], str | None, list[str]]] = []
        if fail_idx:
            counts = {sec: sum(1 for i in fail_idx if sections[i] == sec) for sec in fail_sections}
            out.write('\ndev gate: FAIL - these gate; the hook vetoes the commit, and any run '
                      'exits non-zero\n')
            for sec in fail_sections:
                out.write(f'  {sec} ({counts[sec]})\n')
            gate_fails = [(results[i][0], results[i][2]) for i in fail_idx]
            gate_lines = _fix_lines(gate_fails, fix_hints)
            if gate_lines:
                out.write('\nTo fix:\n')
                _write_fixes(out, gate_lines, '✗')
            lines += gate_lines
        else:
            out.write(f'\ndev gate: PASS - code+schema {det} match the committed expectation; '
                      'nothing here vetoes a commit. What this gate cannot arbitrate - '
                      'that the verbs run - is the usr gate\'s, corpus-yoga pipeline run\n')
        # The verdict is the terminal word — no trailing offer after it. The
        # remediation each finding needs is already printed beside it (the
        # gate's "To fix"). We do NOT append a
        # blanket "or run with --fix to apply and stage automatically": it would fire
        # even on a clean PASS, sit after the
        # verdict where its "or" has no antecedent, and over-promise — the surviving
        # items here are cmd-less curation advice --fix never executes, and --fix does
        # not stage. --fix stays available
        # for anyone who invokes it deliberately (see --help); it just isn't
        # advertised after every run.
        return out.getvalue(), lines

    # Render every surface from this run's results. Nothing is written here —
    # not the committed artifacts, not the machine-local log — that decision
    # belongs to main()'s settle loop (issues/249), which alone knows what is on disk.
    committed_text, _         = _render('committed')
    full_text, full_fix_lines = _render('full')
    terminal_text, _          = _render('terminal', full_text)
    xref_csv_text             = xref.render_csv(xref_rows)

    # Every failure vetoes (issues/530): the gate holds a commit's content and nothing
    # else (issues/535), so its verdict is the same in every room.
    return RunOnce(
        committed_text=committed_text,
        xref_csv_text=xref_csv_text,
        full_text=full_text,
        terminal_text=terminal_text,
        full_fix_lines=full_fix_lines,
        has_failures=bool(failures),
        section_chunks=section_chunks,
    )


def _on_disk(path: Path, newline: str | None) -> str | None:
    """The committed artifact's current bytes, or None if it does not exist yet —
    a missing file can never equal an in-memory result, so it always takes the
    settle loop's write-and-confirm branch (issues/249)."""
    try:
        return path.read_text(newline=newline)
    except OSError:
        return None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--fresh', action='store_true',
                    help='ignore the section cache: re-run every check')
    args = ap.parse_args()

    committed_path = RSC / 'test' / 'run.log'
    xref_path      = RSC / 'test' / 'xref.csv'

    # THE SETTLE LOOP (issues/249), one discipline: check and render build every
    # output in memory; a committed artifact is written only when
    # its bytes differ from what is already on disk, and a write is trusted
    # only once a GENUINELY FRESH recomputation (no section-cache replay, ever,
    # regardless of --fresh) agrees with what was just written. A clean tree
    # settles on the first run, with zero writes and no mtime disturbed. A
    # changed tree writes, confirms once; if the confirmation still differs it
    # writes again and confirms a second time — at most three runs total, two
    # stability diffs, short-circuiting at the first match either way. A result
    # that still will not settle after that budget is a fault, not a commit:
    # the run exits non-zero naming the file, and nothing further is written.
    run_result = _run_once(allow_replay=not args.fresh)
    disk_committed = _on_disk(committed_path, None)
    disk_xref      = _on_disk(xref_path, '')

    settled_result: RunOnce | None = None
    written_committed, written_xref = disk_committed, disk_xref

    if run_result.committed_text == disk_committed and run_result.xref_csv_text == disk_xref:
        settled_result = run_result
    else:
        pending = run_result
        for _ in range(2):   # at most two confirmation runs
            committed_path.write_text(pending.committed_text)
            xref_path.write_text(pending.xref_csv_text, newline='')
            written_committed, written_xref = pending.committed_text, pending.xref_csv_text
            confirmed = _run_once(allow_replay=False)
            if confirmed.committed_text == written_committed \
                    and confirmed.xref_csv_text == written_xref:
                settled_result = confirmed
                break
            pending = confirmed
        else:
            run_result = pending   # unsettled — reported below, never staged

    fault_files = [] if settled_result is not None else [
        name for name, current, written in (
            ('rsc/test/run.log', run_result.committed_text, written_committed),
            ('rsc/test/xref.csv', run_result.xref_csv_text, written_xref),
        ) if current != written
    ]
    final = settled_result if settled_result is not None else run_result

    # The per-check report and the terminal report are per-run emissions —
    # unlike the committed artifacts, nothing gates whether they are written;
    # they always describe this invocation's final (settled or faulted) state.
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(final.full_text)
    write_check_logs(REPORT.with_suffix(''), final.section_chunks)   # each check's own log beside the report (issues/1030)

    print(final.terminal_text, end='')

    if fault_files:
        print(f"ERROR: these results will not settle: {', '.join(fault_files)}",
              file=sys.stderr)
        sys.exit(1)

    if final.has_failures and args.fix and final.full_fix_lines:
        print()
        print('Running fixes:')
        for ps, cmd, gs in final.full_fix_lines:
            for p in ps[:3]:
                print(f'  ✗ {p}')
            if cmd is None:
                # advice, not a command — print it, never execute it
                for g in gs:
                    print(f'      ↳ {g}')
                continue
            print(f'  {cmd}')
            # A hint names the command a reader types, which is `corpus-yoga` — on a PATH only an
            # installed clone has. Run it through this repo's own entrypoint, so the hint
            # stays typeable prose and still executes in a clone that installed nothing.
            run_as = f'./{cmd}' if cmd.startswith('corpus-yoga ') else cmd
            subprocess.run(run_as, shell=True, cwd=REPO_ROOT)
            for g in gs:
                print(f'      ↳ {g}')
        print()
        # Nothing is staged here, deliberately. `git add` cannot be undone: it
        # cannot tell "the tool staged this" from "this was already staged,
        # differently", so a blanket `git add -u` over a hunk staged with
        # `git add -p` destroys that state with nothing to restore it from. The
        # fixes are in the worktree; what enters the commit stays the operator's
        # to say.
        #
        # This run's own exit code and the artifacts it just wrote are the
        # PRE-fix verdict — checking happens before this loop runs, and the
        # settle loop above already wrote rsc/test/run.log and rsc/test/xref.csv
        # from that pre-fix state. A reader who stops at this terminal's exit
        # code sees the failures the fixes just repaired, not the current
        # truth — the prescription below is how they learn there is a truth
        # still to check.
        print('Fixes applied to the worktree — nothing staged. Review with '
              '`git diff`, stage what you meant, then verify:')
        print('    → run: corpus-yoga test run')

    sys.exit(1 if final.has_failures else 0)


if __name__ == '__main__':
    main()
