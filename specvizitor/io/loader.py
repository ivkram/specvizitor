import logging
import pathlib

import numpy as np
from astropy.io import fits
from astropy.table import Table


logger = logging.getLogger(__name__)


# TODO: create FilenameParser class

def get_grizli_id(filename: pathlib.Path) -> str:
    """
    Retrieve a grizli ID from the file name. The file can be any of the grizli fit products.
    @param filename: `~pathlib.Path`
        The file name to parse.
    @return: str
        The object ID.
    """
    return filename.name.split('_')[1].split('.')[0]


def load_cat(filename=None, translate=None, data_folder=None, filename_parser=get_grizli_id) -> [Table, None]:
    """
    Read and filter the input catalogue.

    @return:
        The processed catalogue.
    """

    if filename is None:
        logger.warning('Catalogue filename not specified')
        return

    # read the input catalogue
    try:
        cat = Table(fits.getdata(filename))
    except OSError:
        logger.error('Could not load the catalogue')
        return

    # rename columns
    if translate is not None:
        for cname, cname_synonyms in translate.items():
            for syn in cname_synonyms:
                if syn in cat.colnames:
                    cat.rename_column(syn, cname)
                    break

    if 'id' not in cat.colnames:
        logger.error(column_not_found_message('id', translate))
        return
    cat.add_index('id')

    # scan the data folder
    if data_folder is not None:
        data_files = sorted(pathlib.Path(data_folder).glob('**/*.fits'))

        try:
            obj_ids = np.unique([filename_parser(p) for p in data_files])
        except IndexError:
            logger.error('An error occurred when parsing filenames in the data folder')
            return

        if not obj_ids.size:
            logger.error('No IDs retrieved from the data folder')
            return

        # filter objects using a list of IDs retrieved from the data folder
        cat = cat[np.in1d(cat['id'], obj_ids, assume_unique=True)]

    if len(cat) == 0:
        logger.error('The processed catalogue is empty')
        return

    return cat


def column_not_found_message(cname, translate=None):
    if translate is None or cname not in translate:
        return '`{}` column not found'.format(cname)
    else:
        return '`{}` column and its equivalences ({}) not found'.format(cname, ", ".join(translate[cname]))


def get_filename(directory, search_mask, object_id):
    matched_filenames = sorted(list(pathlib.Path(directory).glob(search_mask.format(object_id))))
    if matched_filenames:
        return matched_filenames[0]  # if more than one filename is matched to `search_mask`, return the first
    else:
        return
