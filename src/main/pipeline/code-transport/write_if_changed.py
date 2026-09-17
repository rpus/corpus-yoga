#!/usr/bin/env python
"""
write_if_changed.py - write a cache file through a sibling temp file and keep the existing
file, and its mtime, when the content is identical. A converted session's mtime is
downstream validation's memoisation key: an unchanged session must not look new, or
every run revalidates it. Shared by every provider's mechanism under this pipeline.
"""
import filecmp
import os

SELF = 'src/main/pipeline/code-transport/write_if_changed.py'


def write_if_changed(path, write):
    tmp = path + '.tmp'
    with open(tmp, 'w') as dst:
        result = write(dst)
    if os.path.exists(path) and filecmp.cmp(tmp, path, shallow=False):
        os.remove(tmp)
    else:
        os.replace(tmp, path)
    return result
