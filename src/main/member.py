"""
member.py - the one reading of membership by placement: the members of a directory are
its subdirectories that hold a file outside __pycache__. A directory git emptied in a
rename keeps its gitignored bytecode in a checkout that held it, and is no member (issues/669).
"""

from pathlib import Path



def is_member(directory: Path) -> bool:
    return directory.is_dir() and directory.name != '__pycache__' and any(
        f.is_file() and '__pycache__' not in f.relative_to(directory).parts
        for f in directory.rglob('*'))


def members(root: Path) -> list[Path]:
    """The member directories of root, sorted by name."""
    return sorted(d for d in root.iterdir() if is_member(d))
