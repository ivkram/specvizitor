import logging
import pathlib

import numpy as np
from astropy.io import fits
from astropy.table import Table


logger = logging.getLogger(__name__)


def get_grizli_id(filename: pathlib.Path) -> str:
    """
    Retrieve a grizli ID from the file name. The file can be any of the grizli fit products.
    @param filename: `~pathlib.Path`
        The file name to parse.
    @return: str
        The object ID.
    """
    return filename.name.split('_')[1].split('.')[0]


def load_cat(filename: pathlib.Path, colnames=None, translate=None,
             data_folder=None, filename_parser=get_grizli_id) -> [Table, None]:
    """
    Read and filter the input catalogue.

    @return:
        The processed catalogue.
    """

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
        if translate is None or 'id' not in translate:
            logger.error('`id` column not found')
        else:
            logger.error('`id` column or its equivalences ({}) not found'.format(", ".join(translate['id'])))
        return

    # select columns
    if colnames is not None:
        selected_columns = ['id']
        for cname in colnames:
            if cname in cat.colnames:
                selected_columns.append(cname)
        cat = cat[selected_columns]

    # scan the data folder and retrieve a list of IDs
    if data_folder is not None:
        spec_files = sorted(pathlib.Path(data_folder).glob('**/*.fits'))
        spec_ids = np.unique([int(filename_parser(p)) for p in spec_files])

        if not spec_ids.size:
            logger.error('No IDs retrieved from the data folder')
            return

        # filter objects using a list of IDs retrieved from the data folder
        cat = cat[np.in1d(cat['id'], spec_ids, assume_unique=True)]

    if len(cat) == 0:
        logger.error('The processed catalogue is empty')
        return

    return cat
