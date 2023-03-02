import logging
import pathlib
import re

import numpy as np

logger = logging.getLogger(__name__)


def get_filename(directory, pattern: str, object_id) -> pathlib.Path | None:
    """ Find a file for a given pattern and a given object ID. If more than one file name is matched to the pattern,
    return the first item from an alphabetically ordered list of matched file names.

    @param directory: the directory where the search is performed
    @param pattern: the pattern used to match file names
    @param object_id: the object ID
    @return: the file name matched to the pattern
    """

    matched_to_id = sorted(pathlib.Path(directory).glob(f'*{object_id}*'))
    matched_filenames = [p for p in matched_to_id if re.search(pattern, str(p))]

    if matched_filenames:
        return matched_filenames[0]
    else:
        return


def get_id_from_filename(filename, pattern: str) -> str | None:
    """ Extract the object ID from a file name using a pattern. If more than one ID is matched to the pattern, return
    the longest match (a typical case for integer IDs).

    @param filename: the file name to parse
    @param pattern: the pattern (a regular expression) used to match the ID
    @return: the matched ID
    """

    try:
        matches: list[str] = re.findall(pattern, pathlib.Path(filename).name)
    except re.error:
        return

    if matches:
        return max(matches, key=len)
    else:
        return


def get_ids_from_dir(directory, id_pattern: str) -> np.ndarray | None:
    """ Extract IDs from a directory using a pattern.
    @param directory: the directory where the search for IDs is performed
    @param id_pattern: the pattern (a regular expression) used to match IDs
    @return: a list of matched IDs
    """

    data_files = sorted(pathlib.Path(directory).glob('*'))  # includes subdirectories, if any
    ids = [get_id_from_filename(p, id_pattern) for p in data_files]
    ids = np.array([i for i in ids if i is not None])

    try:
        # convert IDs to int
        ids = ids.astype(int)
        logger.info('Converted IDs to int')
    except ValueError:
        pass

    # remove ID duplicates
    ids = np.unique(ids)

    if not ids.size:
        logger.error('No IDs retrieved from the data directory')
        return

    return ids
