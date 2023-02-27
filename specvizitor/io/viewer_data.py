import logging
import pathlib

logger = logging.getLogger(__name__)


def get_filename(directory, search_mask: str, object_id) -> pathlib.Path | None:
    """ Find a file for a given search mask and object ID. If more than one filename is matched to the search mask,
    return the first item from an alphabetically ordered list of matched filenames.

    @param directory: the directory where the search is performed
    @param search_mask: the search mask
    Must contain `{}` to indicate the place for ID insertion. Examples: `{}.fits`, `*{}.1D.fits`, `*{}*`
    @param object_id: the object ID
    @return: the file name matched to the search mask
    """

    if '{}' not in search_mask:
        logger.error('Invalid search mask: `{}`. The search mask must contain `{{}}` to indicate the place for ID '
                     'insertion'.format(search_mask))
        return

    matched_filenames = sorted(list(pathlib.Path(directory).glob(search_mask.format(object_id))))

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
