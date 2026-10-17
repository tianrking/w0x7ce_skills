"""Fail-fast, cross-platform locks for cooperating SOP maintenance processes."""
import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def lock(root, name):
    path = Path(root)/'.local'/(name + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('Another SOP operation holds ' + str(path) + '; do not remove it unless that operation has ended.')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        path.unlink()
