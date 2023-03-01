import logging
import pathlib

import numpy as np
from astropy.io import fits
from astropy.table import Table

from . import viewer_data

logger = logging.getLogger(__name__)


def load_cat(filename=None,
             translate: dict[str, list[str]] | None = None,
             data_folder=None,
             id_pattern=r'\d+') -> [Table, None]:

    """ Read and filter the catalogue.
    @param filename: the catalogue filename
    @param translate:
    @param data_folder:
    @param id_pattern:
    @return: the processed catalogue
    """

    if filename is None:
        logger.warning('Catalogue filename not specified')
        return

    # load the catalogue
    try:
        cat = Table(fits.getdata(filename))
    except OSError:
        logger.error('Failed to load the catalogue')
        return

    # rename columns
    if translate is not None:
        for cname, cname_synonyms in translate.items():
            for syn in cname_synonyms:
                if syn in cat.colnames:
                    cat.rename_column(syn, cname)
                    break

    # check that the ID column is present in the catalogue
    if 'id' not in cat.colnames:
        logger.error(column_not_found_message('id', translate))
        return
    cat.add_index('id')

    if data_folder is not None:
        # retrieve IDs from the data folder
        data_files = sorted(pathlib.Path(data_folder).glob('*'))
        obj_ids = [viewer_data.get_id(p, id_pattern) for p in data_files]
        obj_ids = np.array([i for i in obj_ids if i is not None])

        try:
            # convert IDs to int
            obj_ids = obj_ids.astype(int)
            logger.info('Converted IDs to int')
        except ValueError:
            logger.info('Converted IDs to str')

        obj_ids = np.unique([id_ for id_ in obj_ids if id_ is not None])

        if not obj_ids.size:
            logger.error('No IDs retrieved from the data folder')
            return

        # filter objects based on the list of IDs
        cat = cat[np.in1d(cat['id'], obj_ids, assume_unique=True)]

    if len(cat) == 0:
        logger.error('The processed catalogue is empty')
        return

    return cat


def column_not_found_message(cname: str, translate: dict[str, list[str]] | None = None) -> str:
    """ Create the `column not found` message.
    @param cname: the column name
    @param translate:
    @return: the message
    """

    if translate is None or cname not in translate:
        return '`{}` column not found'.format(cname)
    else:
        return '`{}` column and its equivalences ({}) not found'.format(cname, ", ".join(translate[cname]))
