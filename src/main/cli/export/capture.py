#!/usr/bin/env python
"""capture.py (corpus-yoga export capture) - stage a manifest and the payload it lists.

The emailed link downloads the manifest; --manifest names it wherever the download
left it. This verb reads that file - its source, and no other capture (L10) -
copies it into the stage, and fetches each listed zip from its export_url into
the data-* directory sharing the manifest's own star: manifest-<X>.json beside
data-<X>/, the prefix swapped and nothing else derived. The two are the one
staged unit <X> (src/main/pipeline/chat-export/pipeline.json's companion):
corpus-yoga export promote copies data-<X>/ into shared storage, and the
manifest, the record of what was fetched, stays in the stage until
corpus-yoga stage clean removes the unit. If the directory
is staged or held, or a different manifest of the name is staged, the capture
refuses before any URL is touched - the one-use URLs are spent only once the
directory is this run's own. --manifest is required: a default would silently
pick which one-use URLs to spend.

Each export_url is ONE-USE: a fetch consumes it, so every downloaded byte is the
payload's last chance. Each file is therefore written the moment its fetch
completes - streamed to <filename>.part, renamed into place on success - so a
deposit is whole or absent per FILE, never per manifest: a death mid-run keeps
every completed file and loses only the one in flight, named loudly.

Usage:
    src/run_python_script.sh src/main/cli/export/capture.py --manifest <file> [--to <dir>]
"""
import json
import shutil
import sys
import csv
import re
import time
import zipfile
from pathlib import Path

SELF = 'src/main/cli/export/capture.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import tier  # noqa: E402 — the tiers, one home (#702)
from send import SendRefused, assert_may_send  # noqa: E402
from safari import (DOWNLOADS, PAGE_LOAD_WAIT, safari_close_work_tab, safari_eval_js,  # noqa: E402
                    safari_navigate, safari_open_work_tab)

MEMBERS_CSV = REPO / 'rsc' / 'naming' / 'export_archive_members.csv'   # what each category's archive unpacks to in Downloads
ARRIVAL_TIMEOUT = 300   # seconds a download may take to arrive and unpack; conversations.json is tens of MB

FRONT_URL = 'https://claude.ai/'   # the session the export URLs are read under: fronted once, its login checked

STORE = tier.DATA / 'input' / 'claude' / 'chat' / 'bulk-export'    # what is held: a staged name held there is refused
STAGE = tier.TMP_STAGE_INPUT / 'claude' / 'chat' / 'bulk-export'   # where the manifest and its payload land; corpus-yoga export promote reaches the store (#687)


def derived_data_name(manifest_path: Path) -> str:
    """data-<X> from manifest-<X>.json: the prefix swapped, the star kept whole."""
    stem = manifest_path.stem
    if not stem.startswith('manifest-'):
        sys.exit(f'export capture: NOT DONE - {manifest_path.name} does not start with '
                 'manifest-')
    return f'data-{stem.removeprefix("manifest-")}'


def deposit(archive: Path, target: Path) -> list[str]:
    """Unpack an archive at the payload's root - the form the pipeline reads, the held
    payloads' own - and remove the archive. The memories archive's one per-account file
    is hoisted to memories.json, the ruling of 2026-08-24 (the memories family's
    CHANGELOG, v4). Returns the members deposited."""
    with zipfile.ZipFile(archive) as z:
        z.extractall(target)
        names = sorted({n.split('/', 1)[0] for n in z.namelist() if n.strip('/')})
    archive.unlink()
    return [name for name in names if hoist(target, name)]


def hoist(target: Path, member: str) -> str:
    """A memories/ directory holding one file becomes memories.json; every other member
    stays as unpacked. Returns the member's name as deposited."""
    path = target / member
    if member == 'memories' and path.is_dir():
        files = [f for f in path.iterdir() if f.is_file()]
        if len(files) == 1:
            files[0].rename(target / 'memories.json')
            path.rmdir()
            return 'memories.json'
    return member


def front_session() -> tuple[str | None, str | None]:
    """Front claude.ai in a work tab of Safari's own, as the browser capture does for a sweep
    - never the reader's front tab - and read where it landed: a login page is the session's
    absence, said before any URL is spent. Returns (the login page landed on, or None; the
    reader's tab to restore)."""
    prev_tab = safari_open_work_tab()
    safari_navigate(FRONT_URL)
    time.sleep(PAGE_LOAD_WAIT)
    landed = safari_eval_js('String(location.href)') or '(URL unreadable)'
    if 'login' in landed:
        safari_close_work_tab(prev_tab)
        return landed, None
    return None, prev_tab


def archive_member(category: str) -> str:
    """The name a category's archive unpacks to in Downloads (rsc/naming/export_archive_members.csv)."""
    with MEMBERS_CSV.open(newline='') as f:
        for row in csv.DictReader(f):
            if row['category'] == category:
                return row['member']
    sys.exit(f'export capture: NOT DONE - {category}: no row in {MEMBERS_CSV.relative_to(REPO)} says what its archive unpacks to')


def _inode(path: Path) -> int | None:
    try:
        return path.stat().st_ino
    except OSError:
        return None


def fetch(entry: dict, target: Path) -> tuple[list[str] | None, str]:
    """One export_url, by navigation: the export page asks claude.ai for a signed storage URL
    and downloads from it, which an in-page fetch cannot (the storage refuses it), so the work
    tab is navigated to the export_url and Safari takes the download under the server's name,
    unpacking it on arrival where it opens safe files. The arrival is known by name and
    inode, never by clock: the archive under its own name, or what it unpacks to, exists with
    an inode it did not have before - Safari replaces a same-named entry, so a stale one is
    told from the new by inode. What arrives is moved into the payload and deposited there.
    Returns (members deposited, the words) - None where nothing arrived, the words saying
    what the page said."""
    url, filename = entry['export_url'], entry['filename']
    member = archive_member(entry['category'])
    # Safari replaces a same-named directory on unpacking, but a same-named FILE it keeps and
    # names the arrival <stem>-2<ext>, -3, ...: any name of that shape is the archive's or the
    # member's, and the arrival is whichever exists with an inode it did not have before
    def shape(name: str) -> re.Pattern:
        stem, ext = (name.rsplit('.', 1) + [''])[:2] if '.' in name else (name, '')
        return re.compile(re.escape(stem) + r'(-\d+)?' + (r'\.' + re.escape(ext) if ext else '') + '$')
    shapes = {shape(filename): 'archive', shape(member): 'unpacked'}
    def candidates() -> dict[Path, str]:
        return {entry: kind for entry in DOWNLOADS.iterdir() for pattern, kind in shapes.items() if pattern.match(entry.name)}
    before = {path: _inode(path) for path in candidates()}
    print(f'fetch: {url}')
    safari_navigate(url)
    deadline = time.time() + ARRIVAL_TIMEOUT
    while time.time() < deadline:
        said = safari_eval_js('String(document.body.innerText).slice(0, 200)').replace('\n', ' | ')
        if 'has been used' in said or 'Expired link' in said:
            return None, f'{filename}: nothing arrived; the page says: {said}'
        for path, kind in candidates().items():
            now = _inode(path)
            if now is not None and now != before.get(path) and not any(b.name.endswith('.download') for b in DOWNLOADS.glob(f'{Path(filename).stem}*')):
                if kind == 'archive':
                    if not zipfile.is_zipfile(path):
                        continue   # still being written
                    staged = target / filename
                    shutil.move(str(path), staged)
                    size = staged.stat().st_size
                    return deposit(staged, target), f'{filename}: {size} bytes, unpacked here'
                if member == Path(filename).stem:
                    # Safari unpacks a many-entry archive into a directory named by the archive's
                    # stem; the deposit holds the entries themselves at the root, as unpacking there does
                    names = [hoist(target, shutil.move(str(item), target / item.name) and item.name) for item in sorted(path.iterdir())]
                    path.rmdir()
                    return names, f'{filename}: unpacked by Safari as {path.name}/'
                shutil.move(str(path), target / member)   # under the member's own name, whatever Safari called the arrival
                return [hoist(target, member)], f'{filename}: unpacked by Safari as {path.name}'
        time.sleep(1)
    said = safari_eval_js('String(document.body.innerText).slice(0, 200)').replace('\n', ' | ')
    return None, f'{filename}: nothing arrived within {ARRIVAL_TIMEOUT}s; the page says: {said or "(nothing readable)"}'


def main(argv: list[str]) -> int:
    manifest_arg = to = None
    while argv:
        arg = argv.pop(0)
        if arg == '--manifest' and argv:
            manifest_arg = Path(argv.pop(0))
        elif arg == '--to' and argv:
            to = Path(argv.pop(0))
        else:
            sys.exit(f'usage: {SELF} --manifest <file> [--to <dir>]')
    store = to if to else STORE
    if manifest_arg is None:
        print('export capture: NOT DONE - --manifest <file> is required, the manifest where the '
              'download left it; corpus-yoga export lists what is held and staged')
        return 1
    manifest_path = manifest_arg
    if not manifest_path.is_file():
        print(f'export capture: NOT DONE - {manifest_path} is not a file')
        return 1
    manifest = json.loads(manifest_path.read_text())
    files = manifest.get('data_files', [])
    name = derived_data_name(manifest_path)
    target = (to if to else STAGE) / name
    staged_manifest = target.with_name(manifest_path.name)
    print(f'{manifest_path.name}: {len(files)} file(s), version {manifest.get("version")}')
    print(f'  -> {target.relative_to(REPO) if target.is_relative_to(REPO) else target}/')
    if (store / name).is_dir():
        print(f'export capture: NOT DONE - {name}/ is held in shared storage; nothing fetched, no URL spent')
        return 1
    if target.exists():
        print(f'export capture: NOT DONE - {target.name}/ already exists; nothing fetched, '
              'no URL spent. If it holds an earlier or partial capture, the human moves it '
              'aside; this verb never overwrites a deposit')
        return 1
    same = staged_manifest.exists() and staged_manifest.samefile(manifest_path)
    if staged_manifest.exists() and not same and staged_manifest.read_bytes() != manifest_path.read_bytes():
        print(f'export capture: NOT DONE - a different {staged_manifest.name} is staged; nothing fetched, '
              'no URL spent')
        return 1
    if files:
        try:
            assert_may_send('export_url fetches through the Safari session (export capture) - each URL is one-use')
        except SendRefused as refused:
            print(f'export capture: NOT DONE - {refused}; nothing staged, no URL spent')
            return 1
        logged_out, prev_tab = front_session()
        if logged_out:
            print(f'export capture: NOT DONE - Safari is logged out of claude.ai (landed on {logged_out}); '
                  'log in and re-run; nothing staged, no URL spent')
            return 1
    else:
        prev_tab = None
    target.mkdir(parents=True, exist_ok=False)
    if not same:
        # the manifest is consumed: its links are spent here, and a spent manifest has no use
        # but as the unit's record - moved, as the browser capture moves what Safari downloaded
        shutil.move(str(manifest_path), staged_manifest)
    print(f'  {staged_manifest.name}: staged beside {target.name}/' + ('' if same else f' (moved from {manifest_path})'))
    fetched = 0
    for entry in files:
        got, words = fetch(entry, target)
        if got is None:
            print(f'  {words}')
            continue
        print(f'  {words} ({entry["category"]}) - {", ".join(got)}')
        fetched += 1
    if prev_tab is not None:
        safari_close_work_tab(prev_tab)   # the reader's tab back, whatever the fetches did
    # one ask, one verdict: what was fetched of what the manifest lists. Whether the unit is
    # whole is read afterwards from the manifest beside it, by every face, not from here.
    where = target.relative_to(REPO) if target.is_relative_to(REPO) else target
    if fetched < len(files):
        print(f'export capture: NOT DONE - fetched {fetched} of {len(files)} file(s) into {where}/, '
              f'{staged_manifest.name} beside it')
        return 1
    print(f'export capture: DONE - fetched {fetched} of {len(files)} file(s) into {where}/, '
          f'{staged_manifest.name} beside it')
    if not to:
        # the act names the next acts (#687)
        print('export capture: staged under tmp/stage/input/claude/chat/bulk-export, not promoted - '
              'corpus-yoga pipeline rehearse, then corpus-yoga export promote')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
