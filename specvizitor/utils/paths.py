from contextlib import contextmanager
import os
import pathlib
import secrets
import shutil


def absolute_path(path) -> pathlib.Path:
    # resolve() alone does not expand `~`
    return pathlib.Path(path).expanduser().resolve()


@contextmanager
def atomic_write(path):
    """ Yield a temporary path next to `path` to write to, and move it onto `path` once the block succeeds. A crash
    or an error mid-write then leaves the old file untouched instead of half-written.
    """
    path = pathlib.Path(path)
    # the temporary file keeps the full name at the end, so that writers that pick the format by the extension
    # still recognize it
    tmp = path.with_name(f'.{secrets.token_hex(4)}.{path.name}')
    try:
        yield tmp
        with open(tmp, 'r+b') as f:
            os.fsync(f.fileno())
        # the replaced file would otherwise take its permissions with it
        if path.exists():
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
