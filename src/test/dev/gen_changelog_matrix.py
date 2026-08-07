#!/usr/bin/env python
"""
gen_changelog_matrix.py — view or re-render machine-local validation matrices.

Matrices are normally written by validation itself (validate_versions.py renders each
datum's matrix.md beside its validation/ logs whenever the logs change), so running
this tool is never required after a pipeline run. It remains useful to:

  - print the aggregate table across all of a pipeline's data (default), or
  - re-render matrix.md files without revalidating (--write), e.g. after the
    renderer's format changes.

Usage:
    yoga pipeline sync <pipeline>        # this file, with --write, over that pipeline

Where <pipeline> is any key from PIPELINES in run.py.
"""

import argparse
import sys
from pathlib import Path

SELF = 'src/test/dev/gen_changelog_matrix.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — shared modules live at its root

from run import PIPELINES, REPO_ROOT, RSC_SCHEMA, _datum_dirs  # noqa: E402
from validation_matrix import HEADER, render_rows, write_matrix  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pipeline', required=True, choices=list(PIPELINES))
    p.add_argument('--write', action='store_true',
                   help="Re-render each datum's matrix.md (default: print aggregate table to stdout)")
    args = p.parse_args()

    pipeline          = PIPELINES[args.pipeline]
    schema_parent_dir = RSC_SCHEMA / pipeline.changelog.parent.parent.name

    datum_dirs = _datum_dirs(pipeline)
    if not datum_dirs:
        sys.exit(f'no validated data under {pipeline.cache_output.relative_to(REPO_ROOT)} — '
                 f'→ run: yoga pipeline run {args.pipeline}')

    if args.write:
        for datum_dir in datum_dirs:
            mfile = write_matrix(datum_dir, schema_parent_dir)
            if mfile:
                print(f'Wrote {mfile.relative_to(REPO_ROOT)}')
    else:
        print('| Datum ' + HEADER[0])
        print('| --- ' + HEADER[1])
        for datum_dir in datum_dirs:
            subject = ' / '.join(datum_dir.relative_to(pipeline.cache_output).parts)
            for line in render_rows(datum_dir, schema_parent_dir):
                print(f'| `{subject}` {line}')


if __name__ == '__main__':
    main()
