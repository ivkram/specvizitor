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

    filenames = sorted(pathlib.Path(directory).glob('*'))

    # match to the pattern
    matched_to_pattern = [p for p in filenames if re.search(pattern, str(p))]

    # match to the ID
    if isinstance(object_id, int):
        # make sure that we don't match e.g. '1123' or '1234' to '123' (but match '0123')
        matched_ids = [re.findall(r'\d*{}\d*'.format(object_id), str(p)) for p in matched_to_pattern]
        matched = [p for i, p in enumerate(matched_to_pattern)
                   if matched_ids[i] and str(max(matched_ids[i], key=len)).lstrip('0') == str(object_id)]
    else:
        matched = [p for p in matched_to_pattern if re.search(f'{object_id}', str(p))]

    if matched:
        return matched[0]
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
