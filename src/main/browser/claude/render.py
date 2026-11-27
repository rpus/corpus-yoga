"""
render.py - render each claude capture's conversation on its own, a map (issues/1195): its
markdown body and the facts the collate names, places and dresses it by, written at the
capture's cache address, so that the collate reads them and never the capture.

Usage:
  src/run_python_script.sh src/main/browser/claude/render.py --api-capture <API-capture-root>
  src/run_python_script.sh src/main/browser/claude/render.py --capture <API-capture-root>/<uuid>
"""
import argparse
import json
import sys
from pathlib import Path
import tier
from markdown_projection import FACTS, RENDERED, facts, find_api_json, md_validator, project, render_body, write_if_changed

SELF = 'src/main/browser/claude/render.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'


def render_capture(unit: Path, valid) -> bool | None:
    """The capture's rendering and facts at its cache address; whether either changed, or None
    where the capture holds no apiConversation."""
    api = find_api_json(unit)
    if api is None:
        return None
    cache = tier.cache_of(unit)
    body = write_if_changed(cache / RENDERED, render_body(project(api)))
    record = write_if_changed(cache / FACTS, json.dumps(facts(api, valid), ensure_ascii=False, indent=1) + '\n')
    return body or record


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--api-capture', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--capture', help='one <uuid>/ capture folder')
    args = ap.parse_args()
    units = ([Path(args.capture)] if args.capture
             else sorted(p for p in Path(args.api_capture).iterdir() if p.is_dir()))
    valid = md_validator()
    outcome = [render_capture(unit, valid) for unit in units]
    print(f'  render: {len(units)} capture(s), {outcome.count(True)} rendered anew, '
          f'{outcome.count(False)} current, {outcome.count(None)} with no apiConversation')
    return 0


if __name__ == '__main__':
    sys.exit(main())
