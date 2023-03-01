import logging
import pathlib
import re

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


# TODO: create a FilenameParser class
def get_grizli_id(filename) -> int | None:
    """ Parse a file name to get the object ID. The file must be one of the grizli fit products.
    @param filename: the file name to parse
    @return: the object ID
    """

    try:
        return int(pathlib.Path(filename).name.split('_')[1].split('.')[0])
    except (IndexError, ValueError):
        # commented out because might be called too many times
        # logger.error('Failed to parse the file name `{}`'.format(filename))
        return
