import logging
import pathlib
import re

import numpy as np

logger = logging.getLogger(__name__)


def get_filename(directory, pattern: str, object_id) -> pathlib.Path | None:
    """ Find a file for a given pattern and object ID. If more than one filename is matched to the pattern,
    return the first item from an alphabetically ordered list of matched filenames.

    @param directory: the directory where the search is performed
    @param pattern: the pattern used to match filenames
    @param object_id: the object ID
    @return: the file name matched to the pattern
    """

    matched_to_id = sorted(pathlib.Path(directory).glob(f'*{object_id}*'))
    matched_filenames = [p for p in matched_to_id if re.search(pattern, str(p))]

    if matched_filenames:
        return matched_filenames[0]
    else:
        return


def get_id(filename, pattern: str) -> str | None:
    """ Parse a file name to get the object ID. If more than one match is found, returns the longest match (a typical
    case for integer IDs).

    @param filename: the file name to parse
    @param pattern: the pattern used to find the object ID
    @return: the object ID
    """

    matches: list[str] = re.findall(pattern, pathlib.Path(filename).name)

    if matches:
        return max(matches, key=len)
    else:
        return


def get_id_list(directory, id_pattern: str) -> np.ndarray | None:

    # retrieve IDs from the data directory
    data_files = sorted(pathlib.Path(directory).glob('*'))
    obj_ids = [get_id(p, id_pattern) for p in data_files]
    obj_ids = np.array([i for i in obj_ids if i is not None])

    try:
        # convert IDs to int
        obj_ids = obj_ids.astype(int)
        logger.info('Converted IDs to int')
    except ValueError:
        logger.info('Converted IDs to str')

    obj_ids = np.unique([i for i in obj_ids if i is not None])

    if not obj_ids.size:
        logger.error('No IDs retrieved from the data directory')
        return

    return obj_ids
