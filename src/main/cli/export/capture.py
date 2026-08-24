#!/usr/bin/env python
"""capture.py (corpus-yoga export capture) - fetch a deposited manifest's payload.

The manifest arrives by hand (the emailed link downloads it; the reader deposits
it in data/input/claude/chat/bulk-export/). This verb reads the manifest named
by --manifest - its source, and no other capture (L10) - and fetches each
listed zip from its export_url into the data-* directory sharing the
manifest's own star: manifest-<X>.json becomes data-<X>/, the prefix swapped
and nothing else derived (the maintainer's ruling, 2026-08-24). If that directory
already exists the capture refuses before any URL is touched - the one-use
URLs are spent only once the directory is this run's own. Bare invocation fetches
nothing: it lists the manifests held and requires --manifest, because a
default would silently pick which one-use URLs to spend.

Each export_url is ONE-USE: a fetch consumes it, so every downloaded byte is the
payload's last chance. Each file is therefore written the moment its fetch
completes - streamed to <filename>.part, renamed into place on success - so a
deposit is whole or absent per FILE, never per manifest: a death mid-run keeps
every completed file and loses only the one in flight, named loudly.

Usage:
    src/run_python_script.sh src/main/cli/export/capture.py [--manifest <file>] [--to <dir>]
"""
import json
import sys
import urllib.request
from pathlib import Path

SELF = 'src/main/cli/export/capture.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
from send import SendRefused, assert_may_send  # noqa: E402

STORE = REPO / 'data' / 'input' / 'claude' / 'chat' / 'bulk-export'


def derived_data_name(manifest_path: Path) -> str:
    """data-<X> from manifest-<X>.json: the prefix swapped, the star kept whole."""
    stem = manifest_path.stem
    if not stem.startswith('manifest-'):
        sys.exit(f'export capture: NOT DONE - {manifest_path.name} does not start with '
                 'manifest-')
    return f'data-{stem.removeprefix("manifest-")}'


def list_manifests(store: Path) -> int:
    manifests = sorted(store.glob('manifest-*.json')) if store.is_dir() else []
    if not manifests:
        print(f'export capture: NOT DONE - no manifest-*.json in {store} '
              '(deposit the emailed manifest there first)')
        return 1
    print('export capture: NOT DONE - name the manifest to fetch; each export_url is '
          'one-use, so no default picks one:')
    for m in manifests:
        held = (store / derived_data_name(m)).is_dir()
        state = 'payload held' if held else 'unfetched'
        print(f'  --manifest {m} ({state})')
    return 1


def fetch_one(url: str, dest: Path) -> int:
    """One file, streamed to .part and renamed on success - the rename is the deposit."""
    part = dest.with_name(dest.name + '.part')
    print(f'fetch: {url}')
    print(f'    -> {dest}')
    with urllib.request.urlopen(url) as response, open(part, 'wb') as out:
        while chunk := response.read(1 << 16):
            out.write(chunk)
    part.rename(dest)
    return dest.stat().st_size


def main(argv: list[str]) -> int:
    manifest_arg = to = None
    while argv:
        arg = argv.pop(0)
        if arg == '--manifest' and argv:
            manifest_arg = Path(argv.pop(0))
        elif arg == '--to' and argv:
            to = Path(argv.pop(0))
        else:
            sys.exit(f'usage: {SELF} [--manifest <file>] [--to <dir>]')
    store = to if to else STORE
    if manifest_arg is None:
        return list_manifests(store)
    manifest_path = manifest_arg
    if not manifest_path.is_file():
        print(f'export capture: NOT DONE - {manifest_path} is not a file')
        return 1
    manifest = json.loads(manifest_path.read_text())
    files = manifest.get('data_files', [])
    target = store / derived_data_name(manifest_path)
    print(f'{manifest_path.name}: {len(files)} file(s), version {manifest.get("version")}')
    print(f'  -> {target.name}/')
    if target.exists():
        print(f'export capture: NOT DONE - {target.name}/ already exists; nothing fetched, '
              'no URL spent. If it holds an earlier or partial capture, the human moves it '
              'aside; this verb never overwrites a deposit')
        return 1
    try:
        assert_may_send('export_url fetches (export capture) - each URL is one-use')
    except SendRefused as refused:
        print(f'export capture: NOT DONE - {refused}')
        return 1
    target.mkdir(parents=True, exist_ok=False)
    fetched = 0
    for entry in files:
        dest = target / entry['filename']
        try:
            size = fetch_one(entry['export_url'], dest)
        except Exception as error:
            print(f'export capture: NOT DONE - {entry["filename"]} failed ({error}); '
                  f'{fetched} of {len(files)} file(s) deposited in {target.name}/ and kept - '
                  'a spent URL cannot be refetched, so what landed is the record')
            return 1
        print(f'  {entry["filename"]}: {size} bytes ({entry["category"]})')
        fetched += 1
    print(f'export capture: DONE - {target.relative_to(REPO) if target.is_relative_to(REPO) else target}/ '
          f'({fetched} file(s), as the manifest listed them)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
