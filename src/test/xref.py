#!/usr/bin/env python
"""
xref.py — Cross-reference table for the repo.

Scans every non-generated file and extracts references to other repo files,
writing a CSV with one row per reference.

Usage:
    python src/test/xref.py [--out <path>]

    Default output: gen/xref.csv

Output columns
──────────────
    referring_file   Repo-relative path of the file containing the reference.
    line             Line number (1-based).
    ref_type         How the reference appears:
                       import      Python import / from-import
                       call        Shell execution or Python subprocess/exec call
                       path_str    String literal containing a repo-relative path
                       $ref        JSON Schema $ref value
                       $schema     JSON Schema $schema value
                       comment     Mentioned only in a comment or docstring
                       doc         Mentioned in markdown prose or HTML comment
    referred_file    The path string as written (repo-relative where determinable).
    exists           Y if the referred path resolves to an existing file, N otherwise.
    line_text        Stripped source line for context (truncated at 120 chars).

Stale reference detection
─────────────────────────
Filter on  exists = N  to find references to files that no longer exist —
the primary signal for stale comments, outdated documentation, and dead imports.

    python src/test/xref.py && awk -F, '$5=="N"' gen/xref.csv
"""

import argparse
import ast
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

# Directories/files to skip entirely
SKIP_DIRS = {'.git', 'gen', 'rsc/artifacts', '__pycache__', '.claude'}
# Root-level generated/deployed files that are not source
SKIP_FILES = {'index.html'}

# Python stdlib and known third-party modules — not repo files
STDLIB_MODULES = {
    'ast', 'csv', 'json', 're', 'sys', 'os', 'io', 'math', 'time', 'datetime',
    'pathlib', 'collections', 'itertools', 'functools', 'typing', 'types',
    'argparse', 'shutil', 'subprocess', 'hashlib', 'base64', 'copy', 'abc',
    'dataclasses', 'enum', 'logging', 'warnings', 'traceback', 'inspect',
    'textwrap', 'string', 'struct', 'socket', 'http', 'urllib', 'email',
    'difflib', 'sqlite3', 'contextlib', 'threading', 'multiprocessing',
    'jsonschema', 'referencing', 'requests', 'yaml', 'toml', 'pytest',
}

# Repo-relative path prefixes that identify a string as a likely file reference.
# Short bare names (like 'path', 'file') are excluded; only strings that look
# like repo paths are matched.
REPO_PREFIXES = (
    'src/', 'rsc/', 'doc/', 'gen/', 'docs/',
    'conversations/', 'diagnostics/', 'repairs/',
)

# ── helpers ───────────────────────────────────────────────────────────────────

def repo_files() -> list[Path]:
    result = []
    for f in REPO_ROOT.rglob('*'):
        if not f.is_file():
            continue
        rel = f.relative_to(REPO_ROOT)
        parts = rel.parts
        if any(part in SKIP_DIRS or part.startswith('.') for part in parts):
            continue
        if any(str(rel).startswith(d) for d in ('rsc/artifacts',)):
            continue
        if f.name in SKIP_FILES and f.parent == REPO_ROOT:
            continue
        result.append(f)
    return sorted(result)


def looks_like_repo_path(s: str) -> bool:
    """True if s looks like a repo-relative file path worth recording."""
    s = s.strip()
    if not s or ' ' in s or s.startswith('http') or s.startswith('/'):
        return False
    # Explicit relative reference ./name.ext — always a file reference
    if s.startswith('./') and re.search(r'\.(py|sh|json|md|html|g4|txt|log)$', s):
        return True
    if s.startswith('./'):
        s = s[2:]
    # Must be more than a bare fragment like "gen/data-" with no filename
    if not Path(s).suffix and not any(s.rstrip('/') == p.rstrip('/') for p in REPO_PREFIXES):
        has_name = bool(Path(s).name) and len(Path(s).name) > 3
        if not has_name:
            return False
    return any(s.startswith(p) for p in REPO_PREFIXES) or (
        '/' in s and not s.startswith('#') and len(s) > 6
        and s[0].isalpha() and (s.endswith('.py') or s.endswith('.sh')
            or s.endswith('.json') or s.endswith('.md') or s.endswith('.html')
            or s.endswith('.g4') or s.endswith('.txt') or s.endswith('.log'))
    )


def resolve(referred: str, referring: Path) -> tuple[str, str]:
    """Return (canonical_repo_relative_path, exists_flag)."""
    s = referred.strip()
    # Try as repo-relative (strip leading ./ but not ../)
    bare = s.lstrip('./')
    candidate = REPO_ROOT / bare
    if candidate.exists():
        try:
            return str(candidate.resolve().relative_to(REPO_ROOT)), 'Y'
        except ValueError:
            pass
    # Try relative to referring file's directory (handles ../ traversal)
    candidate2 = (referring.parent / s).resolve()
    if candidate2.exists():
        try:
            return str(candidate2.relative_to(REPO_ROOT)), 'Y'
        except ValueError:
            pass
    return bare or s, 'N'


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
                if looks_like_repo_path(s):
                    lineno = getattr(node, 'lineno', 0)
                    ltext = lines[lineno - 1].strip() if lineno else ''
                    # Distinguish comment/docstring context from call context
                    ref_type = 'path_str'
                    emit(rows, f, lineno, ref_type, s, ltext)

    # Line pass: comments and subprocess/exec calls
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            for match in re.finditer(r'[\w./\-]+\.(?:py|sh|json|md|html|g4)', stripped):
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

        # Pattern 1: BASH_SOURCE[0] — the script's own directory
        if 'BASH_SOURCE' in val or 'dirname' in val:
            env[var] = script_dir
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
            for match in re.finditer(r'[\w./\-]+\.(?:py|sh|json|md|html)', stripped):
                s = match.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)
            continue

        is_call_line = bool(re.search(r'\bpython\b|\bsource\b|\bbash\b|\bsh\b', line))

        for match in re.finditer(r'"(\$\w+[^"]*)"'
                                  r"|'(\$\w+[^']*)'", line):
            raw = match.group(1) or match.group(2)
            s = substitute(raw)
            if not looks_like_repo_path(s):
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
        # Other string values that look like repo paths
        for match in re.finditer(r'"((?:src|rsc|doc)/[^"]+)"', stripped):
            emit(rows, f, i, 'path_str', match.group(1), stripped)


def extract_markdown(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
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
        # Bare path-like strings in code blocks / text
        for match in re.finditer(r'\b((?:src|rsc|doc|gen)/[\w./\-]+)', stripped):
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
            for m2 in re.finditer(r'[\w./\-]+\.(?:py|sh|json|md|html|g4)', match.group(1)):
                s = m2.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)
        # JS string literals referencing repo files
        for match in re.finditer(r"['\"]([^'\"]*(?:src|rsc)/[^'\"]*)['\"]", stripped):
            s = match.group(1)
            if looks_like_repo_path(s):
                emit(rows, f, i, 'path_str', s, stripped)


def extract_g4(f: Path, rows: list) -> None:
    try:
        lines = f.read_text(errors='replace').splitlines()
    except OSError:
        return
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('//'):
            for match in re.finditer(r'[\w./\-]+\.(?:py|sh|json|md|g4)', stripped):
                s = match.group()
                if looks_like_repo_path(s):
                    emit(rows, f, i, 'comment', s, stripped)


# ── dispatch ──────────────────────────────────────────────────────────────────

EXTRACTORS = {
    '.py':   extract_python,
    '.sh':   extract_shell,
    '.json': extract_json,
    '.md':   extract_markdown,
    '.html': extract_html,
    '.g4':   extract_g4,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(REPO_ROOT / 'gen' / 'xref.csv'))
    args = parser.parse_args()

    rows: list[list] = []
    for f in repo_files():
        ext = f.suffix.lower()
        extractor = EXTRACTORS.get(ext)
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

    # Full outer join: add rows for repo files never appearing as referred_file.
    # These are candidates for orphaned/dead files.
    referenced: set[str] = {row[3] for row in deduped}
    all_files = {str(f.relative_to(REPO_ROOT)) for f in repo_files()}
    for fp in sorted(all_files - referenced):
        deduped.append(['', '', '', fp, 'Y', ''])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['referring_file', 'line', 'ref_type', 'referred_file', 'exists', 'line_text'])
        w.writerows(deduped)

    stale    = sum(1 for r in deduped if r[0] and r[4] == 'N')
    orphaned = sum(1 for r in deduped if not r[0])
    print(f'{len(deduped)} rows: {len(deduped)-stale-orphaned} live refs, '
          f'{stale} stale, {orphaned} unreferenced files → {out.relative_to(REPO_ROOT)}')


if __name__ == '__main__':
    main()
