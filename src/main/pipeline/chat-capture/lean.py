#!/usr/bin/env python
"""
lean.py - lift one capture into the markdownConversation shape (issues/965): a claude capture's
apiConversation JSON through markdown_projection.project, a gemini DOM scrape's markdown
through markdown_projection.project_scrape; the lean JSON written where the validate step
names, for src/main/validate_versions.py to judge against the family, with source.sha256
beside it naming the staged bytes it was lifted from.

Usage:
  src/run_python_script.sh src/main/pipeline/chat-capture/lean.py <capture.json | scrape.md> <lean.json>
"""
import hashlib
import json
import sys
from pathlib import Path

SELF = 'src/main/pipeline/chat-capture/lean.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main'))
from markdown_projection import project, project_scrape  # noqa: E402


def main(argv: list[str]) -> int:
    source, out = Path(argv[0]), Path(argv[1])
    if source.suffix == '.json':
        lean = project(json.loads(source.read_text()))
    else:
        lean = project_scrape(source.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lean, ensure_ascii=False) + '\n')
    # the lean JSON is a conversion of the staged file: source.sha256 beside it names the
    # bytes it was lifted from, which the rehearsal record carries so the stage reads the
    # family's verdict as the unit's own (src/main/rehearsal.py reduce, corpus.verdict)
    (out.parent / 'source.sha256').write_text(hashlib.sha256(source.read_bytes()).hexdigest() + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
