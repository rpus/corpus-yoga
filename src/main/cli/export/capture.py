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
import urllib.request
from pathlib import Path

SELF = 'src/main/cli/export/capture.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import tier  # noqa: E402 — the tiers, one home (#702)
from send import SendRefused, assert_may_send  # noqa: E402

STORE = tier.DATA / 'input' / 'claude' / 'chat' / 'bulk-export'    # what is held: a staged name held there is refused
STAGE = tier.TMP_STAGE_INPUT / 'claude' / 'chat' / 'bulk-export'   # where the manifest and its payload land; corpus-yoga export promote reaches the store (#687)


def derived_data_name(manifest_path: Path) -> str:
    """data-<X> from manifest-<X>.json: the prefix swapped, the star kept whole."""
    stem = manifest_path.stem
    if not stem.startswith('manifest-'):
        sys.exit(f'export capture: NOT DONE - {manifest_path.name} does not start with '
                 'manifest-')
    return f'data-{stem.removeprefix("manifest-")}'


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
    try:
        assert_may_send('export_url fetches (export capture) - each URL is one-use')
    except SendRefused as refused:
        print(f'export capture: NOT DONE - {refused}')
        return 1
    target.mkdir(parents=True, exist_ok=False)
    if not same:
        shutil.copyfile(manifest_path, staged_manifest)
    print(f'  {staged_manifest.name}: staged beside {target.name}/')
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
          f'({fetched} file(s), as the manifest listed them) and {staged_manifest.name} beside it')
    if not to:
        # the act names the next acts (#687)
        print('export capture: staged under tmp/stage/input/claude/chat/bulk-export, not promoted - '
              'corpus-yoga pipeline rehearse, then corpus-yoga export promote')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
