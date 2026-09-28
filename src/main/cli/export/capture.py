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
from safari import (PAGE_LOAD_WAIT, safari_close_work_tab, safari_eval_js, safari_fetch_file,  # noqa: E402
                    safari_navigate, safari_open_work_tab)

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


def hoist(target: Path, member: str) -> str | None:
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


def fetch(entry: dict, target: Path) -> tuple[list[str] | None, str]:
    """One export_url through the session: the archive lands in Downloads as .part, is
    moved into the payload and unpacked there. Returns (members deposited, the words) -
    None where nothing arrived, the words saying the response the page saw."""
    url, filename = entry['export_url'], entry['filename']
    print(f'fetch: {url}')
    got, status = safari_fetch_file(url, f'{target.name}-{filename}')   # the export's star names the download
    if got is None:
        seen = f'HTTP {status}' if status else 'no response read within the timeout'
        return None, f'{filename}: {seen} from the session; nothing arrived'
    staged = target / filename
    shutil.move(str(got), staged)
    size = staged.stat().st_size
    if not zipfile.is_zipfile(staged):
        # a 2xx whose body is not an archive - what a spent link serves, a page in place of
        # the file; named as what arrived, and never deposited as a payload
        head = staged.read_bytes()[:60]
        staged.unlink()
        return None, f'{filename}: HTTP {status} but the body is not an archive ({size} bytes, beginning {head!r}); nothing deposited'
    return deposit(staged, target), f'{filename}: HTTP {status}, {size} bytes'


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
    failed: list[str] = []
    for entry in files:
        got, words = fetch(entry, target)
        if got is None:
            print(f'  {words}')
            failed.append(entry['filename'])
            continue
        print(f'  {words} ({entry["category"]}) - {", ".join(got)}')
        fetched += 1
    if prev_tab is not None:
        safari_close_work_tab(prev_tab)   # the reader's tab back, whatever the fetches did
    if fetched == 0:
        # nothing landed: no directory that reads as a payload; the manifest stays staged,
        # unpaired, the record of the attempt and the retry's input
        shutil.rmtree(target)
        rel = staged_manifest.relative_to(REPO) if staged_manifest.is_relative_to(REPO) else staged_manifest
        print(f'export capture: NOT DONE - 0 of {len(files)} file(s) fetched: {"; ".join(failed)}; '
              f'{staged_manifest.name} staged alone, unpaired')
        print(f'    → run: corpus-yoga export capture --manifest {rel}')
        return 1
    if failed:
        print(f'export capture: NOT DONE - {fetched} of {len(files)} file(s) in {target.name}/, '
              f'incomplete: {"; ".join(failed)} - the manifest lists what is owed')
        return 1
    print(f'export capture: DONE - {target.relative_to(REPO) if target.is_relative_to(REPO) else target}/ '
          f'({fetched} file(s), as the manifest listed them) and {staged_manifest.name} beside it')
    if not to:
        # the act names the next acts (#687)
        print('export capture: staged under tmp/stage/input/claude/chat/bulk-export, not promoted - '
              'corpus-yoga pipeline rehearse, then corpus-yoga export promote')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
