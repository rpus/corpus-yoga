#!/usr/bin/env python
"""
transcript_to_json.py - one captured Antigravity session directory to session.json, the
gemini session family's datum (rsc/schema/pipeline/code-transport/gemini/session): the
steps of transcript_full.jsonl where the capture holds it, else of transcript.jsonl, one
line each, as one array. The summary row beside the transcripts (summary.json) is copied
to <output>.summary, the projection's source for the title.

Usage:
    src/run_python_script.sh src/main/pipeline/code-transport/gemini/transcript_to_json.py \
        <session-dir> <output.json>
"""
import json
import sys
from pathlib import Path

SELF = 'src/main/pipeline/code-transport/gemini/transcript_to_json.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main' / 'pipeline' / 'code-transport'))
from write_if_changed import write_if_changed  # noqa: E402

TRANSCRIPTS = ('transcript_full.jsonl', 'transcript.jsonl')


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    session_dir, out = Path(sys.argv[1]), sys.argv[2]
    source = next((session_dir / t for t in TRANSCRIPTS if (session_dir / t).is_file()), None)
    if source is None:
        print(f'FAIL: {session_dir}: holds neither {" nor ".join(TRANSCRIPTS)}', file=sys.stderr)
        return 1
    lines = [l for l in source.read_text().splitlines() if l.strip()]
    for number, line in enumerate(lines, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError:
            if number < len(lines):
                raise
            print('warning: dropped truncated final line', file=sys.stderr)   # a session captured mid-append
            lines = lines[:-1]
    write_if_changed(out, lambda dst: dst.write('[\n' + ',\n'.join(lines) + '\n]\n'))
    summary = session_dir / 'summary.json'
    text = summary.read_text() if summary.is_file() else '{}'
    write_if_changed(out + '.summary', lambda dst: dst.write(text))
    print(f'  session.json: {len(lines)} step(s) from {source.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
