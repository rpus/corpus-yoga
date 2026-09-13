#!/usr/bin/env python
"""
provider.py — inspect declared AI providers, live harness directories, and machine stores.

Usage:
    corpus-yoga provider           # table of declared providers, live harnesses, mounts, stores
    corpus-yoga provider sync [--apply]   # wire missing ext/mnt mounts and machine store dirs
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/provider/provider.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser
import provider


def report() -> int:
    declared = provider.providers()
    print(f'{"provider":<10}  {"live harness":<25}  {"mount in ext/mnt/":<25}  {"store":<30}')
    for p in declared:
        name = p['provider']
        live = provider.live_harness_path(p)
        live_str = f'✓ {p["live_harness"]}' if live.is_dir() else f'– {p["live_harness"]} (absent)'
        
        mnt = provider.mount_path(p)
        mnt_str = f'✓ {p["mount_name"]}' if (mnt.is_symlink() and mnt.exists()) else f'– {p["mount_name"]} (absent)'
        
        store = provider.store_path(p)
        rel_store = store.relative_to(REPO) if store.is_relative_to(REPO) else store
        store_str = f'✓ {rel_store}' if store.is_dir() else f'– {rel_store} (absent)'
        
        print(f'{name:<10}  {live_str:<25}  {mnt_str:<25}  {store_str:<30}')
    return 0


def sync(apply: bool) -> int:
    declared = provider.providers()
    acts = []
    for p in declared:
        live = provider.live_harness_path(p)
        mnt = provider.mount_path(p)
        if live.is_dir() and not (mnt.is_symlink() and mnt.exists()):
            acts.append(('mount', p['mount_name'], mnt, live))
        
        store = provider.store_path(p)
        if not store.is_dir():
            acts.append(('store', p['provider'], store, None))
            
    if not acts:
        print('provider sync: all mounts and machine stores for present harnesses are wired')
        return 0
        
    if not apply:
        print('provider sync: --apply would:')
        for kind, name, path, target in acts:
            if kind == 'mount':
                print(f'  link mount ext/mnt/{name} → {target}')
            else:
                rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
                print(f'  create store {rel}')
        return 0
        
    for kind, name, path, target in acts:
        if kind == 'mount':
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True)
            path.symlink_to(target)
            print(f'✓ linked ext/mnt/{name} → {target}')
        else:
            path.mkdir(parents=True, exist_ok=True)
            rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
            print(f'✓ created {rel}')
    return 0


def main() -> int:
    parser = command_parser('provider')
    args = parser.parse_args()
    if getattr(args, 'verb', None) == 'sync':
        return sync(getattr(args, 'apply', False))
    return report()


if __name__ == '__main__':
    sys.exit(main())
