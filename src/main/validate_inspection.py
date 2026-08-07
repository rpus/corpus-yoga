#!/usr/bin/env python
"""
Render the failure inspection a validation log carries after a failed verdict:
the offending sub-instance, the instance and schema paths, the schema fragment
at the error site, its other occurrences in the instance, and the command that
re-fetches those occurrences. One author for the log's content (#396) — the
sections a shell on_failure used to assemble from jq and three scripts.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling helpers when imported from elsewhere
from markdown_projection import REPO  # noqa: E402
from schema_occurrences import enumerate_instance_paths, find_instance_patterns  # noqa: E402
from schema_path import follow_path, parse_instance_path  # noqa: E402


def _rel(path):
    return os.path.relpath(path, REPO)


def _walk(node, parts):
    for part in parts:
        node = node[part]
    return node


def inspect_failure(input_file, schema_file, result):
    """The inspection lines for a failed validate() result — empty when the
    verdict names no instance path (schema errors carry none)."""
    path_raw = None
    for line in result:
        if line.startswith('Path: '):
            path_raw = line[len('Path: '):]
            break
    if path_raw is None:
        return []

    instance_path = parse_instance_path(path_raw)
    with open(input_file) as fh:
        instance = json.load(fh)
    with open(schema_file) as fh:
        schema = json.load(fh)

    out = ['--- jq inspection ---']
    out += json.dumps(_walk(instance, instance_path), indent=2, ensure_ascii=False).splitlines()

    instance_ptr = '/' + '/'.join(str(x) for x in instance_path)
    schema_ptr = follow_path(instance_path, schema, schema)
    out += ['--- instance path ---', f'{_rel(input_file)}#{instance_ptr}']
    out += ['--- schema path ---', f'{_rel(schema_file)}{schema_ptr}']

    out.append('--- schema fragment ---')
    fragment = _walk(schema, [p for p in schema_ptr.lstrip('#').split('/') if p])
    out += json.dumps(fragment, indent=2, ensure_ascii=False).splitlines()

    out.append('--- schema occurrences ---')
    for pattern in find_instance_patterns(schema, schema_ptr):
        for occurrence in enumerate_instance_paths(instance, pattern):
            out.append('  ' + json.dumps(occurrence))

    jq_filter = ('[inputs as $p | {key: ($p|tostring), value: ($inst[0]|getpath($p))}]'
                 ' | from_entries')
    occurrences_script = _rel(Path(__file__).resolve().parent / 'schema_occurrences.py')
    out += ['--- fetch occurrences command ---',
            f'src/run_python_script.sh "{occurrences_script}" "{schema_ptr}"'
            f' "{_rel(schema_file)}" "{_rel(input_file)}" \\',
            f'  | jq -n --slurpfile inst "{_rel(input_file)}" \\',
            f"    '{jq_filter}'"]
    return out
