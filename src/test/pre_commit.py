#!/usr/bin/env python
"""
pre_commit.py — Pre-commit checks for the repo.

Usage (direct):
    src/test/pre_commit.sh
    src/test/pre_commit.sh --fix   # run all fix commands, then stage with git add -u

As a git hook, install the wrapper:
    ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit

Exits 0 if all checks pass, 1 if any fail.

Checks are grouped into three tiers, run in order:
    code    — repo code and documentation (required files, xref); deterministic on any clone
    schema  — committed schema artifacts (diagnostics, changelogs, joins, mcp currency);
              deterministic on any clone (mcp currency needs network)
    data    — local ext//gen/ data vs the committed record (validation outputs, coverage,
              frontier); machine-local, skipped per pipeline where no local data exists

The committed expected score (src/test/pre_commit_expected_score) records the code and
schema tiers only — their counts are identical on every clone. Its first line is the
combined code+schema total, which also matches the score in the log's head line. The
data tier's subtotal is machine-local and never recorded; its failures still fail the
run wherever data exists.

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
EXT                      = REPO_ROOT / 'ext'
GEN                      = REPO_ROOT / 'gen'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
RSC_SCHEMA               = RSC / 'schema'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'diagnostics'

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ — shared modules live at its root
from validation_matrix import rows_from_logs  # noqa: E402

sys.path.insert(0, str(SRC / 'main'))  # markdown_projection owns the format, both directions
from markdown_projection import conv_id as _conv_id, turn_seq  # noqa: E402

# ── Pipeline model ────────────────────────────────────────────────────────────

@dataclass
class Pipeline:
    schemas:         list[str]
    changelog:       Path
    gen:             Path
    input:           Path
    input_glob:      str
    subject_depth:   int
    # Per-item remedy command; takes the pipeline's TOP-LEVEL ext/ entry (see _fix_item_cmd).
    fix_item_cmd:    str
    # Extra diagnostics to skip beyond the universal versioned-schema skip set.
    # composition.base_schemas_closed — session deviation: TurnBase intentionally open (see principles.md).
    diagnostic_skip:    frozenset[str] = frozenset()
    gen_key_prefix:     str = ''

PIPELINES: dict[str, Pipeline] = {
    'browser-captures': Pipeline(
        schemas           = ['apiConversation'],
        changelog         = RSC_SCHEMA / 'browser-captures' / 'apiConversation' / 'CHANGELOG.md',
        gen               = GEN / 'browser-captures' / 'claude',
        input             = EXT / 'browser-captures' / 'claude',
        input_glob        = '*/',
        subject_depth     = 1,
        fix_item_cmd      = 'src/main/browser-captures/claude/validate.sh --browser-capture',
    ),
    'chat-exports': Pipeline(
        schemas           = ['conversations', 'memories', 'projects', 'users'],
        changelog         = RSC_SCHEMA / 'chat-exports' / 'conversations' / 'CHANGELOG.md',
        gen               = GEN / 'chat-exports',
        input             = EXT / 'chat-exports',
        input_glob        = 'data-*/',
        subject_depth     = 1,
        fix_item_cmd      = 'src/main/chat-exports/validate.sh --chat-export',
    ),
    'code-projects': Pipeline(
        schemas           = ['session'],
        changelog         = RSC_SCHEMA / 'code-projects' / 'session' / 'CHANGELOG.md',
        gen               = GEN / 'code-projects',
        input             = EXT / 'code-projects',
        input_glob        = '-Users-*/*.jsonl',
        subject_depth     = 2,
        # validate.sh --code-project-session consumes the gen/ session dir (conversion
        # from .jsonl comes first), so the runnable ext-rooted unit is the project RUNME.
        fix_item_cmd      = 'src/main/code-projects/RUNME.sh --code-project',
        diagnostic_skip   = frozenset({'composition.base_schemas_closed'}),
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
    TOP-LEVEL ext/ entry containing the subject — the granularity every per-item
    command actually accepts. A depth-2 subject ('<project> / <uuid>') therefore
    hints at its project; joining the full subject would name a path no command
    consumes (and, for code-projects, one that does not even exist as given)."""
    item = pipeline.input / subject.split(' / ')[0]
    return f'{pipeline.fix_item_cmd} {item.relative_to(REPO_ROOT)}'


def _datum_dirs(pipeline: Pipeline) -> list[Path]:
    """Each datum directory in gen/ (the dirs that contain a validation/ subdir),
    at the pipeline's subject depth."""
    glob = '*/validation' if pipeline.subject_depth == 1 else '*/*/validation'
    return sorted(v.parent for v in pipeline.gen.glob(glob) if v.is_dir())

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
    if not pipeline.input.exists():
        return []
    glob      = pipeline.input_glob.rstrip('/')
    dirs_only = pipeline.input_glob.endswith('/')
    if pipeline.subject_depth == 1:
        return sorted(d.name for d in pipeline.input.glob(glob) if d.is_dir())
    result = []
    for item in sorted(pipeline.input.glob(glob)):
        if item.is_dir() and dirs_only:
            result.append((item.parent.name, item.name))
        elif not item.is_dir() and not dirs_only:
            # For multi-level globs (e.g. data-*/projects/*.json), walk up enough
            # levels to find the first wildcard segment (the outer subject).
            outer_depth = len(glob.rsplit('/', 1)[0].split('/'))
            outer = item
            for _ in range(outer_depth):
                outer = outer.parent
            result.append((outer.name.removeprefix(pipeline.gen_key_prefix), item.stem))
    return result


def _has_local_data(pipeline: Pipeline) -> bool:
    """True if this machine holds any data for the pipeline — input entries in ext/ or
    previously generated output in gen/. Gates the data tier: where neither exists the
    pipeline's data checks are skipped (the committed matrices are the durable record)."""
    if _input_subjects(pipeline):
        return True
    return pipeline.gen.exists() and any(pipeline.gen.iterdir())


def _check_csv_pointers(csv_path: Path, columns: tuple, base_for: dict, fails: list) -> None:
    """Validate JSON Pointer fragments in a join CSV. base_for maps column name → base dir."""
    with csv_path.open() as fh:
        for i, row in enumerate(csv.DictReader(fh), 2):
            for col in columns:
                ref = row[col].strip()
                if not ref:
                    continue
                file_part, _, pointer = ref.partition('#')
                f = (base_for.get(col, RSC_SCHEMA / 'conversations') / file_part).resolve()
                if not f.exists():
                    fails.append(f'row {i} {col}: file not found: {file_part}')
                    continue
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
        SRC  / 'test' / 'pre_commit_expected_score',
        SRC  / 'test' / 'xref_expected_score',
        SRC  / 'main' / 'schema_recommendations.py',
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
    gen_rel  = pipeline.gen.relative_to(REPO_ROOT)

    print(f'\n  each {gen_rel}/<datum>/matrix.md must match the vN.log files under its validation/')
    seen_versions: dict[str, set[str]] = {}
    processed_subjects: set[str] = set()
    for datum_dir in _datum_dirs(pipeline):
        subject  = ' / '.join(datum_dir.relative_to(pipeline.gen).parts)
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
        else [f'{p1} / {p2}' for p1, p2 in raw_input]
    )
    for subject in sorted(current_subjects):
        if subject not in processed_subjects:
            fix(pipe_cmd, problem=f'unprocessed input: {_leaf(subject)} — no validation output in {gen_rel}/')
            fix(f'then: {run_cmd}')
            run(f'unprocessed input: {_leaf(subject)}', False)


def _gen_subject_dirs(gen_dir, depth):
    """Yield (subject, leaf_dir) for each subject directory in gen_dir."""
    if not gen_dir.exists():
        return
    for d1 in sorted(gen_dir.iterdir()):
        if not d1.is_dir():
            continue
        if depth == 1:
            yield d1.name, d1
        else:
            for d2 in sorted(d1.iterdir()):
                if d2.is_dir():
                    yield f'{d1.name} / {d2.name}', d2


def _datum_recency(name: str, pipeline: Pipeline, subject: str):
    """A sortable recency key for one datum, or None if unavailable. Pipeline-specific,
    because the corpora differ: chat-exports uses the epoch embedded in the batch dir name;
    browser-captures the capture's `updated_at`; code-projects the max record `timestamp` in
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
    if name == 'code-projects':
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
    for subject, leaf_dir in _gen_subject_dirs(pipeline.gen, pipeline.subject_depth):
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
    for subject, leaf_dir in _gen_subject_dirs(pipeline.gen, pipeline.subject_depth):
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


def check_cross_sources(run) -> None:
    """Append-only invariant across export surfaces: every conversation present in BOTH
    a bulk export and the live captures must project to a turn sequence identical to,
    or a prefix of, the capture's — a bulk export is a point-in-time snapshot and
    conversations only ever gain turns. The capture being a prefix of the EXPORT is
    the mirror case: a stale capture, fixed by recapturing that conversation (the
    remedy is printed). Divergence inside the shared prefix means a projection bug
    or data corruption (or a post-export edit/branch switch — rare; investigate
    with compare_sources --diff). Reads the projections both pipelines already
    wrote to gen/; machine-local, so data tier."""
    api_dir = REPO_ROOT / 'lib' / 'markdown' / 'claude' / 'conversations'
    api = {}
    if api_dir.is_dir():
        for f in api_dir.glob('*.md'):
            text = f.read_text()
            cid = _conv_id(text)
            if cid:
                api[cid] = turn_seq(text)
    if not api:
        print('  – skipped: no api projections (lib/markdown/claude/conversations empty)')
        return
    batch_dirs = sorted((GEN / 'chat-exports').glob('data-*/markdown')) if (GEN / 'chat-exports').is_dir() else []
    if not batch_dirs:
        print('  – skipped: no bulk-export projections (gen/chat-exports/*/markdown empty)')
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
                f"\n        → run: src/main/browser-captures/safari_capture.sh --agent claude --id {cid}"
                f"  # first front https://claude.ai/chat/{cid} in Safari (logged in)")
        if divergent:
            detail_parts.append('divergent (projection bug, corruption, or post-export edit): '
                                + ', '.join(divergent[:5]))
        run(f'cross-source: {mdir.parent.name}: {shared} shared — '
            f'{identical} identical, {appended} appended-to'
            + (f', {len(stale)} capture-stale' if stale else ''),
            not (stale or divergent),
            '\n      '.join(detail_parts) if detail_parts else None)


_VERSIONED_SCHEMA_DIAGNOSTICS_SKIP = frozenset({'naming.root_schema_title_matches_filename'})

def check_versioned_schema_diagnostics(run):
    all_diagnostics = sorted(SRC_TEST_DIAGNOSTICS.glob('*.py'))
    schema_skips    = {s: p.diagnostic_skip for p in PIPELINES.values() for s in p.schemas}

    schema_dirs = _schema_families()
    for schema_name in sorted(set(schema_skips) | set(schema_dirs)):
        skip        = _VERSIONED_SCHEMA_DIAGNOSTICS_SKIP | schema_skips.get(schema_name, frozenset())
        schema_dir  = schema_dirs.get(schema_name, SCHEMA_DIR.get(schema_name))
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
    _check_csv_pointers(join,
                        ('conv_path', 'session_path', 'api_path', 'mcp_path'),
                        {'conv_path':    SCHEMA_DIR['conversations'].parent,
                         'session_path': SCHEMA_DIR['session'],
                         'api_path':     SCHEMA_DIR['apiConversation'].parent,
                         'mcp_path':     RSC_SCHEMA},
                        fails)
    run('schema model_join.csv: all pointers valid', not fails,
        '\n    '.join(fails[:5]) if fails else None)


def check_model_join_versions(run):
    """Every versioned schema referenced in model_join.csv must be the latest version."""
    join = RSC_SCHEMA / 'model_join.csv'
    if not join.exists():
        return
    base_for = {
        'conv_path':    SCHEMA_DIR['conversations'].parent,
        'session_path': SCHEMA_DIR['session'],
        'api_path':     SCHEMA_DIR['apiConversation'].parent,
    }
    seen_dirs: dict[Path, str] = {}  # schema_dir → stem of version referenced
    with join.open() as fh:
        for row in csv.DictReader(fh):
            for col, base in base_for.items():
                ref = row.get(col, '').strip()
                if not ref:
                    continue
                file_part = ref.partition('#')[0]
                f = (base / file_part).resolve()
                if not re.match(r'v\d+', f.stem):
                    continue
                if f.parent not in seen_dirs:
                    seen_dirs[f.parent] = f.stem
    for schema_dir, used_stem in sorted(seen_dirs.items()):
        versions = _sorted_versions(schema_dir)
        if not versions:
            continue
        latest_stem = versions[-1].stem
        rel = schema_dir.relative_to(RSC_SCHEMA)
        run(f'model_join: {rel}: {used_stem}',
            used_stem == latest_stem,
            f'Update {used_stem}.json refs to {latest_stem}.json in {join.relative_to(REPO_ROOT)}' if used_stem != latest_stem else None)


def check_mcp_schema(run):
    """_reference/mcp.json must match the upstream schema at the raw URL in its description."""
    import hashlib, urllib.request
    mcp_path = RSC_SCHEMA / '_reference' / 'mcp.json'
    if not mcp_path.exists():
        run('mcp schema: _reference/mcp.json exists', False)
        return
    desc = json.loads(mcp_path.read_text()).get('description', '')
    m_url  = re.search(r'(https://raw\.githubusercontent\.com/\S+)', desc)
    m_hash = re.search(r'upstream SHA256:\s*([0-9a-f]{64})', desc)
    if not m_url or not m_hash:
        run('mcp schema: description has raw URL and upstream SHA256', False,
            'Add raw URL and "upstream SHA256: <hex>" to the description field in _reference/mcp.json')
        return
    raw_url     = m_url.group(1)
    stored_hash = m_hash.group(1)
    try:
        with urllib.request.urlopen(raw_url, timeout=15) as resp:
            live_hash = hashlib.sha256(resp.read()).hexdigest()
        run('mcp schema: up to date',
            stored_hash == live_hash,
            f'upstream changed — re-fetch {raw_url} and update upstream SHA256 in _reference/mcp.json')
    except Exception as e:
        run('mcp schema: upstream reachable', False, f'{e}')



def check_xref(run):
    _, output = _call(SRC / 'test' / 'xref.py')
    summary = output.splitlines()[-1] if output else ''
    m = re.search(r'(\d+ missing-file, \d+ bad-pointer, \d+ self-only, \d+ unreferenced)', summary)
    actual = m.group(1) if m else ''
    m_bad  = re.search(r'(\d+) bad-pointer', actual)
    bad    = int(m_bad.group(1)) if m_bad else 0

    score_file = SRC / 'test' / 'xref_expected_score'
    expected   = score_file.read_text().strip()

    run('xref: no bad pointers', bad == 0, summary if bad else None)
    run(f'xref: {actual}', actual == expected,
        f'expected: {expected}  →  consider updating {score_file.relative_to(REPO_ROOT)}'
        if actual != expected else None)


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true',
                    help='Run all fix commands and stage results with git add -u')
    args = ap.parse_args()

    results = []
    # The report splits by DETERMINISM, mirroring the tiers: code+schema output is
    # identical on any clone and becomes the COMMITTED src/test/pre_commit.log; the
    # data tier describes THIS MACHINE's data (uuids, batch names, home-dir-derived
    # paths) and must never enter a committed artifact — it goes to the terminal and
    # to logs/src/test/pre_commit.log (machine-facing, like the serve daemon's log).
    committed_buffer = io.StringIO()   # code + schema tiers
    machine_buffer   = io.StringIO()   # data tier

    def run(label, passed, detail=None):
        results.append((label, passed, detail))
        mark = '✓' if passed else '✗'
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
              f'{pipeline.gen.relative_to(REPO_ROOT)}/ empty)')

    try:
        run_section(check_required_files, tier='code')
        run_section(check_xref, tier='code')

        run_section(check_root_schema_diagnostics, tier='schema')

        run_section(check_schema_validity, tier='schema')
        run_section(check_schema_changelogs, tier='schema')

        run_section(check_versioned_schema_diagnostics, tier='schema')
        run_section(check_schema_join, tier='schema')
        run_section(check_model_join_versions, tier='schema')
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

    score_file = SRC / 'test' / 'pre_commit_expected_score'
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
                           got == tot,
                           'advisory — a fact about this machine\'s data, not the code; '
                           'remedies are printed beside each ✗ in the data tier above'
                           if got != tot else None))

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
    # any clone; this script writes it to src/test/pre_commit.log itself) and the
    # FULL report (adds the machine-local data tier — printed to stdout and written
    # to logs/src/test/pre_commit.log, run-facing like the serve daemon's log).

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

    def _render(committed_only: bool):
        """Render one report variant; returns (text, runnable fix lines)."""
        idxs  = [i for i in range(len(results)) if not committed_only or _in_committed(i)]
        fails = [(results[i][0], results[i][2]) for i in idxs if not results[i][1]]
        fail_sections = list(dict.fromkeys(sections[i] for i in idxs if not results[i][1]))
        out = io.StringIO()

        data_got, data_tot = tier_counts.get('data', [0, 0])
        data_note = ('data: machine-local' if committed_only else
                     'data: skipped' if data_tot == 0 else f'data: {data_got}/{data_tot}')
        if fails:
            out.write(f'`src/test/pre_commit.py`: {det} ({data_note}; failures in {len(fail_sections)} sections)\n')
        else:
            out.write(f'pre_commit.py: {det} ({data_note})\n')

        out.write('\n')
        out.write(committed_buffer.getvalue())
        if not committed_only:
            out.write(machine_buffer.getvalue())

        name = 'check_score'
        out.write(f'\n── {name} {"─" * (74 - len(name))}\n')
        for label, ok, detail in score_rows:
            if committed_only and label.startswith('score[data]'):
                out.write('  – score[data]: machine-local — reported on the terminal '
                          'and in logs/src/test/pre_commit.log, never committed\n')
                continue
            out.write(f'  {"✓" if ok else "✗"} {label}' +
                      (f'\n      {detail}\n' if not ok and detail else '\n'))

        lines: list[tuple[list[str], str | None, list[str]]] = []
        if fails:
            counts = {sec: sum(1 for i in idxs if not results[i][1] and sections[i] == sec)
                      for sec in fail_sections}
            out.write(f'Failed sections ({len(fail_sections)}):\n')
            for sec in fail_sections:
                out.write(f'  {sec} ({counts[sec]})\n')
            out.write('\n')
            hints = [h for h in fix_hints
                     if not committed_only or fix_tier.get(h) != 'data']
            lines = _fix_lines(fails, hints)
            if lines:
                out.write('\nTo fix:\n')
                for ps, cmd, gs in lines:
                    for p in ps[:3]:
                        out.write(f'  ✗ {p}\n')
                    if len(ps) > 3:
                        out.write(f'  ✗ … and {len(ps) - 3} more like these\n')
                    if cmd is not None:
                        out.write(f'    {cmd}\n')
                    for g in gs:
                        out.write(f'      ↳ {g}\n')
                out.write('\n')
                out.write('  (or run with --fix to apply and stage automatically)\n')
        return out.getvalue(), lines

    committed_text, _         = _render(committed_only=True)
    full_text, full_fix_lines = _render(committed_only=False)

    (SRC / 'test' / 'pre_commit.log').write_text(committed_text)
    machine_log = REPO_ROOT / 'logs' / 'src' / 'test' / 'pre_commit.log'
    machine_log.parent.mkdir(parents=True, exist_ok=True)
    machine_log.write_text(full_text)

    print(full_text, end='')

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
        subprocess.run(['git', 'add', '-u'], cwd=REPO_ROOT)
        print('Staged with git add -u — re-run pre_commit.sh to verify.')

    # The data tier is machine-local ("not recorded"): a stale capture on this
    # machine is a fact about its data, not about the change being committed.
    # Data failures are reported in full above but only code/schema/score
    # failures veto the exit status — otherwise local data drift fails every
    # run, including on trunk where the hook's veto is strict (the hook's
    # branch-awareness solves feature branches; this solves the tier).
    gating = [i for i, (_, p, _) in enumerate(results) if not p and tiers[i] != 'data']
    sys.exit(1 if gating else 0)


if __name__ == '__main__':
    main()
