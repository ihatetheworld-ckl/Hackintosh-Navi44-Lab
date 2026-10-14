"""Project path checks; not a replacement for an OS sandbox or TOCTOU proof."""
from pathlib import Path
import os

ROOT = Path(__file__).absolute().parent

def checked(path):
    path = Path(path)
    if '..' in path.parts:
        raise ValueError('Parent traversal refused')
    if not path.is_absolute(): path = ROOT/path
    path = path.absolute()
    if not path.is_relative_to(ROOT): raise ValueError('Outside authorized project')
    # Reject reparse points in every existing parent, including above ROOT.
    for item in [path, *path.parents]:
        if item.exists() or item.is_symlink():
            state = item.lstat()
            if item.is_symlink() or getattr(state,'st_file_attributes',0) & 0x400:
                raise ValueError('Reparse/symlink refused: '+str(item))
            if item.is_file() and state.st_nlink != 1:
                raise ValueError('Hard-linked file refused: '+str(item))
    if not path.resolve().is_relative_to(ROOT.resolve()): raise ValueError('Resolved escape')
    return path

def mkdir(path):
    path = checked(path); path.mkdir(parents=True,exist_ok=True); return checked(path)

def write(path, data):
    path = checked(path); mkdir(path.parent)
    if isinstance(data,str): path.write_text(data,encoding='utf-8',newline='\n')
    else: path.write_bytes(data)
    return checked(path)

def preflight(paths):
    return [str(checked(p)) for p in paths]
