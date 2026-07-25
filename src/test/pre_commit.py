#!/usr/bin/env python
"""
pre_commit.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/pre_commit.sh
    src/test/pre_commit.sh --fix   # run all fix commands; stages nothing

As a git hook, install the wrapper:
    ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Checks are grouped into three tiers, run in order:
    code    — repo code and documentation (required files, xref); deterministic on any clone
    schema  — committed schema artifacts (diagnostics, changelogs, joins, mcp currency);
              deterministic on any clone (mcp currency needs network)
    data    — local data/input//tmp/cache/ data vs the committed record (validation outputs, coverage,
              frontier); machine-local, skipped per pipeline where no local data exists

The committed expected score (rsc/test/pre_commit_expected_score) records the code and
schema tiers only — their counts are identical on every clone. Its first line is the
combined code+schema total, which also matches the score in the log's head line. The
data tier's subtotal is machine-local and never recorded; its failures are reported in
full but never veto the exit — a fact about this machine's data must not gate an
unrelated commit. Machine state that SHOULD gate — the hook's own installation — is
enforced by the wrapper (pre_commit.sh), never by a tier.

Atomic diagnostic scripts live in src/test/diagnostics/{principle_id}.py.
Atomic repair scripts live in src/test/repairs/{principle_id}.py.
Each diagnostic takes a schema path as argv[1], exits 0 on pass, 1 on fail.
"""

import csv
import io
import json
import re
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

sys.path.insert(0, str(SRC / 'main' / 'cli'))  # the yoga CLI cluster (dispatch + standalone commands)
import cli  # noqa: E402 — the CLI table machinery (check_cli_surface)
import cache_io  # noqa: E402 — the declared tmp/cache/ IO registry (check_cache_io)

sys.path.insert(0, str(SRC / 'main' / 'chat-exports'))  # the shared deposit rule (check_accumulate_contract)
import accumulate as _accumulate  # noqa: E402 — the CALCULUS accumulate operation (issue #22)

sys.path.insert(0, str(SRC / 'main' / 'model'))  # index curation machinery
from build_index import inferred_concepts, orphan_headwords, pending_concepts  # noqa: E402
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
        fix_item_cmd      = 'src/main/browser-captures/claude/validate.sh --browser-capture',
    ),
    'chat-exports': Pipeline(
        schemas           = ['conversations', 'memories', 'projects', 'users'],
        changelog         = RSC_SCHEMA / 'chat-exports' / 'conversations' / 'CHANGELOG.md',
        cache_output      = REPO_ROOT / cache_io.path_for('chat-exports'),
        input             = INPUT / 'claude' / 'chat' / 'bulk-export',
        input_glob        = 'data-*/',
        subject_depth     = 1,
        fix_item_cmd      = 'src/main/chat-exports/validate.sh --chat-export',
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
        # from .jsonl comes first), so the runnable store-rooted unit is the project RUNME.
        fix_item_cmd      = 'src/main/code-agents/RUNME.sh --code-agent',
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
    pre_commit.log then carries no machine-derived slugs (they embed the username)."""
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
        SRC  / 'main' / 'model' / 'gen_model.py',
        RSC  / 'test' / 'pre_commit_expected_score',
        RSC  / 'test' / 'xref_expected_score',
        SRC  / 'test' / 'schema_recommendations.py',
        SRC  / 'run_python_script.sh',
    ]
    for path in required:
        run(f'exists: {path.relative_to(REPO_ROOT)}', path.exists())


def check_root_schema_diagnostics(run):
    root_schemas = sorted(RSC_SCHEMA.glob('*.json'))
    diagnostics  = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))

    for schema_path in root_schemas:
        for script in diagnostics:
            diag = script.stem
            passed, output = _call(script, str(schema_path))
            run(f'{diag}: {schema_path.relative_to(RSC_SCHEMA)}', passed,
                _diag_detail(output) if not passed else None)


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
                    'Missing $schema field' if '$schema' not in schema else None)
            except json.JSONDecodeError as e:
                run(f'{schema_name}: valid JSON: {v}', False, str(e))


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
                if f'## {v}' not in changelog_text else None)
            schema_text = path.read_text()
            run(f'{schema_name}: no_todo: {v}',
                '"TODO' not in schema_text,
                f'Replace TODO descriptions in {path.relative_to(REPO_ROOT)}'
                if '"TODO' in schema_text else None)


def check_pipeline_validation_outputs(run, fix, name: str, pipeline: Pipeline) -> None:
    """Each datum's matrix.md must exist and agree with the vN.log files beside it;
    every schema version must be registered by some datum; every input entry must
    have been processed. Matrices are co-located with their data, so stale rows for
    departed data cannot exist — deleting a datum deletes its matrix."""
    run_cmd  = f'src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {name} --write'
    pipe_cmd = f'Run: src/main/{name}/RUNME.sh --{name} {pipeline.input.relative_to(REPO_ROOT)}'
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
            run(f'matrix.written: {_leaf(subject)}', False, str(mfile.relative_to(REPO_ROOT)))
            continue
        actual = _parse_matrix_file(mfile)
        ok = actual == {k: sym for k, (sym, _) in expected.items()}
        if not ok:
            fix(run_cmd, problem=f'matrix.current: {_leaf(subject)} — matrix.md disagrees with validation logs')
        run(f'matrix.current: {_leaf(subject)}', ok,
            None if ok else f'matrix.md disagrees with validation logs — regenerate: {run_cmd}')

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
            run(f'{schema}: matrix.version_registered: {v}', ok)

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
            run(f'unprocessed input: {_leaf(subject)}', False)


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
        run(label, passing, None if passing else 'validates against no schema version')


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
    run(label, ok, None if ok else str(log.relative_to(REPO_ROOT)))


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
        run(f'indexing: concept disposed: {c}', disposed)
        if not disposed:
            fix('yoga indexing candidates  # write the pending queue: tmp/cache/indexing/candidates.txt',
                problem=f'indexing: concept undisposed: {c}',
                guidance='dispose each pending concept: yoga indexing accept <term> [alias ...] '
                         '| yoga indexing reject [--reason <why>] <concept>')
    # The REVERSE direction (the curate symmetry, PR #36's model.json precedent:
    # a curation record must be grounded both ways). An accepted headword with
    # ZERO corpus locators is orphan documentation — a dead index entry whose
    # concept left the corpus or whose aliases never matched. build_index's sync
    # line has always carried the located/total ratio; this names the orphans.
    # Advisory like the rest of this section: the corpus is machine-local data.
    markdown_root = REPO_ROOT / 'data' / 'output' / 'markdown'
    if markdown_root.is_dir():
        for h in orphan_headwords(markdown_root,
                                  REPO_ROOT / 'data' / 'output' / 'indexing' / 'accepted.txt'):
            run(f'indexing: headword grounded: {h}', False)
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
            '\n      '.join(detail_parts) if detail_parts else None)


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
        run('cache_io: registry parses: rsc/cache_io.csv', False, str(e))
        return
    run('cache_io: registry parses: rsc/cache_io.csv', True)

    # PIPELINES now derives cache_output from cache_io.path_for(), so a pipeline
    # missing its row fails loudly at import; this catches the reverse — a
    # pipeline TAG in cache_io naming no real pipeline (or a mismatch either way).
    tagged = cache_io.pipelines()
    run('cache_io: pipeline tags match PIPELINES', tagged == set(PIPELINES),
        f'cache_io tags {sorted(tagged)} != PIPELINES {sorted(PIPELINES)}'
        if tagged != set(PIPELINES) else None)

    commands = {c['command'] for c in cli.commands()}
    for r in rows:
        # read-but-not-written: the catastrophe (see docstring).
        read_no_writer = bool(r['read_by']) and not r['written_by']
        run(f'cache_io: {r["cache_path"]}: read implies a writer', not read_no_writer,
            'READ but not WRITTEN — a tmp/cache/ dependency nothing produces; name its '
            'producer in written_by, or the tmp/cache/ contract breaks' if read_no_writer else None)
        # Every producer/reader RESOLVES — a rename that strands one (how
        # tmp/cache/browser-captures/markdown happened) fails here, not silently.
        unresolved = [e for e in r['written_by'] + r['read_by']
                      if not _cache_io_resolves(e, commands)]
        run(f'cache_io: {r["cache_path"]}: producers/readers resolve', not unresolved,
            f'unresolved: {", ".join(unresolved)}' if unresolved else None)


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
    """The yoga CLI's table (rsc/cli/commands.csv) is an interface and must not
    lie: it parses, command names are unique, every target exists, every
    calculus term a row cites is defined in rsc/CALCULUS.md (the vocabulary is
    parsed from the document itself), every flag a usage sketch advertises
    appears in the target's source or its stem-sibling .py/.sh pair (wrapper
    and implementation share a stem — the repo idiom), every subcommand VERB it
    advertises appears in the target's own --help (the live dispatch surface —
    a source grep is vacuous for ordinary words like build/accept), and every command
    a help.csv `step` row marks is invoked BY COMMAND AND VERB in the src/RUNME.sh --plan
    output (which is itself the executing list, so the chain cannot drift, and a step
    cannot quietly drop to a bare noun that the bare=status convention no-ops). Committed
    files and the deterministic plan only, so deterministic on any clone:
    code tier."""
    try:
        cmds = cli.commands()
    except Exception as e:
        run('cli: table parses: rsc/cli/commands.csv', False, str(e), law='G4')
        return
    run('cli: table parses: rsc/cli/commands.csv', True, law='G4')
    names = [c['command'] for c in cmds]
    dupes = sorted({n for n in names if names.count(n) > 1})
    run('cli: command names unique', not dupes, ', '.join(dupes) if dupes else None,
        law='G4')
    # alphabetical by contract (2026-07-15): every surface derived from the table
    # (help, synopsis, completion) inherits its order, so the table carries it
    run('cli: commands alphabetical', names == sorted(names),
        None if names == sorted(names) else
        f'first out of order: {next(a for a, b in zip(names, sorted(names)) if a != b)}',
        law='G4')
    vocab = cli.calculus_terms()
    for c in cmds:
        target = REPO_ROOT / c['target']
        run(f'cli: {c["command"]}: target exists: {c["target"]}', target.exists(), law='G7')
        unknown = [t for t in c['calculus'].split() if t not in vocab]
        run(f'cli: {c["command"]}: cited calculus defined', not unknown,
            f'not defined in rsc/CALCULUS.md: {", ".join(unknown)}' if unknown else None,
            law='G6')
        # subcommands and flags are read from rsc/cli/help.csv — the single source the
        # usage is generated from — so there is no usage cell to reconcile it against, and
        # no help.csv-complete check: the two cannot drift because there is only one.
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
                (where + ', '.join(missing)) if missing else None, law='G5')
        # Docstring honesty (issue #33): a module docstring's Usage block is a
        # declared surface too, and nothing read it against the parser —
        # memories' documented three flags no parser defined, and both checks
        # here were satisfied (help.csv honestly advertised none; the lie lived
        # only in the docstring). Every --flag a Usage block cites must be
        # advertised; real ⊆ advertised is held below, so advertised is the one
        # universe a documented flag can exist in.
        doc: set[str] = set()
        for m in re.finditer(r'^Usage.*?(?=\n"""|\n\'\'\'|\Z)', text, flags=re.M | re.S):
            doc.update(re.findall(r'--[a-z][\w-]+', m.group(0)))
        doc.discard('--help')
        undeclared = sorted(doc - set(flags))
        run(f'cli: {c["command"]}: docstring Usage flags advertised', not undeclared,
            f'documented in a Usage block but not in help.csv: {", ".join(undeclared)}'
            if undeclared else None, law='G5')
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
                law='G5')
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
            if unadvertised else None, law='G5')
        # Positionally usable where advertised (issue #33): help.csv renders a
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
                    if rejected else None, law='G5')
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
                law='G8')
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
            f.write(cli.completion_script(cmds))
            tmp = f.name
        proc = subprocess.run([zsh, '-n', tmp], capture_output=True, text=True)
        Path(tmp).unlink()
        parse_ok, parse_err = proc.returncode == 0, (proc.stderr.strip() or None)
    run('cli: completions: emitted script parses (zsh -n)', parse_ok,
        parse_err if not parse_ok else None, law='G9')

    # The run pipeline's command-backed steps (help.csv's `step` column). Each must
    # appear in `src/RUNME.sh --plan` as a line naming the COMMAND and its VERB — so the
    # plan speaks the command surface a reader would type, and a step can never invoke
    # a noun bare, which the bare-noun=status convention silently turns into a no-op.
    stepped = cli.steps()
    if not stepped:
        return
    plan = subprocess.run([str(REPO_ROOT / 'src' / 'RUNME.sh'), '--plan'],
                          capture_output=True, text=True, cwd=REPO_ROOT).stdout
    for s in stepped:
        cmd, sub = s['command'], s['subcommand']
        # the plan line is the step label then its non-path args (steps.sh): the label
        # must BE the command, and the verb must be among the args after it
        ok = bool(re.search(rf'^\s*{re.escape(cmd)}\b.*\b{re.escape(sub)}\b', plan, re.M))
        run(f'cli: {cmd}: run step invokes `{cmd} {sub}` in plan', ok,
            None if ok else f'no `{cmd} … {sub}` line in `src/RUNME.sh --plan` — a bare '
            f'`{cmd}` step would silently be a status no-op', law='G10')


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
        run('grammar: laws parse: rsc/cli/README.md', False, str(e))
        return
    run('grammar: laws parse: rsc/cli/README.md', bool(laws),
        None if laws else 'no `- **G<n> — …**` law bullets found')
    if not laws:
        return

    orphans = sorted(set(cited) - set(laws))
    run('grammar: every citation names a stated law', not orphans,
        f'cited by a check but not stated in the grammar: {", ".join(orphans)}'
        if orphans else None)

    stateless = sorted(g for g, law in laws.items() if law['state'] not in cli.LAW_STATES)
    run('grammar: every law declares a state', not stateless,
        f'no `gated`/`by construction`/`unenforced`/`doctrine` marker: {", ".join(stateless)}'
        if stateless else None)

    # AGGREGATE, not one check per law: nineteen lines saying "G7 is cited" carry the same
    # fact as one saying "7/7 gated laws are cited", and the failing ids belong in a detail
    # line rather than in nineteen labels. A report is read by someone deciding whether to
    # look closer; per-law rows make that decision harder, not easier.
    ids = lambda gs: ', '.join(sorted(gs, key=lambda g: int(g[1:])))

    gated = {g for g, law in laws.items() if law['state'] == 'gated'}
    uncited = gated - set(cited)
    run(f'grammar: every gated law is cited by a check ({len(gated) - len(uncited)}/{len(gated)})',
        not uncited,
        f'declares `gated` but no check cites it: {ids(uncited)}' if uncited else None)

    unenforced = {g for g, law in laws.items() if law['state'] == 'unenforced'}
    issueless = {g for g in unenforced if not laws[g]['issues']}
    run(f'grammar: every unenforced law names its issue ({len(unenforced) - len(issueless)}/{len(unenforced)})',
        not issueless,
        f'declares `unenforced` with no #issue: {ids(issueless)}' if issueless else None)

    # a cited law is held, whatever it claims: the claim is what is wrong
    miscited = {g for g, law in laws.items()
                if law['state'] in ('unenforced', 'doctrine') and g in cited}
    run('grammar: no unenforced or doctrine law is cited', not miscited,
        '; '.join(f'{g} declares `{laws[g]["state"]}` but is cited by: '
                  f'{", ".join(cited[g])}' for g in sorted(miscited)) if miscited else None)

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
                  for g, parent in sorted(dangling.items())) if dangling else None)

    # The enforcement map, printed rather than maintained as prose: this IS the
    # "held honest by the gates" list the README used to carry by hand.
    by_state: dict[str, list[str]] = {}
    for gid, law in laws.items():
        by_state.setdefault(str(law['state']), []).append(gid)
    summary = '; '.join(f'{st}: {len(g)}' for st, g in sorted(by_state.items()))
    run(f'grammar: {len(laws)} laws — {summary}', True)


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
                f'{schema_dir.relative_to(REPO_ROOT) if schema_dir else schema_name} has no v*.json files')
            continue
        for version in versions:
            for script in diagnostics:
                passed, output = _call(script, str(version))
                run(f'{schema_name}: {script.stem}: {version.stem}', passed,
                    _diag_detail(output) if not passed else None)


def check_schema_join(run):
    join = RSC_SCHEMA / 'model_join.csv'
    if not join.exists():
        run('schema model_join.csv exists', False)
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
        '\n    '.join(fails[:5]) if fails else None)


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
        '\n    '.join(pins[:5]) if pins else None)


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
        '\n    '.join(pins[:5]) if pins else None)
    run('model: occurrence pointers resolve against latest versions', not bad,
        '\n    '.join(bad[:5]) if bad else None)
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
                      for n, f in list(gaps.items())[:5]) if gaps else None)


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
            'document it in rsc/schema/model.json or reject it in rsc/schema/model_rejected.txt')
    orphans = set(model_curation.orphan_entries())
    for name in sorted(model_curation.documented()):
        run(f'model: documented type grounded: {name}', name not in orphans,
            None if name not in orphans else
            'no model_join edge asserts this type: curate the asserting edge '
            '(relationship identical | snake_cased), or retire the entry')


def check_mcp_schema(run):
    """The LATEST _reference/mcp/vN.json must match the upstream schema at the raw
    URL in its description. Upstream drift is answered by MINTING the next version
    beside the old one (the snapshot's history is data), never by updating in place."""
    import hashlib, urllib.request
    mcp_dir  = RSC_SCHEMA / '_reference' / 'mcp'
    versions = _sorted_versions(mcp_dir) if mcp_dir.is_dir() else []
    if not versions:
        run('mcp schema: _reference/mcp/ has versions', False)
        return
    latest = versions[-1]
    rel    = latest.relative_to(REPO_ROOT)
    desc = json.loads(latest.read_text()).get('description', '')
    m_url  = re.search(r'(https://raw\.githubusercontent\.com/\S+)', desc)
    m_hash = re.search(r'upstream SHA256:\s*([0-9a-f]{64})', desc)
    if not m_url or not m_hash:
        run('mcp schema: description has raw URL and upstream SHA256', False,
            f'Add raw URL and "upstream SHA256: <hex>" to the description field in {rel}')
        return
    raw_url     = m_url.group(1)
    stored_hash = m_hash.group(1)
    try:
        with urllib.request.urlopen(raw_url, timeout=15) as resp:
            live_hash = hashlib.sha256(resp.read()).hexdigest()
        run(f'mcp schema: {latest.stem} up to date',
            stored_hash == live_hash,
            f'upstream changed — mint _reference/mcp/v{len(versions) + 1}.json from {raw_url} '
            f'(convert to draft-04, set its description commit URL + SHA256, narrate in the family '
            f'CHANGELOG); {rel} stays as history')
    except Exception as e:
        run('mcp schema: upstream reachable', False, f'{e}')



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

    run('xref: no bad pointers', bad == 0, summary if bad else None)
    run(f'xref: {actual}', actual == expected,
        f'expected: {expected}  →  consider updating {score_file.relative_to(REPO_ROOT)}'
        if actual != expected else None)


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
            not failed, 'cases failed: ' + '; '.join(failed) if failed else None)
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
    # identical on any clone and becomes the COMMITTED rsc/test/pre_commit.log; the
    # data tier describes THIS MACHINE's data (uuids, batch names, home-dir-derived
    # paths) and must never enter a committed artifact — it goes to the terminal and
    # to tmp/logs/rsc/test/pre_commit.log (machine-facing, like the serve daemon's log).
    committed_buffer = io.StringIO()   # code + schema tiers
    machine_buffer   = io.StringIO()   # data tier
    cited_laws: dict[str, list[str]] = {}   # grammar law id -> the labels citing it

    def run(label, passed, detail=None, law=None):
        # `law` cites the rsc/cli/README.md grammar law this fact enforces (G<n>).
        # Recorded, not printed: check_grammar_laws reads the citations to hold the
        # document and the checks to each other, in both directions.
        results.append((label, passed, detail))
        if law:
            cited_laws.setdefault(law, []).append(label)
        # Data-tier facts are advisory (they never veto — see the exit) and
        # carry the WARN sigil ⚠, never the gating ✗ (user specification,
        # 2026-07-12: a "final summary" must not LOOK failed where nothing
        # blocks).
        mark = '✓' if passed else ('⚠' if current_tier[0] == 'data' else '✗')
        print(f'  {mark} {label}' + (f'\n      {detail}' if not passed and detail else ''))

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
        sys.stdout = machine_buffer if tier == 'data' else committed_buffer
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
        # after check_cli_surface: it reads that run's citations
        run_section(lambda run, _c=cited_laws: check_grammar_laws(run, _c),
                    label='check_grammar_laws', tier='code')
        run_section(check_cache_io, tier='code')
        run_section(check_accumulate_contract, tier='code')

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

    score_file = RSC / 'test' / 'pre_commit_expected_score'
    expected: dict[str, str] = {}
    expected_total = None
    for line in score_file.read_text().splitlines():
        m = re.match(r'([a-z]+):\s*(\d+/\d+)$', line.strip())
        if m:
            expected[m.group(1)] = m.group(2)
        elif expected_total is None and (m := re.match(r'(\d+/\d+)$', line.strip())):
            expected_total = m.group(1)

    score_rows: list[tuple] = []

    exp = expected_total or '(none)'
    ok  = det_got == det_tot and det == exp
    detail = (
        'Fix failures in the code and schema tiers first' if det_got != det_tot else
        f'Consider updating the first line of {score_file.relative_to(REPO_ROOT)} to {det}'
        if det != exp else None
    )
    score_rows.append((f'score[code+schema]: {det}; expected: {exp}', ok, detail))

    for t in ('code', 'schema'):
        got, tot = tier_counts.get(t, [0, 0])
        sub = f'{got}/{tot}'
        exp = expected.get(t, '(none)')
        ok  = got == tot and sub == exp
        detail = (
            'Fix failures in this tier first' if got != tot else
            f'Consider updating {score_file.relative_to(REPO_ROOT)}: "{t}: {sub}"'
            if sub != exp else None
        )
        score_rows.append((f'score[{t}]: {sub}; expected: {exp}', ok, detail))

    got, tot = tier_counts.get('data', [0, 0])
    skipped_note = f' (skipped: {", ".join(sorted(data_skipped))})' if data_skipped else ''
    if tot == 0:
        score_rows.append((f'score[data]: skipped — no local data{skipped_note}', True, None))
    else:
        score_rows.append((f'score[data]: {got}/{tot}; machine-local, not recorded{skipped_note}',
                           got == tot, None))

    for label, ok, detail in score_rows:
        results.append((label, ok, detail))
        sections.append('check_score')
        # score[data] carries the data tier's advisory nature: it is reported but,
        # like the tier it summarises, must not gate commits (see exit below).
        tiers.append('data' if label.startswith('score[data]') else 'score')
        if not ok:
            failures.append((label, detail))

    # ── report rendering ─────────────────────────────────────────────────────
    # Two renderings of one result set, split by determinism exactly as the tiers
    # are: the COMMITTED report (code+schema and their scores — byte-identical on
    # any clone; this script writes it to rsc/test/pre_commit.log itself) and the
    # FULL report (adds the machine-local data tier — printed to stdout and written
    # to tmp/logs/rsc/test/pre_commit.log, run-facing like the serve daemon's log).

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
            out.write(f'`src/test/pre_commit.py`: {det} ({data_note}; '
                      f'{len(gate_sections)} gating / {len(warn_sections)} advisory section(s) failing)\n')
        else:
            out.write(f'pre_commit.py: {det} ({data_note})\n')

        out.write('\n')
        if include_body:
            out.write(committed_buffer.getvalue())
            if not committed_only:
                out.write(machine_buffer.getvalue())
        else:
            out.write('  full per-check report → tmp/logs/rsc/test/pre_commit.log\n')

        name = 'check_score'
        out.write(f'\n── {name} {"─" * (74 - len(name))}\n')
        for label, ok, detail in score_rows:
            if committed_only and label.startswith('score[data]'):
                out.write('  – score[data]: machine-local — reported on the terminal '
                          'and in tmp/logs/rsc/test/pre_commit.log, never committed\n')
                continue
            mark = '✓' if ok else ('⚠' if label.startswith('score[data]') else '✗')
            out.write(f'  {mark} {label}' +
                      (f'\n      {detail}\n' if not ok and detail else '\n'))

        # Penultimate: WARN — advisory, never gating.
        lines: list[tuple[list[str], str | None, list[str]]] = []
        if warn_idx:
            counts = {sec: sum(1 for i in warn_idx if sections[i] == sec) for sec in warn_sections}
            where = 'above' if include_body else 'in the full report (tmp/logs/rsc/test/pre_commit.log)'
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

    (RSC / 'test' / 'pre_commit.log').write_text(committed_text)
    machine_log = REPO_ROOT / 'tmp' / 'logs' / 'rsc' / 'test' / 'pre_commit.log'
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
            subprocess.run(cmd, shell=True, cwd=REPO_ROOT)
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
              '`git diff`, stage what you meant, then re-run pre_commit.sh to verify.')

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
