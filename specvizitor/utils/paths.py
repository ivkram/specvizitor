import pathlib


def absolute_path(path) -> pathlib.Path:
    # resolve() alone does not expand `~`
    return pathlib.Path(path).expanduser().resolve()
