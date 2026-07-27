#!/usr/bin/env python
"""
run.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/run.sh
    src/test/run.sh --fix   # run all fix commands; stages nothing

As a git hook, install the wrapper:
    yoga test install-hook

Exits 0 if all checks pass, 1 if any fail.

Checks are grouped into three tiers, run in order:
    code    — repo code and documentation (required files, xref); deterministic on any clone
    schema  — committed schema artifacts (diagnostics, changelogs, joins, mcp currency);
              deterministic on any clone (mcp currency needs network)
    data    — local data/input//tmp/cache/ data vs the committed record (validation outputs, coverage,
              frontier); machine-local, skipped per pipeline where no local data exists

The committed expected checks (rsc/test/run_expected_checks) record the code and
schema tiers only — their counts are identical on every clone. Its first line is the
combined code+schema total, which also matches the score in the log's head line. The
data tier's subtotal is machine-local and never recorded; its failures are reported in
full but never veto the exit — a fact about this machine's data must not gate an
unrelated commit. Machine state that SHOULD gate — the hook's own installation — is
enforced by the wrapper (run.sh), never by a tier.

Atomic diagnostic scripts live in src/test/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import ast
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Repo layout ───────────────────────────────────────────────────────────────
REPO_ROOT                = Path(__file__).resolve().parents[2]
INPUT                    = REPO_ROOT / 'data' / 'input'
CACHE                    = REPO_ROOT / 'tmp' / 'cache'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
RSC_SCHEMA               = RSC / 'schema'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ — shared modules live at its root
from validation_matrix import rows_from_logs  # noqa: E402

sys.path.insert(0, str(SRC / 'main'))  # markdown_projection owns the format, both directions
from markdown_projection import conv_id as _conv_id, turn_seq  # noqa: E402
from send import SWITCH as SEND_SWITCH, may_send  # noqa: E402 — the one reading of the send switch

sys.path.insert(0, str(SRC / 'main' / 'cli'))  # the yoga CLI cluster (dispatch + standalone commands)
import cli  # noqa: E402 — the CLI table machinery (check_cli_surface)
import commands as cli_commands  # noqa: E402 — `yoga commands` answers itself here
import completions as cli_completions  # noqa: E402 — and `yoga completions` here
import cache_io  # noqa: E402 — the declared tmp/cache/ IO registry (check_cache_io)

sys.path.insert(0, str(SRC / 'main' / 'chat-exports'))  # the shared deposit rule (check_accumulate_contract)
import accumulate as _accumulate  # noqa: E402 — the CALCULUS accumulate operation (issue #22)

sys.path.insert(0, str(SRC / 'main' / 'model'))  # index curation machinery
from indexing import inferred_concepts, orphan_headwords, pending_concepts  # noqa: E402
import model_curation  # noqa: E402 — the model.json disposal queue (issue #19)

# ── Pipeline model ────────────────────────────────────────────────────────────

@dataclass
class Pipeline:
    schemas:         list[str]
    changelog:       Path
    cache_output:    Path
    input:           Path
    input_glob:      str
    subject_depth:   int
    # Per-item remedy command; takes the pipeline's TOP-LEVEL data/input/ entry (see _fix_item_cmd).
    fix_item_cmd:    str
    # Extra diagnostics to skip beyond the universal versioned-schema skip set.
    # composition.base_schemas_closed — session deviation: TurnBase intentionally open (see principles.md).
    diagnostic_skip:    frozenset[str] = frozenset()
    gen_key_prefix:     str = ''
    # A second input shape the pipeline demands beyond input_glob — code-agents'
    # per-project memory/ dirs beside its per-session .jsonl files. Same subject
    # depth; the trailing-slash convention (dirs vs files) is per glob.
    extra_input_glob:   str = ''

PIPELINES: dict[str, Pipeline] = {
    'browser-captures': Pipeline(
        schemas           = ['apiConversation'],
        changelog         = RSC_SCHEMA / 'browser-captures' / 'apiConversation' / 'CHANGELOG.md',
        cache_output      = REPO_ROOT / cache_io.path_for('browser-captures'),
        input             = INPUT / 'claude' / 'chat' / 'browser-API',
        input_glob        = '*/',
        subject_depth     = 1,
        fix_item_cmd      = 'yoga pipeline run browser-captures',
    ),
    'chat-exports': Pipeline(
        schemas           = ['conversations', 'memories', 'projects', 'users'],
        changelog         = RSC_SCHEMA / 'chat-exports' / 'conversations' / 'CHANGELOG.md',
        cache_output      = REPO_ROOT / cache_io.path_for('chat-exports'),
        input             = INPUT / 'claude' / 'chat' / 'bulk-export',
        input_glob        = 'data-*/',
        subject_depth     = 1,
        fix_item_cmd      = 'yoga pipeline run chat-exports',
    ),
    'code-agents': Pipeline(
        schemas           = ['session', 'sessionConversation', 'projectMemory'],
        changelog         = RSC_SCHEMA / 'code-agents' / 'session' / 'CHANGELOG.md',
        cache_output      = REPO_ROOT / cache_io.path_for('code-agents'),
        # The pipeline sources the repo-owned STORE (machines → projects →
        # sessions), never the harness-owned ~/.claude/projects — transport
        # is the capture step that populates it.
        input             = INPUT / 'claude' / 'code' / 'machine-transport',
        input_glob        = '*/-Users-*/*.jsonl',
        subject_depth     = 3,
        # validate.sh --code-agent-session consumes the tmp/cache/ session dir (conversion
        # from .jsonl comes first), so the runnable store-rooted unit is the project run.sh.
        fix_item_cmd      = 'yoga pipeline run code-agents',
        diagnostic_skip   = frozenset({'composition.base_schemas_closed'}),
        # Each project's memory/ is its own datum (projectMemory), a subject beside
        # the project's sessions: tmp/cache/code-agents/<machine>/<project>/memory/.
        extra_input_glob  = '*/-Users-*/memory/',
    ),
}

# Map schema name → its directory, derived from PIPELINES.
SCHEMA_DIR: dict[str, Path] = {
    schema: RSC_SCHEMA / name / schema
    for name, pipeline in PIPELINES.items()
    for schema in pipeline.schemas
}


def _parse_matrix_file(path: Path) -> dict[tuple[str, str, str], str]:
    """(schema, item, version) → ✓/✗/? parsed from a datum's matrix.md table."""
    rows: dict[tuple[str, str, str], str] = {}
    for line in path.read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 4:
            continue
        m = re.search(r'v\d+', cells[2])
        if not m or cells[3] not in ('✓', '✗', '?'):
            continue
        rows[(cells[0].strip('`'), cells[1].strip('`'), m.group())] = cells[3]
    return rows


def _leaf(subject: str) -> str:
    """Check-label form of a subject: the leaf (uuid/name) only. Depth-2 subjects are
    '<project-slug> / <uuid>' internally (the slug is needed to reconstruct paths), but
    labels use just the uuid — uniform with the depth-1 pipelines, and the committed
    run.log then carries no machine-derived slugs (they embed the username)."""
    return subject.split(' / ')[-1]


def _fix_item_cmd(pipeline: Pipeline, subject: str) -> str:
    """The runnable remedy for one subject: the pipeline's fix_item_cmd plus the
    subject's CONTAINER in data/input/ — the granularity every per-item command
    actually accepts (the subject minus its leaf; the whole subject at depth 1).
    A depth-3 subject ('<machine> / <project> / <uuid>') therefore hints at its
    machine/project dir; joining the full subject would name a path no command
    consumes (and, for code-agents, one that does not even exist as given)."""
    parts = subject.split(' / ')
    item = pipeline.input.joinpath(*(parts[:-1] or parts))
    return f'{pipeline.fix_item_cmd} {item.relative_to(REPO_ROOT)}'


def _datum_dirs(pipeline: Pipeline) -> list[Path]:
    """Each datum directory in tmp/cache/ (the dirs that contain a validation/ subdir),
    at the pipeline's subject depth."""
    glob = '/'.join(['*'] * pipeline.subject_depth) + '/validation'
    return sorted(v.parent for v in pipeline.cache_output.glob(glob) if v.is_dir())

# ── Helpers ───────────────────────────────────────────────────────────────────

def _call(script, *args):
    result = subprocess.run(
        [sys.executable, str(script)] + list(args),
        capture_output=True, text=True
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def _call_many(jobs):
    """[(script, arg)] -> [(passed, output)] in JOB ORDER, run concurrently.

    Each diagnostic is a separate interpreter start (~30ms), and the suite makes ~1400 of
    them: that WAS the runtime — 44s wall at 95% of one core, while nine sat idle. The
    children are independent by construction (each reads one schema and writes nothing), so
    the only thing serialising them was the loop.

    Order is restored before anything is reported, so the committed log is unchanged and the
    parallelism is invisible in the artifact. run() is still called from one thread, in
    sequence — a report assembled in completion order would differ run to run, which is
    exactly what the committed log must not do (L2)."""
    if not jobs:
        return []
    from concurrent.futures import ThreadPoolExecutor
    workers = min(len(jobs), (os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda j: _call(j[0], str(j[1])), jobs))


def _walk_pointer(doc: object, pointer: str) -> bool:
    node: Any = doc
    for tok in pointer.lstrip('/').split('/'):
        tok = tok.replace('~1', '/').replace('~0', '~')
        try:
            if isinstance(node, dict):
                node = node[tok]
            elif isinstance(node, list):
                node = node[int(tok)]
            else:
                return False
        except (KeyError, IndexError, ValueError):
            return False
    return True


def _diag_detail(output):
    lines = output.splitlines()
    if len(lines) > 1:
        return '\n    '.join(lines[1:])
    return lines[0] if lines else None


def _sorted_versions(schema_dir: Path) -> list[Path]:
    """Return all v*.json in schema_dir sorted by version number ascending."""
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )




def _input_subjects(pipeline: Pipeline) -> list:
    """Each input entry as its cache subject: a bare name at depth 1, else the
    tuple of path parts relative to the input root (files contribute their
    stem — the .jsonl becomes the session dir's name)."""
    if not pipeline.input.exists():
        return []
    globs = [g for g in (pipeline.input_glob, pipeline.extra_input_glob) if g]
    if pipeline.subject_depth == 1:
        return sorted(d.name for g in globs
                      for d in pipeline.input.glob(g.rstrip('/')) if d.is_dir())
    result = []
    for pattern in globs:
        glob      = pattern.rstrip('/')
        dirs_only = pattern.endswith('/')
        for item in sorted(pipeline.input.glob(glob)):
            if item.is_dir() != dirs_only:
                continue
            rel   = item.relative_to(pipeline.input)
            parts = rel.parts[:-1] + (item.name if dirs_only else item.stem,)
            parts = (parts[0].removeprefix(pipeline.gen_key_prefix),) + parts[1:]
            result.append(parts)
    return sorted(result)


def _has_local_data(pipeline: Pipeline) -> bool:
    """True if this machine holds any data for the pipeline — input entries in data/input/ or
    previously generated output in tmp/cache/. Gates the data tier: where neither exists the
    pipeline's data checks are skipped (the committed matrices are the durable record)."""
    if _input_subjects(pipeline):
        return True
    return pipeline.cache_output.exists() and any(pipeline.cache_output.iterdir())


def _check_csv_pointers(csv_path: Path, columns: tuple, base_for: dict, fails: list) -> None:
    """Validate JSON Pointer fragments in a join CSV. base_for maps column name → base dir.
    A cell may name a .json file directly, or a versioned FAMILY DIR — the de-versioned
    grammar — in which case the pointer resolves against the family's LATEST version,
    so a mint that renames or removes a referenced definition fails here (the review
    prompt), and a mint that keeps it costs the join table nothing."""
    with csv_path.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in columns:
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (base_for.get(col, RSC_SCHEMA) / file_part).resolve()
                if not f.exists():
                    fails.append(f'row {i} {col}: file not found: {file_part}')
                    continue
                if f.is_dir():
                    versions = _sorted_versions(f)
                    if not versions:
                        fails.append(f'row {i} {col}: no v*.json in family dir: {file_part}')
                        continue
                    f = versions[-1]
                if pointer and f.suffix == '.json':
                    try:
                        doc = json.loads(f.read_text())
                    except json.JSONDecodeError:
                        fails.append(f'row {i} {col}: invalid JSON: {file_part}')
                        continue
                    if not _walk_pointer(doc, pointer):
                        fails.append(f'row {i} {col}: bad pointer: {ref}')


# ── Checks ────────────────────────────────────────────────────────────────────

def check_required_files(run):
    # Only files named independently of the live tree -- walking rsc/schema/ for v*.json and then
    # asserting those same paths exist is tautological (it requires whatever is present); a missing
    # schema dir simply has no versions and is invisible to the family walks instead.
    required = [
        *[SRC / 'main' / name / 'validate.sh' for name in PIPELINES if name != 'browser-captures'],
        SRC / 'main' / 'browser-captures' / 'claude' / 'validate.sh',
        SRC  / 'main' / 'validate.py',
        SRC  / 'main' / 'model' / 'gen_model_candidate.py',
        SRC  / 'main' / 'model' / 'model.py',
        RSC  / 'test' / 'run_expected_checks',
        RSC  / 'test' / 'xref_expected_score',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'run_python_script.sh',
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists(), check='files.required_exists')


def check_root_schema_diagnostics(run):
    root_schemas = sorted(RSC_SCHEMA.glob('*.json'))
    diagnostics  = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))

    jobs = [(script, schema_path) for schema_path in root_schemas for script in diagnostics]
    for (script, schema_path), (passed, output) in zip(jobs, _call_many(jobs)):
        run(f'{script.stem}: {schema_path.relative_to(RSC_SCHEMA)}', passed,
            _diag_detail(output) if not passed else None, check=script.stem)


def _schema_families() -> dict:
    """Every versioned schema family ON DISK ({name: dir}) — the scope for all
    schema-tier per-family checks. Not derived from the pipelines' schemas lists:
    a family can exist outside any pipeline (markdownConversation is validated
    in-memory at projection time) and must still be checked."""
    return {d.name: d for d in sorted(RSC_SCHEMA.glob('*/*'))
            if d.is_dir() and list(d.glob('v*.json'))}


def check_schema_validity(run) -> None:
    """Every version of every schema family parses and declares $schema — a property
    of the committed schema artifacts, not of any pipeline."""
    for schema_name, schema_dir in sorted(_schema_families().items()):
        for path in _sorted_versions(schema_dir):
            v = path.stem
            try:
                schema = json.loads(path.read_text())
                run(f'{schema_name}: valid JSON + $schema: {v}', '$schema' in schema,
                    'Missing $schema field' if '$schema' not in schema else None, check='schema.valid_json_with_schema')
            except json.JSONDecodeError as e:
                run(f'{schema_name}: valid JSON: {v}', False, str(e), check='schema.valid_json')


def check_schema_changelogs(run) -> None:
    """Every schema family's CHANGELOG narrates every version, and no version carries
    TODO descriptions — properties of the committed artifacts, not of any pipeline.
    (Whether each version is registered in the validation matrix is the data-tier
    concern, checked where local data exists.)"""
    for schema_name, schema_dir in sorted(_schema_families().items()):
        changelog = schema_dir / 'CHANGELOG.md'
        changelog_text = changelog.read_text() if changelog.exists() else ''
        for path in _sorted_versions(schema_dir):
            v = path.stem
            run(f'{schema_name}: changelog_narrative: {v}',
                f'## {v}' in changelog_text,
                f'Add a ## {v} section to {changelog.relative_to(REPO_ROOT)}'
                if f'## {v}' not in changelog_text else None, check='schema.changelog_narrative')
            schema_text = path.read_text()
            run(f'{schema_name}: no_todo: {v}',
                '"TODO' not in schema_text,
                f'Replace TODO descriptions in {path.relative_to(REPO_ROOT)}'
                if '"TODO' in schema_text else None, check='schema.changelog_no_todo')


def check_pipeline_validation_outputs(run, fix, name: str, pipeline: Pipeline) -> None:
    """Each datum's matrix.md must exist and agree with the vN.log files beside it;
    every schema version must be registered by some datum; every input entry must
    have been processed. Matrices are co-located with their data, so stale rows for
    departed data cannot exist — deleting a datum deletes its matrix."""
    run_cmd  = f'yoga pipeline sync {name}'
    pipe_cmd = f'yoga pipeline run {name}'
    gen_rel  = pipeline.cache_output.relative_to(REPO_ROOT)

    print(f'\n  each {gen_rel}/<datum>/matrix.md must match the vN.log files under its validation/')
    seen_versions: dict[str, set[str]] = {}
    processed_subjects: set[str] = set()
    for datum_dir in _datum_dirs(pipeline):
        subject  = ' / '.join(datum_dir.relative_to(pipeline.cache_output).parts)
        processed_subjects.add(subject)
        expected = rows_from_logs(datum_dir)
        for (schema, _item, version) in expected:
            seen_versions.setdefault(schema, set()).add(version)
        mfile = datum_dir / 'matrix.md'
        if not mfile.exists():
            fix(run_cmd, problem=f'matrix.written: {_leaf(subject)} — matrix.md missing')
            run(f'matrix.written: {_leaf(subject)}', False, str(mfile.relative_to(REPO_ROOT)), check='data.matrix_written')
            continue
        actual = _parse_matrix_file(mfile)
        ok = actual == {k: sym for k, (sym, _) in expected.items()}
        if not ok:
            fix(run_cmd, problem=f'matrix.current: {_leaf(subject)} — matrix.md disagrees with validation logs')
        run(f'matrix.current: {_leaf(subject)}', ok,
            None if ok else f'matrix.md disagrees with validation logs — regenerate: {run_cmd}', check='data.matrix_current')

    # Every schema version must be registered by some local datum — no version minted
    # without data validated against it. Data-tier counterpart of the narrative check.
    for schema in pipeline.schemas:
        for vpath in _sorted_versions(SCHEMA_DIR[schema]):
            v  = vpath.stem
            ok = v in seen_versions.get(schema, set())
            if not ok:
                fix(pipe_cmd, problem=f'{schema}: matrix.version_registered: {v} — '
                                      f'no local datum has validated against {v}')
                fix(f'then: {run_cmd}')
            run(f'{schema}: matrix.version_registered: {v}', ok, check='data.version_registered')

    print(f'\n  every {pipeline.input.relative_to(REPO_ROOT)}/{pipeline.input_glob} entry should have validation output in {gen_rel}/')
    raw_input = _input_subjects(pipeline)
    current_subjects = (
        raw_input if pipeline.subject_depth == 1
        else [' / '.join(parts) for parts in raw_input]
    )
    for subject in sorted(current_subjects):
        if subject not in processed_subjects:
            fix(pipe_cmd, problem=f'unprocessed input: {_leaf(subject)} — no validation output in {gen_rel}/')
            fix(f'then: {run_cmd}')
            run(f'unprocessed input: {_leaf(subject)}', False, check='data.input_processed')


def _gen_subject_dirs(gen_dir, depth):
    """Yield (subject, leaf_dir) for each subject directory in gen_dir, at any
    depth (the subject is the ' / '-joined path parts)."""
    if not gen_dir.exists():
        return
    for leaf in sorted(gen_dir.glob('/'.join(['*'] * depth))):
        if leaf.is_dir():
            yield ' / '.join(leaf.relative_to(gen_dir).parts), leaf


def _datum_recency(name: str, pipeline: Pipeline, subject: str):
    """A sortable recency key for one datum, or None if unavailable. Pipeline-specific,
    because the corpora differ: chat-exports uses the epoch embedded in the batch dir name;
    browser-captures the capture's `updated_at`; code-agents the max record `timestamp` in
    the session `.jsonl`. Keys are only ever compared within a single pipeline, so mixing
    int (epoch) and ISO-string (timestamp) types across pipelines is fine."""
    if name == 'chat-exports':
        m = re.search(r'-(\d{10})-[0-9a-f]+-batch', subject)
        return int(m.group(1)) if m else None
    if name == 'browser-captures':
        f = pipeline.input / subject / f'{subject}.json'
        try:
            return json.loads(f.read_text()).get('updated_at')
        except (OSError, ValueError):
            return None
    if name == 'code-agents':
        f = pipeline.input.joinpath(*subject.split(' / ')).with_suffix('.jsonl')
        try:
            lines = f.read_text().splitlines()
        except OSError:
            return None
        stamps = []
        for line in lines:
            try:
                t = json.loads(line).get('timestamp')
            except ValueError:
                continue
            if t:
                stamps.append(t)
        return max(stamps) if stamps else None
    return None


def check_pipeline_coverage(run, fix, pipeline: Pipeline) -> None:
    """Every datum must validate against at least one schema version. A datum that validates
    against none is unmodelled drift — evolve the schema (or record why it is permanently
    invalid). Older data may sit below the latest version; that is fine (see check_frontier)."""
    schema   = pipeline.changelog.parent.name
    versions = _sorted_versions(SCHEMA_DIR[schema])
    if not versions:
        return
    for subject, leaf_dir in _gen_subject_dirs(pipeline.cache_output, pipeline.subject_depth):
        logs = [leaf_dir / 'validation' / schema / f'{v.stem}.log' for v in versions]
        logs = [l for l in logs if l.exists()]
        if not logs:
            continue
        passing = any('Valid!' in l.read_text() for l in logs)
        label = f'{schema}: modelled by some version: {_leaf(subject)}'
        if not passing:
            fix(f'{_fix_item_cmd(pipeline, subject)}  # refresh the evidence '
                '(only helps if data or schemas changed since the logs were written)',
                problem=f'{label} — validates against no schema version',
                guidance='if the ✗ persists: follow rsc/schema/WORKFLOW.md to add or adjust a '
                         'schema version — current evidence means only a schema change can clear it')
        run(label, passing, None if passing else 'validates against no schema version', check='data.validates_against_a_version')


def check_pipeline_frontier(run, fix, name: str, pipeline: Pipeline) -> None:
    """The most recent datum must validate against the latest schema version — so the schema
    frontier tracks the data frontier (no unmodelled newest export, no version minted ahead of
    all data). Recency is pipeline-specific; see _datum_recency."""
    schema   = pipeline.changelog.parent.name
    versions = _sorted_versions(SCHEMA_DIR[schema])
    if not versions:
        return
    latest   = versions[-1].stem
    keyed    = []
    for subject, leaf_dir in _gen_subject_dirs(pipeline.cache_output, pipeline.subject_depth):
        key = _datum_recency(name, pipeline, subject)
        if key is not None:
            keyed.append((key, subject, leaf_dir))
    if not keyed:
        return
    _, subject, leaf_dir = max(keyed, key=lambda k: k[0])
    log = leaf_dir / 'validation' / schema / f'{latest}.log'
    ok  = log.exists() and 'Valid!' in log.read_text()
    label = f'{schema}: latest datum validates against latest ({latest}): {_leaf(subject)}'
    if not ok:
        fix(f'{_fix_item_cmd(pipeline, subject)}  # refresh the evidence '
            '(only helps if data or schemas changed since the logs were written)',
            problem=label,
            guidance='if the ✗ persists: follow rsc/schema/WORKFLOW.md to add or adjust a '
                     'schema version — current evidence means only a schema change can clear it')
    run(label, ok, None if ok else str(log.relative_to(REPO_ROOT)), check='data.frontier_current')


def check_index_curation(run, fix) -> None:
    """Indexing data obeys the schema system's disposal rigour: every concept the
    capture proposes (data/output/dashboard/semantic-concepts.json) is either ACCEPTED — covered
    by a headword or alias in data/output/indexing/accepted.txt — or REJECTED in
    data/output/indexing/rejected.txt; anything else is pending curation and says so here.
    All inputs live in the iCloud-shared data/output/ (not git), so this is a DATA-tier
    check — machine-local, advisory (an undisposed concept must not block an
    unrelated commit), skipped where data/output/ has no capture. The pending queue itself
    is the reproducible derivation tmp/cache/indexing/candidates.txt (yoga indexing
    candidates), a rebuildable workshop file, not a committed artifact."""
    concepts = inferred_concepts()
    if not concepts:
        print('  – skipped: no concept capture yet (data/output/dashboard/semantic-concepts.json — run `yoga dashboard capture`)')
        return
    pending = set(pending_concepts(REPO_ROOT / 'data' / 'output' / 'indexing' / 'accepted.txt',
                                   REPO_ROOT / 'data' / 'output' / 'indexing' / 'rejected.txt'))
    # One line per pending concept, no per-row remedy — 27 identical two-line
    # remedies were the mumble; the single fix hint below carries it once.
    for c in concepts:
        disposed = c not in pending
        run(f'indexing: concept disposed: {c}', disposed, check='indexing.concept_disposed')
        if not disposed:
            fix('yoga indexing candidates  # write the pending queue: tmp/cache/indexing/candidates.txt',
                problem=f'indexing: concept undisposed: {c}',
                guidance='dispose each pending concept: yoga indexing accept <term> [alias ...] '
                         '| yoga indexing reject [--reason <why>] <concept>')
    # The REVERSE direction (the curate symmetry, PR #36's model.json precedent:
    # a curation record must be grounded both ways). An accepted headword with
    # ZERO corpus locators is orphan documentation — a dead index entry whose
    # concept left the corpus or whose aliases never matched. indexing's sync
    # line has always carried the located/total ratio; this names the orphans.
    # Advisory like the rest of this section: the corpus is machine-local data.
    markdown_root = REPO_ROOT / 'data' / 'output' / 'markdown'
    if markdown_root.is_dir():
        for h in orphan_headwords(markdown_root,
                                  REPO_ROOT / 'data' / 'output' / 'indexing' / 'accepted.txt'):
            run(f'indexing: headword grounded: {h}', False, check='indexing.headword_grounded')
            fix('yoga indexing   # status names each orphan headword',
                problem=f'indexing: headword ungrounded: {h} (zero corpus locators)',
                guidance='fix the aliases on its accepted.txt line, or remove the line '
                         'and reject the concept with a reason')


def check_cross_sources(run) -> None:
    """Append-only invariant across export surfaces: every conversation present in BOTH
    a bulk export and the live captures must project to a turn sequence identical to,
    or a prefix of, the capture's — a bulk export is a point-in-time snapshot and
    conversations only ever gain turns. The capture being a prefix of the EXPORT is
    the mirror case: a stale capture, fixed by recapturing that conversation (the
    remedy is printed). Divergence inside the shared prefix means a projection bug
    or data corruption (or a post-export edit/branch switch — rare; investigate
    with compare_sources --diff). Reads the projections both pipelines already
    wrote to tmp/cache/; machine-local, so data tier."""
    api_dir = REPO_ROOT / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations'
    api = {}
    if api_dir.is_dir():
        for f in api_dir.glob('*.md'):
            text = f.read_text()
            cid = _conv_id(text)
            if cid:
                api[cid] = turn_seq(text)
    if not api:
        print('  – skipped: no api projections (data/output/markdown/claude/chat/conversations empty)')
        return
    batch_dirs = sorted((CACHE / 'chat-exports').glob('data-*/markdown')) if (CACHE / 'chat-exports').is_dir() else []
    if not batch_dirs:
        print('  – skipped: no bulk-export projections (tmp/cache/chat-exports/*/markdown empty)')
        return
    for mdir in batch_dirs:
        identical = appended = shared = 0
        stale, divergent = [], []
        for f in sorted(mdir.glob('*.md')):
            text = f.read_text()
            cid = _conv_id(text)
            if not cid or cid not in api:
                continue
            shared += 1
            b, a = turn_seq(text), api[cid]
            if b == a:
                identical += 1
            elif len(b) < len(a) and a[:len(b)] == b:
                appended += 1
            elif len(b) > len(a) and b[:len(a)] == a:
                stale.append((cid, f.stem))
            else:
                divergent.append(cid)
        detail_parts = []
        for cid, name in stale[:5]:
            detail_parts.append(
                f"capture-stale {name!r} ({cid}) — the export extends the capture; to recapture:"
                f"\n        → run: yoga browser capture --provider claude --id {cid}"
                f"  # first front https://claude.ai/chat/{cid} in Safari (logged in)")
        if divergent:
            detail_parts.append('divergent (projection bug, corruption, or post-export edit): '
                                + ', '.join(divergent[:5]))
        run(f'cross-source: {mdir.parent.name}: {shared} shared — '
            f'{identical} identical, {appended} appended-to'
            + (f', {len(stale)} capture-stale' if stale else ''),
            not (stale or divergent),
            '\n      '.join(detail_parts) if detail_parts else None, check='data.cross_source_transcripts_agree')


def check_cache_io(run) -> None:
    """The declared tmp/cache/ IO registry (rsc/cache_io.csv) must not lie: it parses, it
    covers every pipeline's gen root (so clean and sync know the pipelines),
    and — the catastrophe guard — no subtree is READ with no WRITER. A tmp/cache/ path
    the machinery consumes but nothing produces breaks the 'tmp/cache/ is reproducible
    from data/input/' contract: a fresh clone, or `yoga cache clean`, would strand the
    reader. Written-but-not-read is fine (a terminal output — a page a browser
    reads); only the read side lacking a writer is fatal. Committed registry
    only, so deterministic on any clone: code tier."""
    try:
        rows = cache_io.rows()
    except Exception as e:
        run('cache_io: registry parses: rsc/cache_io.csv', False, str(e), check='cache_io.registry_parses')
        return
    run('cache_io: registry parses: rsc/cache_io.csv', True, check='cache_io.registry_parses')

    # PIPELINES now derives cache_output from cache_io.path_for(), so a pipeline
    # missing its row fails loudly at import; this catches the reverse — a
    # pipeline TAG in cache_io naming no real pipeline (or a mismatch either way).
    tagged = cache_io.pipelines()
    run('cache_io: pipeline tags match PIPELINES', tagged == set(PIPELINES),
        f'cache_io tags {sorted(tagged)} != PIPELINES {sorted(PIPELINES)}'
        if tagged != set(PIPELINES) else None, check='cache_io.pipeline_tags_match')

    commands = {c['command'] for c in cli.commands()}
    for r in rows:
        # read-but-not-written: the catastrophe (see docstring).
        read_no_writer = bool(r['read_by']) and not r['written_by']
        run(f'cache_io: {r["cache_path"]}: read implies a writer', not read_no_writer,
            'READ but not WRITTEN — a tmp/cache/ dependency nothing produces; name its '
            'producer in written_by, or the tmp/cache/ contract breaks' if read_no_writer else None, check='cache_io.read_implies_writer')
        # Every producer/reader RESOLVES — a rename that strands one (how
        # tmp/cache/browser-captures/markdown happened) fails here, not silently.
        unresolved = [e for e in r['written_by'] + r['read_by']
                      if not _cache_io_resolves(e, commands)]
        run(f'cache_io: {r["cache_path"]}: producers/readers resolve', not unresolved,
            f'unresolved: {", ".join(unresolved)}' if unresolved else None, check='cache_io.paths_resolve')


def _cache_io_resolves(entry: str, commands: set[str]) -> bool:
    """A cache_io written_by/read_by entry resolves iff it is an `external:*` reader
    (exempt), a `yoga <cmd>` whose command is in the table, or a path (its first
    token) that exists in the repo."""
    if entry.startswith('external:'):
        return True
    if entry.startswith('yoga '):
        return entry.split()[1] in commands
    return (REPO_ROOT / entry.lstrip('./').split()[0]).exists()


def check_cli_surface(run) -> None:
    """The yoga CLI's table (rsc/cli/) is an interface and must not
    lie: it parses, command names are unique, every target exists, every
    calculus term a row cites is defined in rsc/CALCULUS.md (the vocabulary is
    parsed from the document itself), every flag a usage sketch advertises
    appears in the target's source or its stem-sibling .py/.sh pair (wrapper
    and implementation share a stem — the repo idiom), every subcommand VERB it
    advertises appears in the target's own --help (the live dispatch surface —
    a source grep is vacuous for ordinary words like build/accept), and every command
    a declared `step` marks is invoked BY COMMAND AND VERB in the src/main/pipeline.sh --plan
    output (which is itself the executing list, so the chain cannot drift, and a step
    cannot quietly drop to a bare noun that the bare=status convention no-ops). Committed
    files and the deterministic plan only, so deterministic on any clone:
    code tier."""
    try:
        cmds = cli.commands()
    except Exception as e:
        run('cli: table parses: rsc/cli/', False, str(e), law='G4', check='cli.table_parses')
        return
    run('cli: table parses: rsc/cli/', True, law='G4', check='cli.table_parses')
    names = [c['command'] for c in cmds]
    dupes = sorted({n for n in names if names.count(n) > 1})
    run('cli: command names unique', not dupes, ', '.join(dupes) if dupes else None,
        law='G4', check='cli.commands_unique')
    # alphabetical by contract (2026-07-15): every surface derived from the table
    # (help, synopsis, completion) inherits its order, so the table carries it
    run('cli: commands alphabetical', names == sorted(names),
        None if names == sorted(names) else
        f'first out of order: {next(a for a, b in zip(names, sorted(names)) if a != b)}',
        law='G4', check='cli.commands_alphabetical')
    vocab = cli.calculus_terms()
    for c in cmds:
        target = REPO_ROOT / c['target']
        run(f'cli: {c["command"]}: target exists: {c["target"]}', target.exists(), law='G7', check='cli.target_exists')
        unknown = [t for t in c['calculus'].split() if t not in vocab]
        run(f'cli: {c["command"]}: cited calculus defined', not unknown,
            f'not defined in rsc/CALCULUS.md: {", ".join(unknown)}' if unknown else None,
            law='G6', check='cli.calculus_defined')
        # subcommands and flags are read from rsc/cli/ — the single source the
        # usage is generated from — so there is no usage cell to reconcile it against, and
        # no completeness check: the two cannot drift because there is only one.
        flags = cli.flags_of(c['command'])
        subcommands = cli.subcommands_of(c['command'])
        if not (flags or subcommands) or not target.exists():
            continue
        sources = [target] + [s for s in (target.with_suffix('.py'), target.with_suffix('.sh'))
                              if s != target and s.exists()]
        text = ''.join(s.read_text() for s in sources)
        where = ('not in ' + ' or '.join(str(s.relative_to(REPO_ROOT)) for s in sources) + ': ')
        if flags:
            missing = [f for f in flags if f not in text]
            run(f'cli: {c["command"]}: advertised flags exist', not missing,
                (where + ', '.join(missing)) if missing else None, law='G5', check='cli.advertised_flags_exist')
        # Docstring honesty (issue #33): a module docstring's Usage block is a
        # declared surface too, and nothing read it against the parser —
        # memories' documented three flags no parser defined, and both checks
        # here were satisfied (the declaration honestly advertised none; the lie lived
        # only in the docstring). Every --flag a Usage block cites must be
        # advertised; real ⊆ advertised is held below, so advertised is the one
        # universe a documented flag can exist in.
        doc: set[str] = set()
        for m in re.finditer(r'^Usage.*?(?=\n"""|\n\'\'\'|\Z)', text, flags=re.M | re.S):
            doc.update(re.findall(r'--[a-z][\w-]+', m.group(0)))
        doc.discard('--help')
        undeclared = sorted(doc - set(flags))
        run(f'cli: {c["command"]}: docstring Usage flags advertised', not undeclared,
            f'documented in a Usage block but not declared: {", ".join(undeclared)}'
            if undeclared else None, law='G5', check='cli.docstring_flags_advertised')
        # the target's own --help is the authority on its live surface — fetched
        # once here for both directions of the honesty check
        runner = REPO_ROOT / 'src' / 'run_python_script.sh'
        help_cmd = ([str(runner), str(target), '--help'] if target.suffix == '.py'
                    else [str(target), '--help'])
        proc = subprocess.run(help_cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        help_text = proc.stdout + proc.stderr
        if subcommands:
            # An advertised subcommand must be REALLY dispatched, not a word in the help
            # prose (2026-07-18: a `model project` once advertised a subcommand no
            # subparser dispatched, and a bare-word grep could never tell). argparse
            # renders its subparsers as a {a,b,c} choice block — parse it and require
            # each advertised subcommand to be an actual choice. Shell targets carry no such
            # block, so there we fall back to matching their printed usage.
            choice_blocks = re.findall(r'\{([a-z0-9][a-z0-9,_-]*)\}', help_text)
            if choice_blocks:
                real = {v for blk in choice_blocks for v in blk.split(',')}
                missing_sub = [s for s in subcommands if s not in real]
                detail = (f'not real subcommands (target dispatches {sorted(real)}): '
                          f'{", ".join(missing_sub)}') if missing_sub else None
            else:
                # No {…} block: a shell target (subcommands in its printed usage), or a
                # cli.py-targeted row — `cli.py --help` renders the command TABLE, not the
                # parser cli.py builds for a command it handles itself, so that parser's
                # choice block never reaches this text. Accept a subcommand that appears
                # as a word in the target's --help OR as a dispatch literal in its source
                # — either is real evidence it is handled, not prose.
                missing_sub = [s for s in subcommands
                               if not re.search(rf'\b{re.escape(s)}\b', help_text)
                               and not re.search(rf'\b{re.escape(s)}\b', text)]
                detail = (f'{c["target"]} neither prints nor dispatches: {", ".join(missing_sub)}'
                          if missing_sub else None)
            run(f'cli: {c["command"]}: advertised subcommands dispatch', not missing_sub, detail,
                law='G5', check='cli.subcommands_dispatch')
        # The REVERSE direction (2026-07-16): every flag the target itself declares
        # must be advertised in the usage cell. The one-way check let the table
        # under-tell — `yoga commands` rendered a synopsis hiding memories' three
        # flags, xref's --out, supersede's four — and nothing cared until a reader
        # did. Harvest only DECLARING lines: argparse option lines (leading
        # whitespace, then --flag) and invocation lines naming the command or
        # target, with trailing '# …' comments stripped (prose cites foreign
        # flags: `git diff --cached`). Under-harvest is safe — the claim is
        # real ⊆ advertised, so a missed declaration weakens, never falsifies.
        real: set[str] = set()
        for line in help_text.splitlines():
            m = re.match(r'\s+(--[a-z][\w-]*)', line)
            if m:
                real.add(m.group(1))
                continue
            if f'yoga {c["command"]} ' in line or f'{target.name} ' in line or '$0' in line:
                real.update(re.findall(r'--[a-z][\w-]+', line.split(' # ')[0]))
        real.discard('--help')
        unadvertised = sorted(real - set(flags))
        run(f'cli: {c["command"]}: target flags all advertised', not unadvertised,
            f'target --help declares flags the usage cell omits: {", ".join(unadvertised)}'
            if unadvertised else None, law='G5', check='cli.target_flags_advertised')
        # Positionally usable where advertised (issue #33): the declaration renders a
        # command-level flag beside the verbs and completion offers it after
        # them, but summaries' four lived only on the command parser — argparse
        # hands a subparser everything after the verb token, so the advertised
        # `yoga summaries sync --summaries-output …` died with `unrecognized
        # arguments`. The observable: an argparse verb's own --help lists every
        # flag that verb accepts, so each command-level flag must appear there
        # (argparse_help.add_dir_flags wires the inherited copies). cli.py
        # targets are excluded as above; shell targets parse no verbs.
        cmd_level = [r['arg-name'] for r in cli.command_rows(c['command'])
                     if not r['subcommand'] and r['arg-name'].startswith('--')]
        if cmd_level and subcommands and target.suffix == '.py' and not c['target'].endswith('cli.py'):
            for verb in subcommands:
                vproc = subprocess.run([str(runner), str(target), verb, '--help'],
                                       capture_output=True, text=True, cwd=REPO_ROOT)
                vhelp = vproc.stdout + vproc.stderr
                rejected = [f for f in cmd_level if f not in vhelp]
                run(f'cli: {c["command"]}: {verb} accepts the command-level flags', not rejected,
                    f'`yoga {c["command"]} {verb}` rejects advertised flag(s): {", ".join(rejected)}'
                    if rejected else None, law='G5', check='cli.verb_accepts_command_flags')
        # Uniform SHAPE, enforced (2026-07-16): a --help is a man entry — name,
        # what, usage, flags — and fits one screen. Length is the cheapest proxy
        # a gate can hold; the essays this bound evicted live on in code
        # comments and changelogs, where they belong.
        if not c['target'].endswith('cli.py'):
            # cli.py-targeted rows (commands, completions) answer --help with the
            # whole derived surface — their help IS the product, unbounded by design
            n_lines = len(help_text.rstrip().splitlines())
            run(f'cli: {c["command"]}: help fits one screen (≤20 lines)', n_lines <= 20,
                f'{n_lines} lines — trim to the shape: name, what, usage, flags' if n_lines > 20 else None,
                law='G8', check='cli.help_one_screen')
    # The emitted completion is a zsh PROGRAM, not prose — it must parse. The
    # 2026-07-15 lesson: a '(--a|--b)' usage leaked '--b)' through flags_of and
    # the installed file failed to load, silently costing completion entirely;
    # no gate parsed what the ritual installs. zsh-less clones skip the parse
    # invisibly (constant label, no detail) so the committed log stays
    # byte-identical; every machine runs macOS, where the check is real.
    import shutil, tempfile
    zsh = shutil.which('zsh')
    parse_ok, parse_err = True, None
    if zsh:
        with tempfile.NamedTemporaryFile('w', suffix='_yoga', delete=False) as f:
            f.write(cli_completions.completion_script(cmds))
            tmp = f.name
        proc = subprocess.run([zsh, '-n', tmp], capture_output=True, text=True)
        Path(tmp).unlink()
        parse_ok, parse_err = proc.returncode == 0, (proc.stderr.strip() or None)
    run('cli: completions: emitted script parses (zsh -n)', parse_ok,
        parse_err if not parse_ok else None, law='G9', check='cli.completions_parse')

    # A command determines its target's name (#40): the target column is verification
    # rather than curation. Every row complies, so the record that declared the ones that
    # did not is gone — the last two left it when `yoga commands` and `yoga completions`
    # were extracted to files of their own, and a disposal record with nothing to dispose
    # of is a file that can only rot.
    for c in cmds:
        stem = Path(c['target']).stem
        # Case is part of a name, and the two kinds of target carry different conventions,
        # so each is held to ITS OWN rather than both to a case-folded comparison:
        #   executable → named for its command exactly:      prerequisites.sh
        #   document   → the repo's SHOUTING doc convention: CALCULUS.md
        # A .md target is PRINTED, not executed (see dispatch), and all 18 markdown
        # documents here are uppercase — four READMEs, eleven CHANGELOGs, WORKFLOW.
        want = c['command'].upper() if Path(c['target']).suffix == '.md' else c['command']
        run(f'cli: {c["command"]}: target is named for the command', stem == want,
            None if stem == want else
            f'target {c["target"]} has stem `{stem}`, not `{want}` — a command determines '
            f'its target\'s name, so rename the target or the command',
            check='naming.target_stem_matches_command')

    # Shell files are linted by shellcheck rather than by anything hand-rolled here: a
    # second vocabulary to police a first is exactly what a check should not be. It found
    # `yoga test run` written in backticks inside a double-quoted echo — command
    # substitution, not quoting, so the plan RAN the gate it was describing while
    # promising "nothing executed" — and an `echo "$(cmd)"` wrapping a command that
    # already prints.
    #
    # Absent, it skips with a CONSTANT label and no detail, so the committed report stays
    # byte-identical on a clone without it (the zsh -n precedent). `yoga prerequisites`
    # is the one voice that says whether this machine has it.
    shellcheck = shutil.which('shellcheck')
    sh_files = sorted(str(f) for f in (REPO_ROOT / 'src').rglob('*.sh'))
    sc_ok, sc_detail = True, None
    if shellcheck and sh_files:
        # -x follows the `# shellcheck source=` directives five files already write;
        # without it those lines are decoration and the sourced vocabulary is unknown
        proc = subprocess.run([shellcheck, '-x', '-f', 'gcc', *sh_files],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        findings = [l for l in proc.stdout.splitlines() if l.strip()]
        sc_ok = not findings
        sc_detail = None if sc_ok else '; '.join(
            f.replace(str(REPO_ROOT) + '/', '') for f in findings[:4])
    run('shell: shellcheck reports nothing', sc_ok, sc_detail,
        check='shell.shellcheck_clean')
    # A command's log path derives from the command (#54): having typed `yoga <noun>
    # <verb>`, a reader can guess where the log went without reading the script that
    # wrote it. Held over the SOURCE — every tmp/logs/ path any file names must open
    # with a command word — because the directories themselves exist only on a machine
    # that has run something, and a check that passes for want of evidence is worse
    # than none. Validation logs are exempt by living under tmp/cache/ beside the datum
    # they memoise: the log IS the memoisation (L1), not run history.
    commands_words = {c['command'] for c in cmds}
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sh', '.applescript', '.md'):
            continue
        # RELATIVE to the repo: an absolute-parts test excluded every file whenever the
        # checkout itself sat under a directory called tmp — which a scratch worktree
        # does, so the check examined nothing and passed. `every expected check ran`
        # caught it; a vacuous check that reports success is worse than no check.
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] in ('tmp', '.git', 'data'):
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.finditer(r"tmp/logs/([A-Za-z0-9_.-]+)", text):
            seg = m.group(1)
            ok = seg in commands_words or seg in ('...', '<command>')
            run(f'logs: {rel}: tmp/logs/{seg}/ opens with a command word', ok,
                None if ok else
                f'{rel} writes or names tmp/logs/{seg}/, and `{seg}` is no command — a '
                f"reader cannot derive it from what they typed",
                check='naming.log_path_derives_from_command')

    # What the repo PRESCRIBES, in both the senses #46 and #76 ask for: the form of an
    # invocation (a yoga command, never a script path) and its validity (flags the
    # command actually advertises). One scan serves both — they are two halves of one
    # sentence about prescribed invocations, and splitting them would mean writing the
    # scanner twice.
    #
    # A PRESCRIPTION is a line carrying one of the repo's markers for "type this":
    # → run:, reinstall:, replace:, refresh:, install via:. The same set the to-do check
    # keys on, because a line that prescribes a remedy and a line that IS a remedy are
    # the same line. Code that merely calls a script is not prescribing it, so an
    # invocation elsewhere in a line is left alone — the distinction a grep for `src/`
    # could not make.
    prescriptions = []
    for path in sorted(REPO_ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sh', '.md', '.json', '.applescript'):
            continue
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] in ('tmp', '.git', 'data') or str(rel) == 'rsc/test/xref.csv':
            continue
        for i, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
            m = re.search(r'(?:→ run:|reinstall:|replace:|refresh:|install via:)\s+(\S+)(.*)', line)
            if m:
                prescriptions.append((rel, i, m.group(1), m.group(2)))
    run('prescriptions: some line prescribes something', bool(prescriptions),
        None if prescriptions else 'no `→ run:` line found — the scan is looking in the wrong place',
        law='G17', check='output.prescriptions_are_commands')

    # Those prescriptions are lines this repo PRINTS, and the scan sees only the ones a
    # clone prints. The data tier's remedies need data to print, so a remedy naming a
    # script by path is invisible to any scan of output on a repo that ships none. They
    # are read from the source instead: every `*_cmd` a remedy is built from must name a
    # yoga command, whether or not this machine can print it.
    for node in ast.walk(ast.parse((SRC / 'test' / 'run.py').read_text())):
        if isinstance(node, ast.Assign) and node.targets and \
                isinstance(node.targets[0], ast.Name) and node.targets[0].id.endswith('_cmd'):
            name, val = node.targets[0].id, node.value
        elif isinstance(node, ast.keyword) and (node.arg or '').endswith('_cmd'):
            name, val = node.arg, node.value
        else:
            continue
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            head = val.value.split()[:1]
        elif isinstance(val, ast.JoinedStr) and val.values and isinstance(val.values[0], ast.Constant):
            head = str(val.values[0].value).split()[:1]
        else:
            continue                      # computed elsewhere; nothing to read here
        if not head:
            continue
        ok = head[0] == 'yoga'
        run(f'remedy: {name} at src/test/run.py:{val.lineno} names a yoga command', ok,
            None if ok else
            f'`{head[0]}` is a path, not a command a reader types — and this remedy prints '
            f'only on a machine with data, where no scan of output can reach it',
            law='G17', check='output.prescriptions_are_commands')

    declared = {c['command'] for c in cmds}
    # The scan reads SOURCE, so a token can carry the quoting and punctuation of the
    # string it sits in, and a remedy can be interpolated at run time. Neither is a
    # defect in the prescription, so both are handled rather than reported:
    #   `browser capture'`   the closing quote of the python literal
    #   `$remedy`, `{c}`     the invocation is computed, and cannot be read here
    # And a STANDARD tool is not what #46 objects to — its complaint is a repo script
    # prescribed by path, which a reader cannot type and cannot find.
    STANDARD = {'rm', 'mv', 'cp', 'ln', 'git', 'brew', 'echo', 'mkdir', 'open', 'pip'}
    def clean(tok):
        return tok.strip('`\'",;)').lstrip('./')

    def unreadable(tok):
        # a regex or a format string, not an invocation — including this scanner's own
        # pattern, which it finds in its own source and cannot be expected to parse
        return not tok or any(c in tok for c in '$({\\')
    for rel, i, head, rest in prescriptions:
        head = clean(head)
        if unreadable(head):
            continue                      # computed at run time, or not an invocation
        if head in STANDARD:
            continue
        ok = head == 'yoga' or head in declared
        run(f'prescription: {rel}:{i} names a yoga command', ok,
            None if ok else f'`→ run: {head}` prescribes a path, not a command a reader types',
            law='G17', check='output.prescriptions_are_commands')
        if not ok:
            continue
        words = [clean(w) for w in (rest if head == 'yoga' else f' {head}{rest}').split()]
        words = [w for w in words if not unreadable(w)]
        cmd = next((w for w in words if not w.startswith('-')), None)
        if cmd is None or cmd not in declared:
            continue
        verbs = set(cli.subcommands_of(cmd))
        after = words[words.index(cmd) + 1:]
        verb = after[0] if after and not after[0].startswith('-') else ''
        if verb and verb not in verbs:
            run(f'prescription: {rel}:{i} names a verb `{cmd}` has', False,
                f'`{cmd} {verb}` — its verbs are {sorted(verbs) or "(none)"}',
                law='G17', check='output.prescriptions_are_commands')
            continue
        advertised = {r['arg-name'] for r in cli.command_rows(cmd)
                      if r['arg-name'].startswith('--') and r['subcommand'] in ('', verb)}
        used = [w for w in after if w.startswith('--')]
        unknown = [f for f in used if f not in advertised]
        form = f'{cmd} {verb}'.strip()
        run(f'prescription: {rel}:{i} names flags `{form}` advertises', not unknown,
            None if not unknown else
            f'{", ".join(unknown)} — advertised: {sorted(advertised) or "(none)"}',
            law='G17', check='output.prescriptions_are_commands')

    # A report line that prescribes a REMEDY is a to-do, and must be emitted as one:
    # `sync` lists the to-dos, so an actionable line left as `info` is invisible there
    # while the report still shows it — and `sync` then says "every prerequisite is
    # satisfied" about a machine that has work outstanding. Four lines were exactly that
    # when sync landed, two of them inside case arms my reclassification pass never
    # matched. The markers below are the unambiguous ones: "populate via" and "stash it"
    # sit on lines describing absent DATA, which is context, not a task.
    prereq = (REPO_ROOT / 'src' / 'prerequisites.sh').read_text()
    REMEDY = ('→ run:', 'install via:', 'reinstall:', 'refresh:')
    mislabelled = [line.strip()[:80] for line in prereq.splitlines()
                   if 'info "' in line and any(m in line for m in REMEDY)]
    run('prerequisites: every line prescribing a remedy is emitted as a to-do',
        not mislabelled,
        None if not mislabelled else
        f'{len(mislabelled)} info line(s) carry a remedy and so never reach `sync`: '
        + '; '.join(mislabelled[:2]),
        check='output.remedy_lines_are_todos')

    # One venv, declared in several shell entrypoints and once more for the editor —
    # so they are read and compared rather than described. The comment that used to
    # carry this named two of the three files that set it, which is how a list-shaped
    # comment rots: the third was added and nothing pointed at it.
    venv_defaults = {}
    for sh in sorted((REPO_ROOT / 'src').rglob('*.sh')):
        for m in re.finditer(r'\$\{VENV:=([^}]+)\}', sh.read_text()):
            venv_defaults.setdefault(m.group(1), []).append(str(sh.relative_to(REPO_ROOT)))
    agree = len(venv_defaults) == 1
    run('venv: every entrypoint defaults it to the same place', agree,
        None if agree else '; '.join(f'{v} in {", ".join(f_)}' for v, f_ in venv_defaults.items()),
        check='naming.venv_default_agrees')
    if agree:
        declared = next(iter(venv_defaults)).replace('$HOME', '${env:HOME}')
        want = f'{declared}/bin/python'
        ws_text = (REPO_ROOT / 'claude-export-yoga.code-workspace').read_text()
        found = re.search(r'"python\.defaultInterpreterPath":\s*"([^"]+)"', ws_text)
        editor_ok = bool(found) and found.group(1) == want
        run('venv: the editor interpreter is that same venv', editor_ok,
            None if editor_ok else
            f'the workspace names {found.group(1) if found else "(nothing)"}, the entrypoints '
            f'{want} — an editor resolving against a different venv sees different packages',
            check='naming.venv_default_agrees')

    # A send is refusable through one switch, and src/main/send.py is the only place that
    # reads it out of the environment. One reading means refusal cannot come to mean two
    # things: raise for a send that IS the work, skip for one that only checks stored data.
    #
    # Read by AST, not by pattern. A regex over the literal name is blind to the reading
    # that imports SWITCH and passes it as a variable — which is the reading a second
    # module would most naturally write, having found the constant. Naming the switch in
    # prose stays free; only reaching into the environment for it is confined.
    def _reads_switch(path):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            return False
        aliases = {SEND_SWITCH}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'send':
                for a in node.names:
                    if a.name == 'SWITCH':
                        aliases.add(a.asname or a.name)
        for node in ast.walk(tree):
            arg = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ('get', 'getenv') and node.args:
                arg = node.args[0]
            elif isinstance(node, ast.Subscript):
                arg = node.slice
            if isinstance(arg, ast.Constant) and arg.value == SEND_SWITCH:
                return True
            if isinstance(arg, ast.Name) and arg.id in aliases:
                return True
        return False

    holder = REPO_ROOT / 'src' / 'main' / 'send.py'
    readers = sorted(str(f.relative_to(REPO_ROOT))
                     for f in (REPO_ROOT / 'src').rglob('*')
                     if f.is_file() and f != holder
                     and (_reads_switch(f) if f.suffix == '.py' else
                          f.suffix == '.sh' and re.search(rf'\$\{{?{SEND_SWITCH}', f.read_text())))
    run(f'send: only src/main/send.py reads {SEND_SWITCH}', not readers,
        None if not readers else
        f'{", ".join(readers)} reads the switch directly — import may_send (skip and pass) '
        f'or assert_may_send (raise) from src/main/send.py, so refusal cannot come to mean '
        f'two things by accident',
        check='effects.send_switch_read_once')

    # Python is type-checked by pyright — Pylance's own engine — against
    # pyrightconfig.json, the ONE declaration of the import roots that the editor, this
    # gate and any CLI all read. `standard` mode, matching what an editor reports today;
    # strict would demand ~4000 annotations to surface a tail that is currently all
    # false positives (a heterogeneous PROVIDERS dict, and a call dispatched by
    # inspect.signature, neither of which a type checker can follow).
    #
    # --pythonpath names the venv explicitly: without it pyright resolves imports from
    # whatever python is on PATH, and a run without the venv reports 25 errors that are
    # nothing but unresolved third-party packages.
    # The VENV the repo builds, ONE resolution for both halves: which pyright runs, and
    # which interpreter it analyses with. Looking pyright up on PATH alone made the check
    # depend on the reader's shell — it ran here only because that shell happens to put
    # the venv first, which is the same accident --pythonpath was added to avoid.
    venv = Path(os.environ.get('VENV', str(Path.home() / 'venvs' / 'general')))
    venv_pyright, venv_python = venv / 'bin' / 'pyright', venv / 'bin' / 'python'
    pyright = str(venv_pyright) if venv_pyright.exists() else shutil.which('pyright')
    py_ok, py_detail = True, None
    if pyright:
        cmd = [pyright, '--outputjson']
        if venv_python.exists():
            cmd += ['--pythonpath', str(venv_python)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = None
        if report is not None:
            diags = [d for d in report['generalDiagnostics'] if d['severity'] == 'error']
            py_ok = not diags
            py_detail = None if py_ok else '; '.join(
                f"{d['file'].replace(str(REPO_ROOT) + '/', '')}:"
                f"{d['range']['start']['line'] + 1} {d['message'].splitlines()[0][:60]}"
                for d in diags[:4])
    run('python: pyright reports nothing', py_ok, py_detail, check='python.pyright_clean')

    # Every printed plan line names where its step is implemented (#45). The plan is
    # the one place the whole program is listed, and it named no file at all: `validate`
    # alone had four candidates. The label is no longer asked to resolve — the line
    # carries the path, so a reader needs no rule about which namespace a label is in.
    plan = subprocess.run([str(REPO_ROOT / 'src' / 'main' / 'pipeline.sh'), 'run', '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout
    # ONE pattern, matched once. A filter and an extractor written separately can
    # disagree — these two did, on whether a non-space must precede the gap — and the
    # extractor was then indexing a None the filter had promised could not occur.
    named = r'\S\s{2,}((?:src|rsc)/\S+?)(?:\s|$)'
    step_lines = [(l, m) for l in plan.splitlines() if (m := re.search(named, l))]
    run('plan: every step line names an implementation', bool(step_lines),
        None if step_lines else 'no plan line carries a repo-relative path',
        law='G16', check='output.plan_lines_name_their_target')
    for line, match in step_lines:
        impl = match.group(1)
        exists = (REPO_ROOT / impl).is_file()
        run(f'plan: {impl}: the file the line names exists', exists,
            None if exists else f'`{line.strip()}` names {impl}, which is not a file',
            law='G16', check='output.plan_lines_name_their_target')
    # A step that is also a command prints AS that command — the line says it is typeable
    # by being typeable, rather than by a marker a legend would have to explain.
    for st in cli.steps():
        want = f'yoga {st["command"]} {st["subcommand"]}'
        run(f'plan: `{want}` is printed as the command it is', want in plan,
            None if want in plan else f'the plan names {st["command"]} without `yoga`, so '
            f'nothing distinguishes it from a label you cannot type',
            law='G16', check='output.plan_lines_name_their_target')

    # A file lives at the level of its subject (#41). Which tier imports a module is a
    # fact about the import graph, not a curated list — so this needs no vocabulary: a
    # module both tiers import belongs at src/, one only its own tier imports belongs in
    # that tier. src/ was holding validation_matrix by instinct and argparse_help one
    # level down, with the same cross-tier subject and the opposite placement.
    src_root = REPO_ROOT / 'src'
    modules = {p.stem: p for p in src_root.rglob('*.py')
               if '__pycache__' not in p.parts}
    importers: dict[str, set[str]] = {name: set() for name in modules}
    for path in modules.values():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        rel = path.relative_to(src_root)
        if rel.name == 'run.py' and rel.parts[0] == 'test':
            continue   # the gate imports what it CHECKS, which is not a dependency: it
                       # reaches into markdown_projection, cli and safari_utils to hold
                       # them to their contracts, and counting that as use would put
                       # every checked module at src/
        tier = 'test' if rel.parts[0] == 'test' else 'main'
        for node in ast.walk(tree):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                     [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for n in names:
                if n in importers and modules[n] != path:
                    importers[n].add(tier)
    for name, tiers in sorted(importers.items()):
        if not tiers:
            continue                      # imported by nothing: its own entrypoint
        rel = modules[name].relative_to(src_root)
        at_root = len(rel.parts) == 1
        shared = len(tiers) > 1
        ok = at_root == shared
        run(f'src: {rel}: lives at the level of its subject', ok,
            None if ok else
            (f'imported from {" and ".join(sorted(tiers))} but sits inside one tier — a '
             f'module both tiers import belongs at src/'
             if shared else
             f'imported only from the {tiers.pop()} tier but sits at src/, which is for '
             f'modules both tiers import'),
            check='structure.file_at_level_of_subject')

    # The declaration tree IS the API (#58): every command is a file or a directory
    # under rsc/cli/, every directory holds its own <command>.json plus one file per
    # subcommand, and nothing else lives there. Uniqueness and ordering need no check —
    # a directory cannot hold two entries of one name, and a listing has no out-of-order
    # state to be in (G4, by construction rather than by assertion).
    cli_root = REPO_ROOT / 'rsc' / 'cli'
    declared = {c['command'] for c in cmds}
    stray = sorted(p.name for p in cli_root.iterdir()
                   if p.name not in ('README.md', 'readings.md')
                   and not p.name.endswith('.schema.json')
                   and p.name not in declared)
    run('cli: rsc/cli/ holds declarations and nothing else', not stray,
        None if not stray else f'{", ".join(stray)} is neither a command nor a known document',
        law='G3', check='structure.cli_declaration_mirrors_the_api')
    # ONE shape, whether or not the command has verbs: a directory holding its own
    # declaration and one file per verb. Two shapes meant gaining a first verb converted
    # a file into a directory before the verb could be added — against the whole point,
    # which is that adding a verb is adding a file.
    for c in cmds:
        name = c['command']
        d = cli_root / name
        want = {f'{name}.json'} | {f'{v}.json' for v in cli.subcommands_of(name)}
        have = {f.name for f in d.glob('*.json')} if d.is_dir() else set()
        run(f'cli: {name}: its directory holds exactly its declarations', have == want,
            None if have == want else
            f'{d.relative_to(REPO_ROOT)} holds {sorted(have)}, declared {sorted(want)}',
            law='G3', check='structure.cli_declaration_mirrors_the_api')

    # Every declaration validates against the schema beside it. The schemas live in
    # rsc/cli/ and not under rsc/schema/, which is the DATA domain: this is the repo's
    # own interface, not corpus data. additionalProperties is false in all three, so a
    # field nobody reads cannot accumulate in a file nobody would notice it in.
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT4
    schemas = {k: json.loads((cli_root / f'{k}.schema.json').read_text())
               for k in ('command', 'subcommand', 'argument')}
    # the same resolution idiom validate.py uses — RefResolver is deprecated and warns,
    # and a warning on stderr would land in a committed report that must stay byte-stable
    registry = Registry().with_resource(
        'argument.schema.json',
        Resource.from_contents(schemas['argument'], default_specification=DRAFT4))
    for c in cmds:
        name = c['command']
        d = cli_root / name
        decl = [(d / f'{name}.json', 'command')] if d.is_dir() else [(cli_root / f'{name}.json', 'command')]
        if d.is_dir():
            decl += [(f, 'subcommand') for f in sorted(d.glob('*.json')) if f.stem != name]
        for path, kind in decl:
            validator = jsonschema.Draft4Validator(schemas[kind], registry=registry)
            errors = sorted(validator.iter_errors(json.loads(path.read_text())),
                            key=lambda e: list(e.path))
            run(f'cli: {path.relative_to(cli_root)}: validates as a {kind} declaration',
                not errors,
                None if not errors else
                f'{errors[0].message} at {"/".join(str(x) for x in errors[0].path) or "(root)"}',
                law='G3', check='structure.cli_declaration_validates')

    # Every typeable form is listed (#85). The bare noun is an alternative like any
    # other, so the forms number one per subcommand PLUS one — and the whole-table
    # listing must contain every form the per-command view shows, because the second is
    # derived from the first rather than rebuilt beside it.
    listing = cli_commands.render_synopsis(cmds)
    for c in cmds:
        forms = cli.command_forms(c['command'])
        expected = len([s for s in cli.subcommands_of(c['command'])]) + 1
        run(f'cli: {c["command"]}: every form is rendered (bare + one per subcommand)',
            len(forms) == expected,
            None if len(forms) == expected else
            f'{len(forms)} form(s) for {expected} expected — the bare noun is not '
            f'conditional in the grammar, so it cannot be conditional in the derivation',
            law='G3', check='cli.every_form_listed')
        # the RENDERED views, not the helper both are supposed to use: asking
        # command_forms whether the two agree cannot detect a view that adds a form of
        # its own, which is exactly the drift this replaces
        shown = [line.strip().replace('   (status)', '')
                 for line in cli.render_command_help(c).splitlines()
                 if line.startswith(f'  yoga {c["command"]}')]
        missing = [f for f in shown if f not in listing]
        run(f'cli: {c["command"]}: every form appears in the whole-table listing', not missing,
            None if not missing else
            f'{", ".join(missing)} is shown by `yoga commands {c["command"]}` but not by '
            f'`yoga commands` — two renderings of one table disagreeing',
            law='G3', check='cli.every_form_listed')

    # G21: an axis is an arg-type enumeration (`API|DOM`), and a flag named for one of
    # its values reads as a restriction to that value while behaving as an addition. Held
    # per command, over the declaration alone — the same table the surface is derived from.
    for cmd in sorted({r['command'] for r in cli.help_rows()}):
        rows = [r for r in cli.help_rows() if r['command'] == cmd]
        values = {v.strip().lower() for r in rows for v in (r['arg-type'] or '').split('|')
                  if v.strip() and '<' not in v}
        flags = [r['arg-name'] for r in rows if (r['arg-name'] or '').startswith('--')]
        clash = sorted(f for f in flags if f.lstrip('-').lower() in values)
        run(f'cli: {cmd}: no flag names a value of its own axis', not clash,
            None if not clash else
            f'{", ".join(clash)} names a value the command already enumerates — a reader '
            f'takes it for a restriction to that value, and the restriction it displaces '
            f'becomes unsayable', law='G21', check='cli.flag_not_axis_value')

    # G20, over a SYNTHETIC ~/.zshrc — the property is about the pure function, and the
    # gate must not read (much less converge) the machine's real shell config. The stale
    # marker below is the exact wording an earlier version wrote; it is the case that
    # actually escaped, so it is the case the check holds.
    stale = '# yoga tab-completion (refresh: ./yoga completions install-latest)'
    block = ['fpath=(~/x $fpath)', "alias yoga='~/x/yoga'", cli_completions.COMPLETION_END]
    synthetic = ['# unrelated', '', stale, *block, '', cli_completions.COMPLETION_MARKER, *block, '',
                 'autoload -Uz compinit', 'compinit']
    kept, _ = cli_completions.without_yoga_block(synthetic)
    # survivors counted by a LITERAL test-side predicate, never by the function under
    # test: asking cli.is_completion_marker what survived is asking the bug whether it
    # is present, and the answer under the old code was "converged" while the stale
    # block sat in the file
    left = [line for line in kept if line.startswith('# yoga tab-completion')]
    run('cli: completions: a marker with different advice is still the block',
        cli_completions.is_completion_marker(stale),
        None if cli_completions.is_completion_marker(stale) else
        f'{stale!r} is not recognised — identity is matching advice, so every block an '
        f'earlier version wrote is orphaned: install duplicates it, uninstall leaves it, '
        f'status calls a wired shell unwired', law='G20', check='cli.block_identity_stable')
    run('cli: completions: install converges on ONE block', not left,
        None if not left else f'{len(left)} block(s) survive removal: {left} — removing one '
        f'and writing one is not idempotence when two exist',
        law='G20', check='cli.block_convergence')
    run('cli: completions: the end marker does not open a block',
        not cli_completions.is_completion_marker(cli_completions.COMPLETION_END),
        None if not cli_completions.is_completion_marker(cli_completions.COMPLETION_END) else
        f'{cli_completions.COMPLETION_END!r} matches the start-marker test — a block would end where it '
        f'begins and removal would take the wrong extent',
        law='G20', check='cli.block_identity_stable')

    # The run pipeline's command-backed steps (the declared `step`). Each must
    # appear in `src/main/pipeline.sh --plan` as a line naming the COMMAND and its VERB — so the
    # plan speaks the command surface a reader would type, and a step can never invoke
    # a noun bare, which the bare-noun=status convention silently turns into a no-op.
    stepped = cli.steps()
    if not stepped:
        return
    plan = subprocess.run([str(REPO_ROOT / 'src' / 'main' / 'pipeline.sh'), '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout
    for s in stepped:
        cmd, sub = s['command'], s['subcommand']
        # the plan line is the step label then its non-path args (steps.sh): the label
        # must BE the command, and the verb must be among the args after it
        # `yoga ` prefixes a step that IS a command (#45), which is how the plan says the
        # line is typeable — so the invocation it must name is the command form
        ok = bool(re.search(rf'^\s*(yoga )?{re.escape(cmd)}\b.*\b{re.escape(sub)}\b', plan, re.M))
        run(f'cli: {cmd}: run step invokes `{cmd} {sub}` in plan', ok,
            None if ok else f'no `{cmd} … {sub}` line in `src/main/pipeline.sh --plan` — a bare '
            f'`{cmd}` step would silently be a status no-op', law='G10', check='cli.step_invokes_verb')


def check_grammar_laws(run, cited: dict) -> None:
    """The CLI's grammar (the law list in rsc/cli/README.md) and the checks that enforce
    it are held to each other, in both directions — so neither can drift into fiction.

    Forward: a citation must name a law the document states. A check citing G99 is
    enforcing something nobody wrote down.

    Backward: a law declaring itself `gated` must really be cited by a check that ran.
    This is the direction that rots silently — the prose list this replaced said nine
    things were held, and the law it did NOT mention (bare is status) was the one whose
    violation became four incidents (#29). A law with no check is now a failing check,
    not a discovery made during an outage.

    A law must declare a state at all: `gated`, `by construction` (the shape admits no
    violation — there is no second source to check), `unenforced (#N)` naming the issue that
    will hold it, or `doctrine` (stated deliberately, with no check). Silence is not a state,
    because silence is how an unheld law passes for a held one. `unenforced` must name an
    issue, so the gap is tracked rather than merely noted; `doctrine` need not, because it
    promises nothing — it is the state that keeps a law from obliging a check that would
    need a curated vocabulary invented just to make it codable.

    A law may declare a parent corpus law (`from L5`) — it is that law applied to the
    surface. The parent must exist in rsc/CALCULUS.md (calculus_terms is the authority),
    so the grammar cites the principle instead of paraphrasing it.

    Committed files only (the document, and the citations of this same run): code tier."""
    try:
        laws = cli.grammar_laws()
    except Exception as e:
        run('grammar: laws parse: rsc/cli/README.md', False, str(e), check='grammar.laws_parse')
        return
    run('grammar: laws parse: rsc/cli/README.md', bool(laws),
        None if laws else 'no `- **G<n> — …**` law bullets found', check='grammar.laws_parse')
    if not laws:
        return

    # TWO vocabularies, one citation field (#50): a check enforces either a surface law
    # from the grammar or a corpus law from rsc/CALCULUS.md, and a citation is stated if
    # either document states it.
    corpus = cli.calculus_laws()
    orphans = sorted(set(cited) - set(laws) - set(corpus))
    run('grammar: every citation names a stated law', not orphans,
        f'cited by a check but stated in neither the grammar nor the calculus: '
        f'{", ".join(orphans)}' if orphans else None, check='grammar.citation_is_stated')

    # The same three questions the G-laws answer, asked of the laws that govern the DATA
    # — which is where the stakes are higher and the gap was identical: the Laws section
    # promised "each law names its current enforcement" in prose, and nothing read it.
    run('calculus: laws parse: rsc/CALCULUS.md', bool(corpus),
        None if corpus else 'no `- **L<n> — …**` law bullets found', check='calculus.laws_parse')
    stateless_l = sorted(l for l, law in corpus.items() if law['state'] not in cli.LAW_STATES)
    run('calculus: every law declares a state', not stateless_l,
        f'no `gated` / `by construction` / `unenforced (#N)` / `doctrine`: '
        f'{", ".join(stateless_l)}' if stateless_l else None, check='calculus.state_declared')
    uncited_l = sorted(l for l, law in corpus.items()
                       if law['state'] == 'gated' and l not in cited)
    run('calculus: every gated law is cited by a check that ran', not uncited_l,
        f'declares `gated` but no check cites it: {", ".join(uncited_l)}'
        if uncited_l else None, check='calculus.gated_is_cited')
    issueless_l = sorted(l for l, law in corpus.items()
                         if law['state'] == 'unenforced' and not law['issues'])
    run('calculus: every unenforced law names the issue that will hold it', not issueless_l,
        f'declares `unenforced` with no #issue: {", ".join(issueless_l)}'
        if issueless_l else None, check='calculus.unenforced_names_issue')

    stateless = sorted(g for g, law in laws.items() if law['state'] not in cli.LAW_STATES)
    run('grammar: every law declares a state', not stateless,
        f'no `gated`/`by construction`/`unenforced`/`doctrine` marker: {", ".join(stateless)}'
        if stateless else None, check='grammar.state_declared')

    # AGGREGATE, not one check per law: nineteen lines saying "G7 is cited" carry the same
    # fact as one saying "7/7 gated laws are cited", and the failing ids belong in a detail
    # line rather than in nineteen labels. A report is read by someone deciding whether to
    # look closer; per-law rows make that decision harder, not easier.
    ids = lambda gs: ', '.join(sorted(gs, key=lambda g: int(g[1:])))

    gated = {g for g, law in laws.items() if law['state'] == 'gated'}
    uncited = gated - set(cited)
    run(f'grammar: every gated law is cited by a check ({len(gated) - len(uncited)}/{len(gated)})',
        not uncited,
        f'declares `gated` but no check cites it: {ids(uncited)}' if uncited else None, check='grammar.gated_is_cited')

    unenforced = {g for g, law in laws.items() if law['state'] == 'unenforced'}
    issueless = {g for g in unenforced if not laws[g]['issues']}
    run(f'grammar: every unenforced law names its issue ({len(unenforced) - len(issueless)}/{len(unenforced)})',
        not issueless,
        f'declares `unenforced` with no #issue: {ids(issueless)}' if issueless else None, check='grammar.unenforced_names_issue')

    # a cited law is held, whatever it claims: the claim is what is wrong
    miscited = {g for g, law in laws.items()
                if law['state'] in ('unenforced', 'doctrine') and g in cited}
    run('grammar: no unenforced or doctrine law is cited', not miscited,
        '; '.join(f'{g} declares `{laws[g]["state"]}` but is cited by: '
                  f'{", ".join(cited[g])}' for g in sorted(miscited)) if miscited else None, check='grammar.unenforced_not_cited')

    # A law citing a parent corpus law must cite one that exists. The bridge is the point:
    # G3 IS L5 applied to the surface, so rsc/CALCULUS.md stays the authority for the
    # principle and the grammar paraphrases nothing. A dangling `from L99` would put the
    # paraphrase back, silently.
    vocab = cli.calculus_terms()
    bridged = {g: laws[g]['from'] for g in laws if laws[g]['from']}
    dangling = {g: parent for g, parent in bridged.items() if parent not in vocab}
    run(f'grammar: every cited corpus law is defined ({len(bridged) - len(dangling)}/{len(bridged)})',
        not dangling,
        '; '.join(f'{g}: `from {parent}` names no law in rsc/CALCULUS.md'
                  for g, parent in sorted(dangling.items())) if dangling else None, check='grammar.parent_law_defined')

    # The enforcement map, printed rather than maintained as prose: this IS the
    # "held honest by the gates" list the README used to carry by hand.
    by_state: dict[str, list[str]] = {}
    for gid, law in laws.items():
        by_state.setdefault(str(law['state']), []).append(gid)
    summary = '; '.join(f'{st}: {len(g)}' for st, g in sorted(by_state.items()))
    run(f'grammar: {len(laws)} laws — {summary}', True, check='grammar.enforcement_map')


_VERSIONED_SCHEMA_DIAGNOSTICS_SKIP = frozenset({'naming.root_schema_title_matches_filename'})

def check_versioned_schema_diagnostics(run):
    all_diagnostics = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
    schema_skips    = {s: p.diagnostic_skip for p in PIPELINES.values() for s in p.schemas}

    schema_dirs = _schema_families()
    for schema_name in sorted(set(schema_skips) | set(schema_dirs)):
        skip        = _VERSIONED_SCHEMA_DIAGNOSTICS_SKIP | schema_skips.get(schema_name, frozenset())
        schema_dir  = schema_dirs.get(schema_name, SCHEMA_DIR.get(schema_name))
        if schema_dir and schema_dir.parent.name.startswith('_'):
            # _reference/ families are VERBATIM upstream snapshots (e.g. the MCP
            # protocol spec): house style diagnostics do not apply — repairing
            # upstream text to satisfy them would falsify the snapshot. Validity
            # ($schema, parseability) is still checked by check_schema_validity.
            continue
        versions    = _sorted_versions(schema_dir) if schema_dir else []
        diagnostics = [s for s in all_diagnostics if s.stem not in skip]
        if not versions:
            run(f'{schema_name}: no versions', False,
                f'{schema_dir.relative_to(REPO_ROOT) if schema_dir else schema_name} has no v*.json files', check='schema.has_versions')
            continue
        jobs = [(script, version) for version in versions for script in diagnostics]
        for (script, version), (passed, output) in zip(jobs, _call_many(jobs)):
            run(f'{schema_name}: {script.stem}: {version.stem}', passed,
                _diag_detail(output) if not passed else None, check=script.stem)


def check_schema_join(run):
    join = RSC_SCHEMA / 'model_join.csv'
    if not join.exists():
        run('schema model_join.csv exists', False, check='model.join_exists')
        return
    fails: list[str] = []
    # One grammar, one base: every cell is a versioned family dir relative to
    # rsc/schema ('chat-exports/conversations#…', '_reference/mcp#…'), resolved
    # against its latest version. No per-column tribal knowledge to resolve a cell.
    _check_csv_pointers(join,
                        ('conversations_path', 'session_path', 'apiConversation_path', 'mcp_path'),
                        {c: RSC_SCHEMA for c in ('conversations_path', 'session_path', 'apiConversation_path', 'mcp_path')},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None, check='model.join_pointers_valid')


def check_model_join_versions(run):
    """The versioned columns must use the de-versioned grammar — a family dir per
    cell ('<pipeline>/<family>#/definitions/…'), never a vN.json pin. The old pinned
    grammar churned every session/conv/api cell on each mint and its bare filenames
    defeated search: a session row spelling 'v7.json#…' contains neither 'session'
    nor its pipeline, which is how a 2026-07-10 grep for session references found
    nothing while 37 rows sat there. check_schema_join resolves family dirs against
    their latest version, so currency is enforced by resolution, not by rewriting."""
    join = RSC_SCHEMA / 'model_join.csv'
    if not join.exists():
        return
    pins: list[str] = []
    with join.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in ('conversations_path', 'session_path', 'apiConversation_path', 'mcp_path'):
                file_part = (row.get(col) or '').strip().partition('#')[0]
                if re.search(r'v\d+\.json$', file_part):
                    pins.append(f'row {i} {col}: {file_part}')
    run('model_join: de-versioned pointer grammar (family dirs, no vN.json pins)',
        not pins,
        '\n    '.join(pins[:5]) if pins else None, check='model.join_family_grammar')


def _deref(node, root, _seen=None):
    """Follow $ref chains ('#/definitions/X') within one schema document."""
    seen = _seen or set()
    while isinstance(node, dict) and '$ref' in node and node['$ref'] not in seen:
        seen.add(node['$ref'])
        target: Any = root
        for tok in node['$ref'].lstrip('#/').split('/'):
            target = target.get(tok) if isinstance(target, dict) else None
        if target is None:
            return node
        node = target
    return node


def _admits_instance_pointer(schema, pointer: str) -> bool:
    """Does the schema's structure admit this INSTANCE pointer ('#/0/account/uuid')?
    An integer token steps into items, a key token into properties or
    additionalProperties; $ref is followed and oneOf/anyOf/allOf branches are
    searched — any branch admitting the remainder admits it."""
    def admits(node, tokens) -> bool:
        node = _deref(node, schema)
        if not tokens:
            return True
        if not isinstance(node, dict):
            return False
        t, rest = tokens[0], tokens[1:]
        if t.isdigit():
            items = node.get('items')
            if isinstance(items, dict) and admits(items, rest):
                return True
            if isinstance(items, list) and int(t) < len(items) and admits(items[int(t)], rest):
                return True
        else:
            props = node.get('properties', {})
            if t in props and admits(props[t], rest):
                return True
            extra = node.get('additionalProperties')
            if isinstance(extra, dict) and admits(extra, rest):
                return True
        return any(admits(b, tokens)
                   for comb in ('oneOf', 'anyOf', 'allOf') for b in node.get(comb, []))
    return admits(schema, pointer.lstrip('#/').split('/'))


def check_model_occurrences(run):
    """model.json's occurrence paths obey the de-versioned family-dir grammar
    model_join.csv earned (check_model_join_versions) and RESOLVE (issue #19):
    each occurrences key is '<pipeline>/<family>' — the pinned grammar was drift
    already in progress, v15 pins under a v17 corpus, and unlike model_join
    nothing validated them — and each instance pointer must resolve against the
    family's LATEST version by walking the schema's structure. A mint that
    renames a documented field fails here, the model_join review prompt; one
    that keeps it costs nothing."""
    doc = json.loads((RSC_SCHEMA / 'model.json').read_text()).get('default', {})
    fams = model_curation.latest_versions()
    pins, bad = [], []
    for tname, entry in doc.items():
        for key, pointers in entry.get('occurrences', {}).items():
            if re.search(r'v\d+\.json$', key.partition('#')[0]):
                pins.append(f'{tname}: {key}')
                continue
            latest = fams.get(key)
            if latest is None:
                bad.append(f'{tname}: no such family dir: {key}')
                continue
            schema = json.loads(latest.read_text())
            for ptr in pointers:
                if not _admits_instance_pointer(schema, ptr):
                    bad.append(f'{tname}: {key} {ptr} does not resolve against {latest.name}')
    run('model: occurrences use family-dir grammar (no vN.json pins)', not pins,
        '\n    '.join(pins[:5]) if pins else None, check='model.occurrence_family_grammar')
    run('model: occurrence pointers resolve against latest versions', not bad,
        '\n    '.join(bad[:5]) if bad else None, check='model.occurrence_pointers_resolve')
    # Completeness (issue #19 follow-up, the foolproof-index fix, user + reading-room):
    # grounds() needs one family to match, so a type can be documented with a
    # dressing missing and still ground — model.json would then answer "where does
    # this type occur" incompletely, the non-foolproof grep the account-uuid thread
    # exposed. Every DATA family a grounding edge asserts must be an occurrence, so
    # the index is the complete, reliable answer the four-dressing schemas cannot be.
    gaps = model_curation.coverage_gaps()
    run('model: documented types occur completely (occurrences cover their edges\' data families)',
        not gaps,
        '\n    '.join(f'{n}: grounding edge asserts {", ".join(f)} — not in occurrences'
                      for n, f in list(gaps.items())[:5]) if gaps else None, check='model.occurrences_cover_edges')


def check_model_obligations(run) -> None:
    """The blocking half of model.json's curate discipline (issue #19; the PR
    #36 review, reading-room, directed by the user), BOTH directions of the one
    grounding relation (model_curation.grounds — by containing-definition name,
    or by property trail for inline field types whose semantic name no schema
    definition can supply, e.g. UserUUID's account uuid):

    - edge→doc: every model_join edge whose relationship kind asserts ONE
      shared type (identical, snake_cased) is grounded by a documented entry or
      covered by a rejection in rsc/schema/model_rejected.txt. One check per
      distinct shared type, so a regression names what it broke.
    - doc→edge: every documented type is grounded by >=1 obligating edge — no
      orphan documentation (the review's gap: UserUUID passed the
      one-directional gate on no recorded basis).

    Together: model.json documents exactly the shared types model_join asserts,
    minus rejections. GATES (schema tier): an edge is a human-asserted
    identity, and an undocumented asserted identity — or a documented type no
    edge asserts — is a defect, not a queue. The raw name scan stays `yoga
    model`'s leisurely advisory pointed at model_join, since a name_collision
    is a false friend no scan can tell from a shared type."""
    queue = model_curation.edge_queue()
    for names, rows in sorted(model_curation.shared_types().items(),
                              key=lambda kv: sorted(kv[0])):
        pending = queue.get(names)
        run(f'model: shared type disposed: {"/".join(sorted(names))}', not pending,
            None if not pending else
            f'model_join row(s) {", ".join(map(str, pending))} assert one shared type: '
            'document it in rsc/schema/model.json or reject it in rsc/schema/model_rejected.txt', check='model.shared_type_disposed')
    orphans = set(model_curation.orphan_entries())
    for name in sorted(model_curation.documented()):
        run(f'model: documented type grounded: {name}', name not in orphans,
            None if name not in orphans else
            'no model_join edge asserts this type: curate the asserting edge '
            '(relationship identical | snake_cased), or retire the entry', check='model.documented_type_grounded')


def check_mcp_schema(run):
    """The LATEST _reference/mcp/vN.json must match the upstream schema at the raw
    URL in its description. Upstream drift is answered by MINTING the next version
    beside the old one (the snapshot's history is data), never by updating in place."""
    import hashlib, urllib.request
    mcp_dir  = RSC_SCHEMA / '_reference' / 'mcp'
    versions = _sorted_versions(mcp_dir) if mcp_dir.is_dir() else []
    if not versions:
        run('mcp schema: _reference/mcp/ has versions', False, check='mcp.has_versions')
        return
    latest = versions[-1]
    rel    = latest.relative_to(REPO_ROOT)
    desc = json.loads(latest.read_text()).get('description', '')
    m_url  = re.search(r'(https://raw\.githubusercontent\.com/\S+)', desc)
    m_hash = re.search(r'upstream SHA256:\s*([0-9a-f]{64})', desc)
    if not m_url or not m_hash:
        run('mcp schema: description has raw URL and upstream SHA256', False,
            f'Add raw URL and "upstream SHA256: <hex>" to the description field in {rel}', check='mcp.description_pins_upstream')
        return
    raw_url     = m_url.group(1)
    stored_hash = m_hash.group(1)
    # This is the gate's only SEND — an outward call over the network, and the one effect
    # with no scratch form (#29). It is refusable like every other send here, through the
    # one reading of the switch in src/main/send.py: YOGA_NO_SEND=1 skips it.
    #
    # An unreachable upstream is NOT a failure. It used to raise its own check, so an
    # offline run failed three ways at once — the expected mcp.up_to_date never ran, an
    # unexpected mcp.upstream_reachable did, and the schema tier lost a point — which meant
    # no commit was possible without the internet. The label is CONSTANT and the result
    # passes when the send did not happen, so the committed report is byte-identical on a
    # machine that cannot reach github (the shellcheck and pyright precedent, and L2).
    drift = None
    if may_send():
        try:
            with urllib.request.urlopen(raw_url, timeout=15) as resp:
                live_hash = hashlib.sha256(resp.read()).hexdigest()
            if stored_hash != live_hash:
                drift = (f'upstream changed — mint _reference/mcp/v{len(versions) + 1}.json '
                         f'from {raw_url} (convert to draft-04, set its description commit URL '
                         f'+ SHA256, narrate in the family CHANGELOG); {rel} stays as history')
        except Exception:
            pass          # unreached: the currency of the copy is simply unknown this run
    run(f'mcp schema: {latest.stem} up to date', drift is None, drift, check='mcp.up_to_date')



def check_xref(run):
    # `check` is the writing verb (bare `xref` is read-only status now); the gate
    # regenerates the committed table and compares, so it must call the verb.
    _, output = _call(SRC / 'test' / 'xref.py', 'check')
    summary = output.splitlines()[-1] if output else ''
    m = re.search(r'(\d+ missing-file, \d+ bad-pointer, \d+ self-only, \d+ unreferenced)', summary)
    actual = m.group(1) if m else ''
    m_bad  = re.search(r'(\d+) bad-pointer', actual)
    bad    = int(m_bad.group(1)) if m_bad else 0

    score_file = RSC / 'test' / 'xref_expected_score'
    expected   = score_file.read_text().strip()

    run('xref: no bad pointers', bad == 0, summary if bad else None, check='xref.no_bad_pointers')
    run(f'xref: {actual}', actual == expected,
        f'expected: {expected}  →  consider updating {score_file.relative_to(REPO_ROOT)}'
        if actual != expected else None, law='L9', check='xref.score_matches_expectation')
    # L9 is cited ONLY from here, never from mcp.up_to_date: that run() sits inside a
    # network fetch, and when the fetch fails control leaves for the except branch and
    # the citation never happens. A law must not look unenforced because a request timed
    # out, so its citation lives on a check that cannot be skipped.


def check_capture_monotone(run) -> None:
    """L4 where a browser capture BECOMES the record. Gemini has no API, so its DOM
    capture is the only copy, and the page renders just its last few human turns until
    a walk reaches the top — so a walk that ends up shorter than what is already on disk
    failed partway. Held over a temporary tree, never the machine's own captures: the
    property is about the write, and the write must be exercised to test it.

    The growth case is checked beside the refusal, because a guard that also blocks the
    normal path would pass a refusal-only test while breaking every real capture."""
    import contextlib
    import shutil
    import tempfile
    import time
    sys.path.insert(0, str(REPO_ROOT / 'src' / 'main' / 'browser-captures'))
    import safari_utils
    real_downloads = safari_utils.DOWNLOADS

    def turns(n):
        return ''.join(f'## Human ({i})\nq{i}\n\n## Gemini ({i})\na{i}\n\n' for i in range(1, n))

    try:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dl = base / 'downloads'
            dest = base / 'input' / 'gemini' / 'chat' / 'browser-DOM' / 'abc123'
            logs = base / 'logs'
            for d in (dl, dest, logs):
                d.mkdir(parents=True)
            safari_utils.DOWNLOADS = dl

            long_md = turns(10)
            (dest / 'standing.md').write_text(long_md)
            (dl / 'standing.md').write_text(turns(3))
            after = time.time() - 1
            # the guard reports loudly, as it must in a real capture; here the verdicts
            # below are the report, so its output does not belong in the check log
            with contextlib.redirect_stdout(io.StringIO()):
                moved = safari_utils.collect_md_and_log(after, dest, logs)
            kept = (dest / 'standing.md').read_text()
            run('capture: a shorter walk never replaces a longer record', kept == long_md,
                None if kept == long_md else
                f'the record was replaced by a walk holding {len(turn_seq(kept))} turns',
                law='L4', check='capture.monotone_record')
            run('capture: a refused walk reports no markdown', moved == [],
                None if moved == [] else f'returned {moved} — the caller would file it as a '
                f'successful capture', law='L4', check='capture.monotone_record')
            evidence = (logs / 'abc123.short.md')
            run('capture: the refused walk is kept as evidence', evidence.exists(),
                None if evidence.exists() else 'the short capture was discarded, so the '
                'reason for the refusal cannot be inspected', law='L4', check='capture.monotone_record')

            shutil.rmtree(dl)
            dl.mkdir()
            (dl / 'grown.md').write_text(turns(20))
            after = time.time() - 1
            with contextlib.redirect_stdout(io.StringIO()):
                moved = safari_utils.collect_md_and_log(after, dest, logs)
            grew = moved == ['grown.md'] and not (dest / 'standing.md').exists()
            run('capture: a longer walk still supersedes', grew,
                None if grew else f'moved={moved}, dir={sorted(f.name for f in dest.glob("*.md"))} '
                f'— the guard is blocking the normal path', law='L4', check='capture.monotone_record')
    finally:
        safari_utils.DOWNLOADS = real_downloads


def check_accumulate_contract(run) -> None:
    """The shared accumulate operation (src/main/chat-exports/accumulate.py) obeys
    the contract issue #22 unified it to and rsc/CALCULUS.md states: deposit iff
    the content differs from the NEAREST EARLIER deposit, so the store records a
    trajectory, not a set. The design turns on cases a byte-set would get wrong —
    above all that a genuine A→B→A return deposits while a re-stamp of an unchanged
    reading does not (the 196-twin bug). CALCULUS.md holds the sentence; this holds
    it to account. Deterministic, tempdir-only, committed code — code tier: the
    guarantee is guarded in the repo, not only in a PR's prose (issue #22)."""
    import tempfile
    import shutil
    d = Path(tempfile.mkdtemp())
    try:
        def acc(stamp, content):
            return _accumulate.accumulate(d, stamp, content,
                                          suffix='.md', exclude={'index.md'})
        # A→B→A: every leg is a trajectory event, so all three deposit — the
        # return is exactly what a folder-wide content set would erase.
        cases = [
            ('A deposits',              acc('2026-01-01T000000Z', 'A') == 'deposited'),
            ('B deposits',              acc('2026-01-02T000000Z', 'B') == 'deposited'),
            ('A→B→A return deposits',   acc('2026-01-03T000000Z', 'A') == 'deposited'),
            # a re-stamp of an unchanged reading (A again, nothing between) is not
            # an event — suppressed; this is the re-stamp bug's fix.
            ('re-stamp suppressed',     acc('2026-01-04T000000Z', 'A') == 'unchanged'),
            # re-run of an existing stamp with identical content is idempotent.
            ('idempotent re-run',       acc('2026-01-03T000000Z', 'A') == 'unchanged'),
            # same stamp, different content: conflict, and nothing is written.
            ('same-stamp mismatch → conflict',
                                        acc('2026-01-03T000000Z', 'Z') == 'conflict'),
            ('conflict leaves deposit immutable',
                (d / '2026-01-03T000000Z.md').read_text() == 'A'),
        ]
        # a non-deposit sibling never enters the comparison.
        (d / 'index.md').write_text('B')
        cases.append(('non-deposit sibling excluded',
                      acc('2026-01-06T000000Z', 'A') == 'unchanged'))
        failed = [name for name, ok in cases if not ok]
        run('accumulate: the CALCULUS trajectory contract (#22)',
            not failed, 'cases failed: ' + '; '.join(failed) if failed else None, law='L1 L6', check='accumulate.trajectory_contract')
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true')
    args = ap.parse_args()

    results = []
    # The report splits by DETERMINISM, mirroring the tiers: code+schema output is
    # identical on any clone and becomes the COMMITTED rsc/test/run.log; the
    # data tier describes THIS MACHINE's data (uuids, batch names, home-dir-derived
    # paths) and must never enter a committed artifact — it goes to the terminal and
    # to tmp/logs/test/run.log (machine-facing, like the serve daemon's log).
    committed_buffer = io.StringIO()   # code + schema tiers
    machine_buffer   = io.StringIO()   # data tier
    cited_laws: dict[str, list[str]] = {}   # grammar law id -> the labels citing it
    check_types: list[str | None] = []     # per result: which TYPE of check it is an instance of

    def run(label, passed, detail=None, law=None, check=None):
        # `law` cites the law this fact enforces — a CLI grammar law from
        # rsc/cli/README.md (G<n>) or a corpus law from rsc/CALCULUS.md (L<n>), two
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
        # Data-tier facts are advisory (they never veto — see the exit) and
        # carry the WARN sigil ⚠, never the gating ✗ (user specification,
        # 2026-07-12: a "final summary" must not LOOK failed where nothing
        # blocks).
        mark = '✓' if passed else ('⚠' if current_tier[0] == 'data' else '✗')
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

    def run_section(fn, label=None, tier='schema'):
        name = label or fn.__name__
        sys.stdout = machine_buffer
        if tier != current_tier[0]:
            current_tier[0] = tier
            print(f'\n════ {tier} tier {"═" * (68 - len(tier))}')
        print(f'\n── {name} {"─" * (74 - len(name))}')
        before = len(results)
        ret = fn(run)
        n = len(results) - before
        sections.extend([name] * n)
        tiers.extend([tier] * n)
        return ret

    data_skipped = {n for n, p in PIPELINES.items() if not _has_local_data(p)}

    def _data_skip_note(pipeline):
        print(f'  – skipped: no local data '
              f'({pipeline.input.relative_to(REPO_ROOT)}/{pipeline.input_glob} absent, '
              f'{pipeline.cache_output.relative_to(REPO_ROOT)}/ empty)')

    try:
        run_section(check_required_files, tier='code')
        run_section(check_xref, tier='code')
        run_section(check_cli_surface, tier='code')
        run_section(check_cache_io, tier='code')
        run_section(check_accumulate_contract, tier='code')
        run_section(check_capture_monotone, tier='code')
        # LAST of the code tier, because it reads the citation ledger: a law is held by
        # whichever check cites it, and until every section has run the ledger is partial.
        # Registered after check_cli_surface alone, it saw the G-citations (all raised
        # there) and none of the L-citations, which are raised by the sections that
        # enforce the corpus laws — so three gated laws looked uncited.
        run_section(lambda run, _c=cited_laws: check_grammar_laws(run, _c),
                    label='check_grammar_laws', tier='code')

        run_section(check_root_schema_diagnostics, tier='schema')

        run_section(check_schema_validity, tier='schema')
        run_section(check_schema_changelogs, tier='schema')

        run_section(check_versioned_schema_diagnostics, tier='schema')
        run_section(check_schema_join, tier='schema')
        run_section(check_model_join_versions, tier='schema')
        run_section(check_model_occurrences, tier='schema')
        run_section(check_model_obligations, tier='schema')
        run_section(check_mcp_schema, tier='schema')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline, _fix=fix:
                            check_pipeline_validation_outputs(run, _fix, n, p)
                            if n not in data_skipped else _data_skip_note(p),
                        label=f'check_{_slug}_validation_outputs', tier='data')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline, _fix=fix:
                            check_pipeline_coverage(run, _fix, p)
                            if n not in data_skipped else _data_skip_note(p),
                        label=f'check_{_slug}_coverage', tier='data')

        for _name, _pipeline in PIPELINES.items():
            _slug = _name.replace('-', '_')
            run_section(lambda run, n=_name, p=_pipeline, _fix=fix:
                            check_pipeline_frontier(run, _fix, n, p)
                            if n not in data_skipped else _data_skip_note(p),
                        label=f'check_{_slug}_frontier', tier='data')

        run_section(check_cross_sources, tier='data')
        run_section(lambda run, _fix=fix: check_index_curation(run, _fix),
                    label='check_index_curation', tier='data')
    finally:
        sys.stdout = sys.__stdout__

    failures = [(n, d) for n, p, d in results if not p]

    # Score check — per-tier subtotals. code and schema are deterministic on any clone and
    # are compared against the committed expected score (whose first line is their combined
    # total, matching the log's head line); data is machine-local — its subtotal is reported
    # (and its failures block) but never recorded.
    tier_counts: dict[str, list[int]] = {}
    for i, (_, p, _) in enumerate(results):
        c = tier_counts.setdefault(tiers[i], [0, 0])
        c[0] += 1 if p else 0
        c[1] += 1

    det_got = sum(tier_counts.get(t, [0, 0])[0] for t in ('code', 'schema'))
    det_tot = sum(tier_counts.get(t, [0, 0])[1] for t in ('code', 'schema'))
    det     = f'{det_got}/{det_tot}'

    # The committed expectation is the SET OF CHECK TYPES, not a count of invocations.
    # A count moved whenever a schema version, a command or a conversation was added — work
    # that adds no check — so the file was updated reflexively, which is how the failure it
    # exists to catch (a check that silently stopped running) would have been waved through.
    # A type leaving the set is that failure, and nothing else produces it.
    checks_file = RSC / 'test' / 'run_expected_checks'
    expected_types = {l.strip() for l in checks_file.read_text().splitlines()
                      if l.strip() and not l.startswith('#')} if checks_file.exists() else set()
    seen_types = {t for t, tier in zip(check_types, tiers)
                  if t and tier in ('code', 'schema')}

    score_rows: list[tuple] = []

    ok = det_got == det_tot
    score_rows.append((f'checks[code+schema]: {len(seen_types)} types, {det} invocations passing',
                       ok, 'Fix failures in the code and schema tiers first' if not ok else None))

    gone = sorted(expected_types - seen_types)
    score_rows.append(('checks: every expected check ran', not gone,
                       f'expected but never ran — deleted, renamed, or skipped: {", ".join(gone)}'
                       if gone else None))

    added = sorted(seen_types - expected_types)
    score_rows.append(('checks: every check that ran is expected', not added,
                       f'new: {", ".join(added)} — add to '
                       f'{checks_file.relative_to(REPO_ROOT)} deliberately'
                       if added else None))

    for t in ('code', 'schema'):
        got, tot = tier_counts.get(t, [0, 0])
        n_types = len({ty for ty, tier in zip(check_types, tiers) if ty and tier == t})
        score_rows.append((f'checks[{t}]: {n_types} types, {got}/{tot} invocations passing',
                           got == tot, 'Fix failures in this tier first' if got != tot else None))

    got, tot = tier_counts.get('data', [0, 0])
    skipped_note = f' (skipped: {", ".join(sorted(data_skipped))})' if data_skipped else ''
    if tot == 0:
        score_rows.append((f'score[data]: skipped — no local data{skipped_note}', True, None))
    else:
        score_rows.append((f'score[data]: {got}/{tot}; machine-local, not recorded{skipped_note}',
                           got == tot, None))

    for label, ok, detail in score_rows:
        results.append((label, ok, detail))
        check_types.append(label.split(':')[0])   # keeps the parallel lists in step
        sections.append('check_score')
        # score[data] carries the data tier's advisory nature: it is reported but,
        # like the tier it summarises, must not gate commits (see exit below).
        tiers.append('data' if label.startswith('score[data]') else 'score')
        if not ok:
            failures.append((label, detail))

    # ── report rendering ─────────────────────────────────────────────────────
    # Two renderings of one result set, split by determinism exactly as the tiers
    # are: the COMMITTED report (code+schema and their scores — byte-identical on
    # any clone; this script writes it to rsc/test/run.log itself) and the
    # FULL report (adds the machine-local data tier — printed to stdout and written
    # to tmp/logs/test/run.log, run-facing like the serve daemon's log).

    def _in_committed(i: int) -> bool:
        return tiers[i] != 'data' and not results[i][0].startswith('score[data]')

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
                _d = SCHEMA_DIR.get(parts[0])
                schema_path = (_d if _d is not None else RSC_SCHEMA / parts[0]) / f'{parts[2]}.json'
                repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                if repair.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif diagnostic.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif detail:
                    _add(detail, name, prose=True)   # a detail is advice, not a command
            elif len(parts) == 2 and re.match(r'[a-z_]+\.[a-z_]+', parts[0]):
                diag, schema_path = parts[0], RSC_SCHEMA / parts[1]
                repair     = SRC / 'test' / 'repairs'     / f'{diag}.py'
                diagnostic = SRC / 'test' / 'diagnostics' / f'{diag}.py'
                if repair.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {repair.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif diagnostic.exists() and schema_path.exists():
                    _add(f'src/run_python_script.sh {diagnostic.relative_to(REPO_ROOT)} {schema_path.relative_to(REPO_ROOT)}', name)
                elif detail:
                    _add(detail, name, prose=True)

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

    def _is_advisory(i: int) -> bool:
        return tiers[i] == 'data' or results[i][0].startswith('score[data]')

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

        Every invocation stays in the machine-local log (tmp/logs/test/run.log),
        where evidence belongs; this is the file a human reads in a diff."""
        out, seen_section = io.StringIO(), None
        order: dict[tuple, list] = {}
        for i in idxs:
            order.setdefault((sections[i], check_types[i] or results[i][0]), []).append(i)
        for (section, ctype), members in order.items():
            if section != seen_section:
                seen_section = section
                out.write(f'\n── {section} {"─" * max(0, 74 - len(section))}\n')
            failed = [i for i in members if not results[i][1]]
            mark = '✓' if not failed else ('⚠' if all(_is_advisory(i) for i in failed) else '✗')
            n = len(members)
            count = f'  ({n - len(failed)}/{n})' if n > 1 else ''
            out.write(f'  {mark} {ctype}{count}\n')
            for i in failed:                      # only the failures are named
                label, _, detail = results[i]
                out.write(f'      {label}\n')
                if detail:
                    out.write(f'          {detail}\n')
        return out.getvalue()

    def _render(committed_only: bool, include_body: bool = True):
        """Render one report variant; returns (text, runnable fix lines).
        include_body=False drops the per-check ✓/✗ body, leaving header + tail —
        the terminal variant, which points at the log for the per-check detail.
        The tail splits by GATE EFFECT (user specification, 2026-07-12): a
        penultimate WARN block carries the machine-local advisory facts (the
        data tier, score[data] included — they never veto anything), and the
        FINAL word states what the hook actually does — FAIL with the gating
        sections and their remedies, or an explicit PASS."""
        idxs       = [i for i in range(len(results)) if not committed_only or _in_committed(i)]
        fail_idx   = [i for i in idxs if not results[i][1]]
        warn_idx   = [i for i in fail_idx if _is_advisory(i)]
        gate_idx   = [i for i in fail_idx if not _is_advisory(i)]
        warn_sections = list(dict.fromkeys(sections[i] for i in warn_idx))
        gate_sections = list(dict.fromkeys(sections[i] for i in gate_idx))
        out = io.StringIO()

        data_got, data_tot = tier_counts.get('data', [0, 0])
        data_note = ('data: machine-local' if committed_only else
                     'data: skipped' if data_tot == 0 else f'data: {data_got}/{data_tot}')
        if fail_idx:
            out.write(f'`src/test/run.py`: {det} ({data_note}; '
                      f'{len(gate_sections)} gating / {len(warn_sections)} advisory section(s) failing)\n')
        else:
            out.write(f'run.py: {det} ({data_note})\n')

        out.write('\n')
        if include_body:
            out.write(_by_type(idxs))
            if not committed_only:
                out.write(machine_buffer.getvalue())
        else:
            out.write('  full per-check report → tmp/logs/test/run.log\n')

        name = 'check_score'
        out.write(f'\n── {name} {"─" * (74 - len(name))}\n')
        for label, ok, detail in score_rows:
            if committed_only and label.startswith('score[data]'):
                out.write('  – score[data]: machine-local — reported on the terminal '
                          'and in tmp/logs/test/run.log, never committed\n')
                continue
            mark = '✓' if ok else ('⚠' if label.startswith('score[data]') else '✗')
            out.write(f'  {mark} {label}' +
                      (f'\n      {detail}\n' if not ok and detail else '\n'))

        # Penultimate: WARN — advisory, never gating.
        lines: list[tuple[list[str], str | None, list[str]]] = []
        if warn_idx:
            counts = {sec: sum(1 for i in warn_idx if sections[i] == sec) for sec in warn_sections}
            where = 'above' if include_body else 'in the full report (tmp/logs/test/run.log)'
            out.write(f'\nWARN — machine-local facts, marked ⚠ {where}; they never gate a commit:\n')
            for sec in warn_sections:
                out.write(f'  {sec} ({counts[sec]})\n')
            warn_fails = [(results[i][0], results[i][2]) for i in warn_idx]
            warn_lines = _fix_lines(warn_fails, [h for h in fix_hints if fix_tier.get(h) == 'data'])
            if warn_lines:
                out.write('  to address, at leisure:\n')
                _write_fixes(out, warn_lines, '⚠')
            lines += warn_lines

        # Final: the gate's actual verdict.
        if gate_idx:
            counts = {sec: sum(1 for i in gate_idx if sections[i] == sec) for sec in gate_sections}
            out.write('\nFAIL — these gate: the hook vetoes the commit, and any run '
                      'exits non-zero:\n')
            for sec in gate_sections:
                out.write(f'  {sec} ({counts[sec]})\n')
            gate_fails = [(results[i][0], results[i][2]) for i in gate_idx]
            gate_lines = _fix_lines(gate_fails, [h for h in fix_hints
                                                 if fix_tier.get(h) != 'data'])
            if gate_lines:
                out.write('\nTo fix:\n')
                _write_fixes(out, gate_lines, '✗')
            lines += gate_lines
        else:
            out.write(f'\ngate: PASS — code+schema {det} match the committed expectation; '
                      'nothing here vetoes a commit\n')
        # The verdict is the terminal word — no trailing offer after it. The
        # remediation each finding needs is already printed beside it (WARN's
        # "to address, at leisure"; the gate's "To fix"). We do NOT append a
        # blanket "or run with --fix to apply and stage automatically": it fired
        # even on a clean PASS (lines includes non-gating advisories), sat after
        # the verdict where its "or" had no antecedent, and over-promised — the
        # surviving items here are cmd-less curation advice --fix never executes.
        # It also offered to stage, which --fix no longer does at all. --fix stays available
        # for anyone who invokes it deliberately (see --help); it just isn't
        # advertised after every run.
        return out.getvalue(), lines

    committed_text, _         = _render(committed_only=True)
    full_text, full_fix_lines = _render(committed_only=False)
    terminal_text, _          = _render(committed_only=False, include_body=False)

    (RSC / 'test' / 'run.log').write_text(committed_text)
    machine_log = REPO_ROOT / 'tmp' / 'logs' / 'test' / 'run.log'
    machine_log.parent.mkdir(parents=True, exist_ok=True)
    machine_log.write_text(full_text)

    print(terminal_text, end='')

    if failures and args.fix and full_fix_lines:
        print()
        print('Running fixes:')
        for ps, cmd, gs in full_fix_lines:
            for p in ps[:3]:
                print(f'  ✗ {p}')
            if cmd is None:
                # advice, not a command — print it, never execute it
                for g in gs:
                    print(f'      ↳ {g}')
                continue
            print(f'  {cmd}')
            # A hint names the command a reader types, which is `yoga` — on a PATH only an
            # installed clone has. Run it through this repo's own entrypoint, so the hint
            # stays typeable prose and still executes in a clone that installed nothing.
            run_as = f'./{cmd}' if cmd.startswith('yoga ') else cmd
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
        print('Fixes applied to the worktree — nothing staged. Review with '
              '`git diff`, stage what you meant, then re-run run.sh to verify.')

    # The data tier is machine-local ("not recorded"): a stale capture on this
    # machine is a fact about its data, not about the change being committed.
    # Data failures are reported in the WARN tail and the log, but only code/schema/score
    # failures veto the exit status — otherwise local data drift would fail every
    # run everywhere. This tier rule is now the ONLY thing standing between local
    # data drift and a blocked commit: the veto used to soften itself on feature
    # branches, and no longer does (2026-07-17 — a check that reads your branch
    # name to decide how much to mean it). What is machine-local never gates;
    # what is deterministic always does. The axis is the tier, not the branch.
    gating = [i for i, (_, p, _) in enumerate(results) if not p and tiers[i] != 'data']
    sys.exit(1 if gating else 0)


if __name__ == '__main__':
    main()
