#!/usr/bin/env python
"""
xref.py — the cross-reference table of the repo. `xref` is a NOUN: the table. A bare
invocation shows its status (the committed table's tallies) and writes nothing; the
`check` verb rebuilds it, writes rsc/test/xref.csv, and reports. Every non-generated
file is scanned for references to other repo files, one CSV row per reference (columns
are the header of rsc/test/xref.csv; exists=N marks a stale reference).

    yoga test                            # status, including this table
    yoga test xref                       # rebuild + write + report
    awk -F, '$5=="N"' rsc/test/xref.csv    # the stale references
"""

import argparse
import ast
import csv
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/ — modules both tiers import
from argparse_help import enrich  # noqa: E402

REPO_ROOT = Path(__file__).parents[3]

# The git-ignored lifecycle roots to skip — parsed from the committed .gitignore
# (its one authority) rather than restated by hand. .gitignore is a committed source,
# so this stays machine-invariant (L2) — unlike iterdir(); see the REF_EXTS note below.
# A hand-kept copy is a second source, free to go on naming a root the .gitignore
# line has retired. __pycache__ stays explicit: a universal
# Python artifact, always skipped whatever .gitignore says, not a repo lifecycle root.
def _gitignored_roots() -> frozenset:
    roots = set()
    for line in (REPO_ROOT / '.gitignore').read_text().splitlines():
        m = re.fullmatch(r'/([^/]+)/?', line.strip())  # anchored top-level dir: /tmp/cache/, /output
        if m:
            roots.add(m.group(1))
    return frozenset(roots)

_IGNORED_ROOTS = _gitignored_roots()
SKIP_DIRS  = _IGNORED_ROOTS | {'__pycache__'}
# Generated output files that live in src/test/ — skip to avoid scanning their contents
SKIP_FILES = {'rsc/test/run.log', 'rsc/test/xref.csv'}

# Python stdlib and known third-party modules — not repo files
# A module name that is not a repo path — derived, both halves.
#
# The stdlib half comes from the INTERPRETER (sys.stdlib_module_names): the hand-written list
# it replaced omitted `concurrent`, so a dotted stdlib import was read as a pointer into the
# repo and reported as a missing file. (Written without spelling that path, because this
# scanner reads comments too — the first draft of this comment was the next missing pointer.)
#
# The third-party half comes from the DECLARATION, src/requirements.txt. Its hand-written
# predecessor listed six names where two are declared: requests, yaml, toml and pytest were
# neither declared nor installed, so `import yaml` would have passed this check as
# "third party" and then failed at runtime — the checker complicit in the break.
#
# requirements name DISTRIBUTIONS, imports name MODULES, and they differ (PyYAML provides
# yaml), so the correspondence is read from installed metadata rather than assumed. Falling
# back to the declared names keeps the scan working on a machine whose venv is not built yet
# — a state `yoga prerequisites` reports.
def _declared_modules() -> set[str]:
    req = REPO_ROOT / 'src' / 'requirements.txt'
    if not req.is_file():
        return set()
    declared = {re.split(r'[=<>\[;]', line, maxsplit=1)[0].strip().lower()
                for line in req.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')}
    try:
        from importlib.metadata import packages_distributions
        provided = {m for m, dists in packages_distributions().items()
                    if any(d.lower() in declared for d in dists)}
        return provided or declared
    except Exception:
        return declared


STDLIB_MODULES = sys.stdlib_module_names | _declared_modules()

# The DECLARED lifecycle roots, statically — never derived from the live
# filesystem. Deriving them from iterdir() made the committed xref.csv depend
# on which git-ignored dirs happen to exist at run time: a machine whose gate has
# already created a log root swallows the whole token and skips it, while a fresh
# worktree without that root matches the same text from `src/` inward and emits a
# row — two machines, two artifacts, one byte-identical tree. Freshness is the
# wrong invariant for a committed
# artifact; machine-invariance is the right one.
# The artifact extensions xref recognises — ONE authority: every extractor's
# token pattern and looks_like_repo_path derive from it. Restated at each site, the
# list drifts a vintage per site. (The subprocess/exec
# scan stays narrower on purpose: only executables run.)
REF_EXTS = ('py', 'sh', 'json', 'md', 'html', 'g4', 'graphql', 'txt', 'csv', 'log')
_DOT_EXTS = tuple(f'.{e}' for e in REF_EXTS)
_TOKEN = r'[\w./\-]+\.(?:' + '|'.join(REF_EXTS) + r')'
PATH_TOKEN_RE = re.compile(_TOKEN)
DOTSLASH_TOKEN_RE = re.compile(r'(?<![./\w])\./' + _TOKEN)

REPO_PREFIXES = tuple(f'{d}/' for d in sorted(_IGNORED_ROOTS | {'rsc', 'src'}))
# Regex alternation of bare directory names, e.g. 'cache|rsc|src'
PREFIXES_RE = '|'.join(re.escape(p.rstrip('/')) for p in REPO_PREFIXES)

# ── helpers ───────────────────────────────────────────────────────────────────

def _gitignored(rels: list[str]) -> set[str]:
    """The subset of paths .gitignore matches, asked of git itself — the backstop
    for anything the anchored top-level parse above cannot see. Gitignored files
    are machine-local by definition and must not enter the scannable set: the
    committed expected counts are machine-invariant (L2), and a file that exists
    on some machines only would skew them per machine. This once had to catch a
    gitignored file living INSIDE the committed tree (the machine binding, then a
    self.txt under rsc/machine/); since 2026-07-17 that binding is rooted, so the
    parse catches it by its own rule and nothing in the tree is an exception."""
    import subprocess
    r = subprocess.run(['git', '-C', str(REPO_ROOT), 'check-ignore', '--stdin'],
                       input='\n'.join(rels), capture_output=True, text=True)
    return set(r.stdout.splitlines())


def repo_files() -> list[Path]:
    """Return all scannable source files in the repo."""
    result = []
    for f in REPO_ROOT.rglob('*'):
        if not f.is_file():
            continue
        rel = f.relative_to(REPO_ROOT)
        if str(rel) in SKIP_FILES:
            continue
        parts = rel.parts
        if any(part in SKIP_DIRS or part.startswith('.') for part in parts):
            continue
        result.append(f)
    ignored = _gitignored([str(f.relative_to(REPO_ROOT)) for f in result])
    return sorted(f for f in result if str(f.relative_to(REPO_ROOT)) not in ignored)


def looks_like_repo_path(s: str) -> bool:
    """True if s looks like a repo-relative file path worth recording."""
    s = s.strip()
    if not s or ' ' in s or s.startswith('http') or s.startswith('/'):
        return False
    if s.startswith('~'):
        return False  # home-relative path, outside the repo
    bare = s.lstrip('./')
    if any(bare.startswith(d + '/') or bare == d for d in SKIP_DIRS):
        return False  # reference into a skipped directory
    if '<' in s or '…' in s:
        return False  # a placeholder-bearing path is a format QUOTATION, not a reference
    lead = re.match(r'^(?:\.\./)+', s)
    body = s[lead.end():] if lead else s
    if '/../' in body or body.endswith('/..'):
        return False  # interior parent hops — never a link shape the repo writes
    if lead:
        # leading ../ hops from a nested file are ordinary intra-repo relative
        # links — resolve() checks them against the referring file and rejects
        # true escapes. Rejecting them wholesale lets a born-broken ../ext/ link
        # in a schema CHANGELOG sail through unflagged.
        base = body.split('#')[0]
        return base.endswith(_DOT_EXTS) or (base.endswith('/') and '/' in base.rstrip('/'))
    # Explicit relative reference ./name.ext or ./name.ext#fragment
    if s.startswith('./'):
        base = s.split('#')[0]  # strip JSON Pointer fragment before extension check
        if base.endswith(_DOT_EXTS):
            return True
        s = s[2:]
    # Must be more than a bare fragment like "tmp/cache/data-" with no filename
    if not Path(s).suffix and not any(s.rstrip('/') == p.rstrip('/') for p in REPO_PREFIXES):
        has_name = bool(Path(s).name) and len(Path(s).name) > 3
        if not has_name:
            return False
    return any(s.startswith(p) for p in REPO_PREFIXES) or (
        '/' in s and not s.startswith('#') and len(s) > 6
        and s[0].isalpha() and s.endswith(_DOT_EXTS)
    )


def resolve(referred: str, referring: Path) -> tuple[str, str]:
    """Return (canonical_ref_with_fragment, exists_flag).

    For paths with a JSON Pointer fragment (file.json#/a/b/c), checks both
    that the file exists and that the pointer navigates successfully within it.
    """
    s = referred.strip()

    # Split off JSON Pointer fragment; strip trailing slash from path
    file_part, _, pointer = s.partition('#')
    file_part = file_part.rstrip('/')

    def check_pointer(f: Path) -> bool:
        if not pointer or not f.suffix == '.json':
            return True  # no fragment to check, or not JSON
        try:
            doc = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        node = doc
        for tok in pointer.lstrip('/').split('/'):
            tok = tok.replace('~1', '/').replace('~0', '~')  # RFC 6901 escapes
            try:
                node = node[tok] if isinstance(node, dict) else node[int(tok)]
            except (KeyError, IndexError, ValueError, TypeError):
                return False
        return True

    def canon(f: Path) -> str:
        rel = str(f.resolve().relative_to(REPO_ROOT))
        return f'{rel}#{pointer}' if pointer else rel

    bare = file_part.lstrip('./')
    candidate = REPO_ROOT / bare
    if candidate.exists():
        try:
            exists = check_pointer(candidate)
            return canon(candidate), 'Y' if exists else 'N'
        except ValueError:
            pass
    candidate2 = (referring.parent / file_part).resolve()
    if candidate2.exists():
        try:
            candidate2.relative_to(REPO_ROOT)
            exists = check_pointer(candidate2)
            return canon(candidate2), 'Y' if exists else 'N'
        except ValueError:
            pass
    return (bare or s), 'N'


def emit(rows: list, referring: Path, lineno: int, ref_type: str,
         referred: str, line_text: str) -> None:
    canonical, exists = resolve(referred, referring)
    rows.append([
        str(referring.relative_to(REPO_ROOT)),
        lineno,
        ref_type,
        canonical,
        exists,
        line_text[:120],
    ])


# ── per-file-type extractors ──────────────────────────────────────────────────

def extract_python(f: Path, rows: list) -> None:
    try:
        src = f.read_text(errors='replace')
    except OSError:
        return
    lines = src.splitlines()

    # AST pass: imports and string literals
    try:
        tree = ast.parse(src, filename=str(f))
    except SyntaxError:
        tree = None

    if tree:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split('.')[0]
                    if top in STDLIB_MODULES:
                        continue
                    name = alias.name.replace('.', '/') + '.py'
                    if looks_like_repo_path(name):
                        emit(rows, f, node.lineno, 'import', name,
                             lines[node.lineno - 1].strip())
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split('.')[0]
                    if top in STDLIB_MODULES:
                        continue
                    name = node.module.replace('.', '/') + '.py'
                    if looks_like_repo_path(name):
                        emit(rows, f, node.lineno, 'import', name,
                             lines[node.lineno - 1].strip())
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
                lineno_base = getattr(node, 'lineno', 0)
                if '\n' in s:
                    # Multi-line string (docstring): scan each line for paths
                    for j, subline in enumerate(s.splitlines()):
                        for m in PATH_TOKEN_RE.finditer(subline):
                            candidate = m.group()
                            if looks_like_repo_path(candidate):
                                emit(rows, f, lineno_base + j, 'comment',
                                     candidate, subline.strip())
                elif looks_like_repo_path(s):
                    ltext = lines[lineno_base - 1].strip() if lineno_base else ''
                    emit(rows, f, lineno_base, 'path_str', s, ltext)
                elif ' ' in s and s.split() and looks_like_repo_path(s.split()[0]):
                    # String starting with a repo path followed by flags, e.g. validate_cmd values
                    ltext = lines[lineno_base - 1].strip() if lineno_base else ''
                    emit(rows, f, lineno_base, 'path_str', s.split()[0], ltext)

    # Line pass: comments and subprocess/exec calls
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            for match in PATH_TOKEN_RE.finditer(stripped):
                s = match.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)
            continue
        # subprocess.run / os.system / exec calls containing a repo path
        if re.search(r'\bsubprocess\b|\bos\.system\b|\bos\.exec', line):
            for match in re.finditer(r'["\']([^"\']+\.(?:py|sh))["\']', line):
                s = match.group(1)
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'call', s, stripped)


def shell_vars(f: Path) -> dict[str, Path]:
    """Parse top-of-script variable definitions into repo-relative Paths.

    Handles the three patterns found in this repo's shell scripts:
      VAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  → script's own dir
      VAR="$(cd "$OTHER/subpath" && pwd)"                  → resolve from OTHER
      VAR="$OTHER/suffix"                                  → concat from OTHER
    """
    env: dict[str, Path] = {}
    try:
        src = f.read_text(errors='replace')
    except OSError:
        return env

    script_dir = f.parent.resolve().relative_to(REPO_ROOT)

    for line in src.splitlines():
        m = re.match(r'^(\w+)="(.+)"$', line.strip())
        if not m:
            continue
        var, val = m.group(1), m.group(2)

        # Pattern 1: BASH_SOURCE[0] — the script's own directory, minus any
        # trailing /.. hops (src/main/cli/pipeline/pipeline.sh anchors REPO_ROOT at its parent)
        if 'BASH_SOURCE' in val or 'dirname' in val:
            d = script_dir
            for _ in range(val.count('/..')):
                d = d.parent
            env[var] = d
            continue

        # Pattern 2: $(cd "$OTHER/subpath" && pwd) — resolve path
        cd_m = re.match(r'\$\(cd "\$(\w+)(/[^"]+)?" && pwd\)', val)
        if cd_m:
            base_var, suffix = cd_m.group(1), cd_m.group(2) or ''
            if base_var in env:
                resolved = (REPO_ROOT / env[base_var] / suffix.lstrip('/')).resolve()
                try:
                    env[var] = resolved.relative_to(REPO_ROOT)
                except ValueError:
                    pass
            continue

        # Pattern 3: $OTHER/suffix — string concat
        concat_m = re.match(r'\$(\w+)/(.+)', val)
        if concat_m:
            base_var, suffix = concat_m.group(1), concat_m.group(2)
            if base_var in env:
                env[var] = Path(str(env[base_var]) + '/' + suffix)

    return env


def extract_shell(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return

    env = shell_vars(f)

    def substitute(s: str) -> str:
        """Replace $VAR prefixes using the parsed variable dict."""
        m = re.match(r'^\$(\w+)(.*)', s)
        if m and m.group(1) in env:
            return str(env[m.group(1)]) + m.group(2)
        return s

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            for match in PATH_TOKEN_RE.finditer(stripped):
                s = match.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)
            continue

        is_call_line = bool(re.search(r'\bpython\b|\bsource\b|\bbash\b|\bsh\b', line))

        for match in re.finditer(r'"(\$\w+[^"]*)"'
                                  r"|'(\$\w+[^']*)'", line):
            raw = match.group(1) or match.group(2)
            s = substitute(raw)
            if '$' in s or not looks_like_repo_path(s):
                continue
            at_start = line.strip().startswith(match.group(0))
            ref_type = 'call' if (is_call_line or at_start) else 'path_str'
            emit(rows, f, i, ref_type, s, stripped)


def extract_json(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # $ref and $schema
        for match in re.finditer(r'"\$(ref|schema)"\s*:\s*"([^"]+)"', stripped):
            key, val = match.group(1), match.group(2)
            ref_type = '$ref' if key == 'ref' else '$schema'
            # Skip intra-file refs and canonical schema URIs (not repo paths)
            if val.startswith('#') or val.startswith('http'):
                continue
            emit(rows, f, i, ref_type, val, stripped)
        # Any quoted string (key or value) that looks like a repo path
        for match in re.finditer(r'"([^"]+)"', stripped):
            s = match.group(1)
            if looks_like_repo_path(s):
                emit(rows, f, i, 'path_str', s, stripped)


def extract_markdown(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    in_frontmatter = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if i == 1 and stripped == '---':
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == '---':
                in_frontmatter = False
                continue
            # YAML key: value — treat value as a path if it has a known extension
            m = re.match(r'^\w[\w_]*:\s+(\S+)$', stripped)
            if m:
                val = m.group(1).strip('"\'')
                if val.endswith(_DOT_EXTS):
                    emit(rows, f, i, 'doc', val, stripped)
            continue
        # Markdown links [text](path)
        for match in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', stripped):
            target = match.group(2)
            if target.startswith('http') or target.startswith('#'):
                continue
            if looks_like_repo_path(target):
                emit(rows, f, i, 'doc', target, stripped)
        # Inline code `path`
        for match in re.finditer(r'`([^`]+)`', stripped):
            s = match.group(1)
            if looks_like_repo_path(s):
                emit(rows, f, i, 'doc', s, stripped)
        # Explicit ./path.ext references (e.g. in fenced code blocks).
        # Negative lookbehind prevents matching the inner ./ in ./../foo.
        for match in DOTSLASH_TOKEN_RE.finditer(stripped):
            s = match.group()
            if looks_like_repo_path(s):
                emit(rows, f, i, 'doc', s, stripped)
        # Bare path-like strings in code blocks / text (must not end with a hyphen)
        for match in re.finditer(rf'\b((?:{PREFIXES_RE})/[\w./\-]+)(?![\-])\b', stripped):
            s = match.group(1)
            if looks_like_repo_path(s):
                emit(rows, f, i, 'doc', s, stripped)


def extract_html(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # HTML comments
        for match in re.finditer(r'<!--(.*?)-->', stripped):
            for m2 in PATH_TOKEN_RE.finditer(match.group(1)):
                s = m2.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)
        # JS string literals referencing repo files
        for match in re.finditer(rf"['\"]([^'\"]*(?:{PREFIXES_RE})/[^'\"]*)['\"]", stripped):
            s = match.group(1)
            if looks_like_repo_path(s):
                emit(rows, f, i, 'path_str', s, stripped)


def extract_csv(f: Path, rows: list) -> None:
    try:
        reader = csv.reader(f.open())
        next(reader, [])  # skip header row
        for i, record in enumerate(reader, 2):  # 1-based, row 1 is header
            for cell in record:
                cell = cell.strip()
                if looks_like_repo_path(cell):
                    emit(rows, f, i, 'path_str', cell, ','.join(record)[:120])
    except OSError:
        return


def extract_g4(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('//'):
            for match in PATH_TOKEN_RE.finditer(stripped):
                s = match.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)


# ── dispatch ──────────────────────────────────────────────────────────────────

EXTRACTORS = {
    '.py':      extract_python,
    '.sh':      extract_shell,
    '.command': extract_shell,  # Terminal-hosted shell — same language, Finder-executable name
    '.json':    extract_json,
    '.md':      extract_markdown,
    '.html':    extract_html,
    '.g4':      extract_g4,
    '.csv':     extract_csv,
}


DEFAULT_OUT = REPO_ROOT / 'rsc' / 'test' / 'xref.csv'
HEADER = ['referring_file', 'line', 'ref_type', 'referred_file', 'exists', 'line_text']


def build_table() -> list[list]:
    """Scan the repo and return the deduplicated, outer-joined reference rows."""
    rows: list[list] = []
    for f in repo_files():
        extractor = EXTRACTORS.get(f.suffix.lower())
        if extractor:
            extractor(f, rows)

    # Deduplicate (same referring + line + type + referred)
    seen: set[tuple] = set()
    deduped: list[list] = []
    for row in rows:
        key = (row[0], row[1], row[2], row[3])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    # Full outer join: add rows for repo files never appearing as referred_file,
    # and for files only referenced from themselves.
    all_files = {str(f.relative_to(REPO_ROOT)) for f in repo_files()}
    externally_referenced: set[str] = set()
    for row in deduped:
        referring, referred = row[0], row[3]
        if referring and referred:
            referred_base = referred.split('#')[0]
            if referred_base != referring:
                externally_referenced.add(referred_base)
    for fp in sorted(all_files):
        if fp not in externally_referenced:
            ref_type = 'self_only' if any(
                row[0] == fp and row[3].split('#')[0] == fp
                for row in deduped
            ) else ''
            deduped.append(['', '', ref_type, fp, 'Y', ''])
    return deduped


@dataclass(frozen=True)
class XrefCounts:
    total:          int
    live:           int
    stale_file:     int
    stale_pointer:  int
    self_only:      int
    unreferenced:   int


def count(rows: list[list]) -> XrefCounts:
    """Pure: the table's row classes, tallied — the comparable shape both the
    gate's check_xref and the standalone `yoga test xref` report from."""
    stale_file    = sum(1 for r in rows if r[0] and r[4] == 'N' and '#' not in r[3])
    stale_pointer = sum(1 for r in rows if r[0] and r[4] == 'N' and '#' in r[3])
    self_only     = sum(1 for r in rows if not r[0] and r[2] == 'self_only')
    unreferenced  = sum(1 for r in rows if not r[0] and r[2] != 'self_only')
    live          = len(rows) - stale_file - stale_pointer - self_only - unreferenced
    return XrefCounts(len(rows), live, stale_file, stale_pointer, self_only, unreferenced)


def score_line(counts: XrefCounts) -> str:
    """The fragment comparable against rsc/test/xref_expected_score — row counts
    only, independent of where the table is being reported from."""
    return (f'{counts.stale_file} missing-file, {counts.stale_pointer} bad-pointer, '
            f'{counts.self_only} self-only, {counts.unreferenced} unreferenced')


def summary_line(counts: XrefCounts, where) -> str:
    return f'{counts.total} rows: {counts.live} live, {score_line(counts)} → {where}'


def render_csv(rows: list[list]) -> str:
    """Pure: rows -> the committed table's bytes. No file IO — the caller decides
    whether and where to write. `check()` below writes directly for a standalone
    `yoga test xref`; the gate's check_xref hands the same rows to render, which
    owns the write to rsc/test/xref.csv there (#249's check/render/gate
    separation — a check computes, only render writes)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADER)
    writer.writerows(rows)
    return buf.getvalue()


def check(out: Path) -> None:
    """The verb: rebuild the table, WRITE it, and report. The only writing path in
    this module; idempotent (L1) — a re-run reproduces the same bytes."""
    rows = build_table()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_csv(rows), newline='')
    print(summary_line(count(rows), out.relative_to(REPO_ROOT)))


def status() -> None:
    """The bare-noun default: summarise the committed table, write nothing."""
    if not DEFAULT_OUT.exists():
        print(f'{DEFAULT_OUT.relative_to(REPO_ROOT)} not present — `yoga test xref` builds it')
        return
    with DEFAULT_OUT.open(newline='') as fh:
        rows = list(csv.reader(fh))[1:]   # drop header
    print(summary_line(count(rows), DEFAULT_OUT.relative_to(REPO_ROOT)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='verb')
    sub.add_parser('check')
    enrich(parser, 'xref')
    args = parser.parse_args()
    # bare noun → status (read the committed table); only `check` rebuilds and writes
    check(DEFAULT_OUT) if args.verb == 'check' else status()


if __name__ == '__main__':
    main()
