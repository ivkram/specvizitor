import numpy as np

import logging
import pathlib
import re


__all__ = [
    "get_ids_from_dir"
]

logger = logging.getLogger(__name__)


def _get_id_from_filename(filename, pattern: str) -> str | None:
    """Extract the object ID from a file name using regular expressions. If more than one ID is matched to the pattern,
    return the longest match.

    @param filename: the file name to parse
    @param pattern: the regular expression used to match the ID
    @return: the matched ID
    """

    try:
        matches: list[str] = re.findall(pattern, pathlib.Path(filename).name)
    except re.error:
        return None

    if not matches:
        return None

    return max(matches, key=len)


def get_ids_from_dir(directory, id_pattern: str = r'\d+', recursive: bool = False) -> np.ndarray | None:
    """Extract IDs from a directory using regular expressions.
    @param directory: the directory where the search for IDs is performed
    @param id_pattern: the regular expression used to match the IDs
    @param recursive: if True, search the directory recursively
    @return: a list of matched IDs
    """

    data_files = sorted(pathlib.Path(directory).glob('**/*' if recursive else '*'))
    ids = [_get_id_from_filename(p, id_pattern) for p in data_files]
    ids = np.array([i for i in ids if i is not None])

    try:
        ids = ids.astype(np.int64)  # convert IDs to int
    except ValueError:
        pass

    ids = np.unique(ids)  # remove duplicates

    if not ids.size:
        logger.error("No IDs retrieved from the data directory")
        return

    return ids
