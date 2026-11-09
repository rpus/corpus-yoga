"""
gate.py - the dev gate's shared vocabulary (issues/1023): the repository's layout, the
helpers its checks share, and `check`, the one declaration of a check - its tier, the
names it reports and the paths it reads, beside its function in its subject's module
under src/test/dev/check/. The runner, src/test/dev/run.py, derives its sections, its
replay subjects and its expected names from these declarations.
"""
import ast
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The gate compares rendered BYTES - argparse help against the generated
# parser, run output against committed expectations - and color is context,
# not content: python 3.14 colorizes argparse help by stream and environment,
# so an interactive run's in-process render diverged from the captured
# subprocess's (cli.verb_help_answered, 9/16 red on a checkout, 2026-08-13).
# The whole run pins color off, for itself and every child it spawns.
os.environ['PYTHON_COLORS'] = '0'
os.environ['NO_COLOR'] = '1'
os.environ.pop('FORCE_COLOR', None)
# Same law for width: argparse wraps help to the terminal, and a tty-attached
# run (the pre-commit hook) would render the in-process expectation at the
# terminal's width while the captured subprocess renders at the 80 fallback.
os.environ['COLUMNS'] = '80'

# ── Repo layout ───────────────────────────────────────────────────────────────
SELF = 'src/test/dev/gate.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
INPUT                    = REPO_ROOT / 'data' / 'input'
CACHE                    = REPO_ROOT / 'tmp' / 'cache'
RSC                      = REPO_ROOT / 'rsc'
SRC                      = REPO_ROOT / 'src'
RSC_SCHEMA               = RSC / 'schema'
RSC_MODEL                = RSC / 'model'
SRC_TEST_DIAGNOSTICS     = SRC / 'test' / 'dev' / 'diagnostics'
SRC_TEST_REPAIRS         = SRC / 'test' / 'dev' / 'repairs'

# The per-check report is an ARTIFACT beside the act's record (issues/708), IMMUTABLE (issues/370):
# one stamped, colon-free file per run under the verb directory, <stamp>.report, never
# rewritten; a same-second twin gains a numeric suffix instead of overwriting. The record
# itself, <stamp>.log, is the launcher's tee of the whole verb, and the stamp is the
# launcher's where it ran the verb, so the pair share it. The committed surface names
# only the stable directory — a stamp is machine-varying and may not enter it (L2).
sys.path.insert(0, str(SRC / 'main'))  # tier: the act's stamp, one reading (issues/912)
import tier  # noqa: E402
import facts  # noqa: E402 - the one printer: the report's stages as facts (issues/755)
_REPORT_STAMP = tier.stamp_of('test run')
REPORT = REPO_ROOT / 'tmp' / 'logs' / 'test' / 'run' / f'{_REPORT_STAMP}.report'
_twin = 2
while REPORT.exists():
    REPORT = REPORT.with_name(f'{_REPORT_STAMP}-{_twin}.report')
    _twin += 1
REPORT_REL = str(REPORT.relative_to(REPO_ROOT))
CLI                      = SRC / 'main' / 'cli'
# What a sentence does instead of the marks the printer cannot leave plain: the one remedy
# both the declarations' prose check (pull/797) and the wording check (issues/909) print, so that an
# edit made to pass them keeps the sentence's anchor.
PLAIN_PHRASE_REMEDY = ('a pair is a fact of its own beneath, or the phrase says it without the colon; an em dash is written '
                         "' - '; a hash is YAML's comment, a URL's fragment and a shell's, so an anchor is written as the forge's "
                         'path segment, issues/N or pull/N, and is never dropped')

sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — shared modules live at its root

sys.path.insert(0, str(SRC / 'main'))  # markdown_projection owns the format, both directions
from markdown_projection import turn_seq  # noqa: E402
from send import SWITCH as SEND_SWITCH, may_send  # noqa: E402 — the one reading of the send switch

sys.path.insert(0, str(CLI))  # the corpus-yoga CLI cluster (dispatch + shared machinery)
# A CLI-native command lives in its own directory (issues/307), so its module sits beside
# the declarations that name it: import it from there, not from the cluster root.
sys.path.insert(0, str(CLI / 'cache'))
sys.path.insert(0, str(CLI / 'completions'))
import cli  # noqa: E402 — the CLI table machinery (check_cli_surface)
import completions as cli_completions  # noqa: E402 — and `corpus-yoga completions` here
import offer as cli_offer  # noqa: E402 - what zsh evaluates when tab is pressed
import cache_io  # noqa: E402 — the declared tmp/cache/ IO registry (check_cache_io)
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main' / 'model'))
sys.path.insert(0, str(SRC / 'main' / 'mcp'))  # the house mcp factoring (check_mcp_factoring)
import mcp_factoring  # noqa: E402
import mcp_extraction  # noqa: E402  (the schema.ts reader, through the generated parser)
import mcp_face  # noqa: E402  (the consumer and producer faces, issues/605)
import provider  # noqa: E402  (src/main - the provider registry, check_schema_layout)
from member import is_member, members  # noqa: E402  (src/main - the one reading of membership by placement)
sys.path.insert(0, str(SRC / 'main' / 'grammar'))  # the generated parsers (check_grammar)
import grammar as grammar_module  # noqa: E402
from latest import latest_file, lineages  # noqa: E402  (src/main - the one reading of the latest)
import frontier  # noqa: E402 — subject recency + vN.log reading, shared with bare `corpus-yoga model` (issues/373)

sys.path.insert(0, str(SRC / 'main' / 'pipeline' / 'chat-export'))  # the shared deposit rule (check_accumulate_contract)
import accumulate as _accumulate  # noqa: E402 — the CALCULUS accumulate operation (issues/22)

sys.path.insert(0, str(SRC / 'main' / 'cli' / 'indexing'))  # index curation machinery
sys.path.insert(0, str(SRC / 'main' / 'model'))  # model.json disposal queue
import model_curation  # noqa: E402 — the model.json disposal queue (issues/19)

import xref  # the cross-reference table (check_xref) — a same-directory sibling, already
             # on sys.path[0] when this script runs, so no path insert is needed

# ── Pipeline model ────────────────────────────────────────────────────────────

PIPELINE_ROOT = SRC / 'main' / 'pipeline'

@dataclass
class Pipeline:
    name:             str
    schemas:          list[str]
    input:            Path
    input_glob:       str
    subject_depth:    int
    extra_input_glob: str
    providers:        list[str]
    diagnostic_skip:  dict[str, frozenset[str]]

    @property
    def changelog(self) -> Path:
        # The FIRST schema is the one whose CHANGELOG anchors the format history.
        return RSC_SCHEMA / 'pipeline' / self.name / self.schemas[0] / 'CHANGELOG.md'

    @property
    def cache_output(self) -> Path:
        return REPO_ROOT / cache_io.path_for(self.name)

    @property
    def fix_item_cmd(self) -> str:
        # Per-item remedy command; takes the pipeline's TOP-LEVEL data/input/ entry (see _fix_item_cmd).
        return f'corpus-yoga pipeline run {self.name}'


def _load_pipeline(directory: Path) -> Pipeline:
    facts = json.loads((directory / 'pipeline.json').read_text())
    return Pipeline(
        name             = directory.name,
        schemas          = facts['schemas'],
        input            = REPO_ROOT / facts['input'],
        input_glob       = facts.get('input_glob', ''),
        subject_depth    = facts['subject_depth'],
        extra_input_glob = facts.get('extra_input_glob', ''),
        providers        = sorted(facts.get('provider', {})),
        diagnostic_skip  = {family: frozenset(skips) for family, skips in facts['diagnostic_skip'].items()},
    )


# Membership is placement (issues/327): a pipeline is a subdirectory of src/main/pipeline/, and
# its facts are its own pipeline.json — the same listing `corpus-yoga pipeline` serves, so the
# gate's list and the CLI's cannot drift apart. A member without a declaration stays OUT
# of the dict but IN _PIPELINE_UNDECLARED, so check_pipeline_declarations can name it
# instead of the import dying on it.
_PIPELINE_DIRS = members(PIPELINE_ROOT)
_PIPELINE_UNDECLARED = [d.name for d in _PIPELINE_DIRS if not (d / 'pipeline.json').is_file()]
PIPELINES: dict[str, Pipeline] = {
    d.name: _load_pipeline(d)
    for d in _PIPELINE_DIRS if (d / 'pipeline.json').is_file()
}



def _leaf(subject: str) -> str:
    """Check-label form of a subject: the leaf (uuid/name) only. Depth-2 subjects are
    '<project-slug> / <uuid>' internally (the slug is needed to reconstruct paths), but
    labels use just the uuid — uniform with the depth-1 pipelines, and the committed
    run.log then carries no machine-derived slugs (they embed the username)."""
    return subject.split(' / ')[-1]


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
                    latest = latest_file(f)
                    if not latest:
                        fails.append(f'row {i} {col}: no v*.json or lineage under: {file_part}')
                        continue
                    f = latest
                if pointer and f.suffix == '.json':
                    try:
                        doc = json.loads(f.read_text())
                    except json.JSONDecodeError:
                        fails.append(f'row {i} {col}: invalid JSON: {file_part}')
                        continue
                    if not _walk_pointer(doc, pointer):
                        fails.append(f'row {i} {col}: bad pointer: {ref}')


# ── Checks ────────────────────────────────────────────────────────────────────

def _machine_anchor() -> str:
    """The provenance line every machine-facing log opens with (issues/365): the Signature
    triad the commit hook stamps - the machine this checkout is bound to (or 'unbound':
    a worktree carries no binding), the provider and session that ran it where the
    environment declares one (issues/704) - the commit the tree stood at, and clean/dirty
    with the count."""
    from provider import signature
    def _git(*args):
        proc = subprocess.run(['git', '-C', str(REPO_ROOT), *args],
                              capture_output=True, text=True)
        return proc.stdout.strip()
    branch = _git('branch', '--show-current') or '(detached)'
    sha = _git('rev-parse', '--short', 'HEAD') or '(no git)'
    dirty_n = len([l for l in _git('status', '--porcelain').splitlines() if l])
    dirty = 'clean' if dirty_n == 0 else f'dirty ({dirty_n})'
    return f'{signature()} · {branch} @ {sha}, {dirty}'


def _schema_families() -> dict:
    """Every versioned schema family ON DISK ({address under rsc/schema: dir}) — the
    scope for all schema-tier per-family checks, found by walking for a directory that
    holds a v*.json, at any depth. Not derived from the pipelines' schemas lists:
    a family can exist outside any pipeline (markdownConversation is validated
    in-memory at projection time) and must still be checked."""
    return {d.relative_to(RSC_SCHEMA).as_posix(): d
            for d in sorted({v.parent for v in RSC_SCHEMA.rglob('v*.json')})}


def _cache_io_resolves(entry: str, commands: set[str]) -> bool:
    """A cache_io written_by/read_by entry resolves iff it is an `external:*` reader
    (exempt), a CANONICAL `corpus-yoga` invocation — `corpus-yoga <command> [<verb>]`, both
    resolved against the declaration tree — or a path (its first token) that
    exists in the repo. Two rules from the pull/109 review: the verb is checked
    (a cell naming `indexing candidates` read as clean after the verb became
    `list-candidates`), and `./corpus-yoga` is REJECTED, not tolerated — the cell is a
    name (one referent, one name, G14); the runnable `./` form is presentation,
    derived by `cache sync` at execution (L5). Tolerating both spellings is how
    the old cells dodged the command branch and resolved as the launcher file's
    path. Tokens after the verb (a pipeline name, a flag) are arguments, not
    resolution targets."""
    if entry.startswith('external:'):
        return True
    words = entry.split()
    if not words:
        return False
    if words[0].lstrip('./') == 'corpus-yoga':
        if words[0] != 'corpus-yoga' or len(words) < 2 or words[1] not in commands:
            return False
        verb = words[2] if len(words) > 2 and not words[2].startswith('-') else None
        return verb is None or verb in cli.subcommands_of(words[1])
    return (REPO_ROOT / words[0].lstrip('./')).exists()


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


def _read_committed_xref(path: Path) -> list[list]:
    """Rows in build_table()'s shape, read back from an already-committed
    rsc/test/xref.csv. Used only when check_xref replayed from the section cache
    (TREE unchanged, so the file is already at its fixpoint) and so never built a
    fresh table for render to write — the committed file IS this artifact's cache,
    so nothing needs duplicating into sections.json to serve render on a replay."""
    if not path.exists():
        return []
    with path.open(newline='') as fh:
        rows = list(csv.reader(fh))
    return rows[1:] if rows else []   # drop header



# ── Declarations ──────────────────────────────────────────────────────────────

DIAGNOSTIC_NAMES = tuple(p.stem for p in sorted(SRC_TEST_DIAGNOSTICS.glob('*.py')))   # each diagnostic reports under its own name
GATE_FILES = frozenset({SRC / 'test' / 'dev' / 'run.py', SRC / 'test' / 'dev' / 'gate.py',
                        *(SRC / 'test' / 'dev' / 'check').glob('*.py')})   # the gate's own sources, which hold its fixtures


@dataclass(frozen=True)
class Declared:
    """One check as its declaration states it: its function, its tier, the names it reports, the
    paths it reads ('TREE' for every file; None where it never replays), and whether it reads
    what every other check has cited, and so runs after them all."""
    fn: Any
    tier: str
    says: tuple[str, ...]
    on: Any = None
    after_all: bool = False

    @property
    def name(self) -> str:
        return self.fn.__name__


CHECKS: list[Declared] = []


def check(*, tier: str, says: tuple[str, ...], on: Any = None, after_all: bool = False):
    """Declare the function beneath as a check: one declaration, beside the function, that the
    runner's sections, replay subjects and expected names derive from."""
    def declared(fn):
        CHECKS.append(Declared(fn, tier, tuple(says), on, after_all))
        return fn
    return declared
