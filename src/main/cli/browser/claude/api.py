#!/usr/bin/env python
"""
api.py - the claude mechanism of the browser capture: a conversation's JSON fetched
from the claude.ai API through Safari, and the conversation's record completed with
the files the JSON names (#422), deposited into the artifact library. Called by
capture.py for a claude capture; gemini has no API and no counterpart here.
"""
import json
import shutil
import sys
from pathlib import Path

SELF = 'src/main/cli/browser/claude/api.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_DIR = _root[0]
sys.path.insert(0, str(REPO_DIR / 'src' / 'main'))  # src/main - the tier's shared modules
from safari import safari_fetch_api_json, safari_fetch_asset, process_chain  # noqa: E402


def rel(path):
    """The repo-relative spelling of a path where one exists (#412): logs speak
    the repo's addresses, never a resolved machine path."""
    try:
        return str(Path(path).resolve().relative_to(REPO_DIR))
    except ValueError:
        return str(path)


# The run's own tally, written by capture_all and read by the footer — including
# the interrupted footer, which must say how far the run got (#415).

def fetch_api(conv_id, out_dir):
    """Fetch the apiConversation JSON; returns the saved filename, or None on failure."""
    f = safari_fetch_api_json(conv_id)
    if f is None:
        return None
    try:
        shutil.move(str(f), out_dir / f'{conv_id}.json')
    except PermissionError:
        # macOS TCC: reading ~/Downloads needs a per-app grant held by some app
        # in this process's ancestry — print the ancestry so the reader knows
        # which app to grant (Files and Folders only lists apps that have
        # ASKED; Full Disk Access accepts manual additions via its + button).
        print(f'FAIL: macOS denied reading {f} from this process chain:\n'
              f'    {process_chain()}\n'
              '    grant the outermost app Downloads access (System Settings → Privacy & '
              'Security; Full Disk Access takes manual additions where Files and Folders '
              f'shows nothing). The fetched json is stranded in ~/Downloads — move it '
              f'into {out_dir} by hand, or recapture from an already-granted Terminal:\n'
              f'    → run: corpus-yoga browser capture --provider claude --id {conv_id}'
              f'  # first front https://claude.ai/chat/{conv_id} in Safari',
              file=sys.stderr)
        return None
    return f'{conv_id}.json'



def asset_handles(conv_json):
    """The fetchable file handles one API capture names (#422): each files[]
    entry's best asset URL — the document original where one exists, else the
    image preview — with its file_name. Attachments carry their text inline
    (extracted_content) and name no asset URL; they are not handles."""
    out = []
    for m in conv_json.get('chat_messages', []):
        for f in (m.get('files') or []):
            url = ((f.get('document_asset') or {}).get('url')
                   or f.get('preview_url')
                   or (f.get('thumbnail_asset') or {}).get('url'))
            name = f.get('file_name')
            if url and name:
                out.append((url, name))
    return out


_LIBRARY = None   # (dir_for, dressing) once per run — set on the first claude capture


def _library():
    """The artifact library face, once per run (#421/#422): dir_for and the
    corpus dressing map, imported lazily so gemini sweeps never touch it."""
    global _LIBRARY
    if _LIBRARY is None:
        sys.path.insert(0, str(REPO_DIR / 'src' / 'main' / 'pipeline' / 'chat-exports'))
        from library import dir_for, migration_note  # noqa: E402 — one authority (#421)
        from markdown_projection import corpus_index  # noqa: E402
        migration_note()
        dressing = {}
        md_root = REPO_DIR / 'data' / 'output' / 'markdown'
        if md_root.is_dir():
            dressing = {cid: f'{n:03d}-{stem.rsplit("/", 1)[-1].split("-", 1)[-1]}'
                        for n, stem, _title, cid in corpus_index(str(md_root))}
        _LIBRARY = (dir_for, dressing)
    return _LIBRARY


def complete_files(conv_id, api_dir):
    """A capture COMPLETES the conversation's record (#422): the JSON names the
    conversation's files (uploads — documents, images), so the same visit
    fetches whatever the artifact library lacks and deposits it uuid-keyed.
    The library gap is the work-list — a complete library costs nothing — and
    by-hand remains the stated fallback for what no handle names. Returns
    (fetched, notes): a failed asset is a note, not a failed capture — the
    JSON is the record; the files are its belongings."""
    j = api_dir / f'{conv_id}.json'
    if not j.is_file():
        return 0, []
    handles = asset_handles(json.loads(j.read_text()))
    if not handles:
        return 0, []
    dir_for, dressing = _library()
    lib_dir = dir_for(conv_id, dressing.get(conv_id, ''))
    lib_rel = rel(lib_dir)
    fetched, notes = 0, []
    for url, name in handles:
        if (lib_dir / name).exists():
            continue
        print(f'  file: {name} ← {url} → {lib_rel}/')
        got = safari_fetch_asset(url, name)
        if got is None:
            notes.append(f'file {name}: no completed download arrived — fetch by hand: {url}')
            continue
        lib_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(got), lib_dir / name)
        # the count states verified deposits: a move that leaves no regular
        # file at the address is a note, never a success
        if (lib_dir / name).is_file():
            fetched += 1
        else:
            notes.append(f'file {name}: download arrived but no file stands at '
                         f'{lib_rel}/{name} — fetch by hand: {url}')
    return fetched, notes
