"""
render.py - render each gemini scrape on its own, a map (issues/1195): the scrape with each turn
heading anchored, and the facts the collate names and places it by, written at the scrape's
cache address, so that the collate reads them and never the scrape.

Usage:
  src/run_python_script.sh src/main/browser/gemini/render.py --dom-capture <DOM-capture-root>
"""
import argparse
import json
import re
import sys
from pathlib import Path
import tier
from markdown_projection import FACTS, MD033_PRAGMA, RENDERINGS, counted, md_validator, project_scrape, write_if_changed


HEADING = re.compile(r'^## (Human|Gemini) \((\d+)\)$', flags=re.M)


def anchored(md):
    """The scrape with each turn heading anchored by its role count - gemini has no message
    uuids, and its conversations are append-only, so an anchor never moves - and the turn
    counts as frontmatter; the lint pragma after the title line, as claude's rendering has it."""
    md = HEADING.sub(lambda m: f'## {m[1]} ({m[2]}) <a id="{m[1].lower()}-{m[2]}"></a>', md)
    first, _, rest = md.partition('\n')
    said = counted(md)                                # the turn count's one home, by role (issues/1001)
    return f"---\nsource: dom-capture\nhuman: {said['human']}\nassistant: {said['assistant']}\n---\n\n{first}\n\n{MD033_PRAGMA}\n\n{rest.lstrip()}"


def render_scrape(unit: Path, valid) -> bool:
    """Each of the scrape's markdown files anchored, and its problems recorded, at the scrape's
    cache address; whether anything changed."""
    cache = tier.cache_of(unit)
    record, changed = {}, False
    for f in sorted(unit.glob('*.md')):
        text = f.read_text()
        record[f.name] = {'problems': [] if valid.is_valid(project_scrape(text)) else ['fails markdownConversation']}
        changed |= write_if_changed(cache / RENDERINGS / f.name, anchored(text))
    for stale in (cache / RENDERINGS).glob('*.md') if (cache / RENDERINGS).is_dir() else []:
        if stale.name not in record:
            stale.unlink()
            changed = True
    changed |= write_if_changed(cache / FACTS, json.dumps(record, ensure_ascii=False, indent=1) + '\n')
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dom-capture', required=True, help='dir of <id>/ scrape folders')
    args = ap.parse_args()
    units = sorted(p for p in Path(args.dom_capture).iterdir() if p.is_dir())
    valid = md_validator()
    outcome = [render_scrape(unit, valid) for unit in units]
    print(f'  render: {len(units)} scrape(s), {outcome.count(True)} rendered anew, {outcome.count(False)} current')
    return 0


if __name__ == '__main__':
    sys.exit(main())
