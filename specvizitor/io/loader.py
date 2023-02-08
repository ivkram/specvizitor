import logging
import pathlib

import numpy as np
from astropy.io import fits
from astropy.table import Table


def get_grizli_id(filename: pathlib.Path) -> str:
    """
    Retrieve a grizli ID from the file name. The file can be any of the grizli fit products.
    @param filename: `~pathlib.Path`
        The file name to parse.
    @return: str
        The object ID.
    """
    return filename.name.split('_')[1].split('.')[0]


def load_cat(filename: pathlib.Path, colnames=None, strict_search='all', synonyms=None,
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
        logging.error('Could not load the catalogue')
        return

    # select columns from the catalogue
    if colnames is not None:
        selected_columns = {}
        for cname in colnames:

            if cname in cat.colnames:
                selected_columns[cname] = cname
            elif synonyms is not None and synonyms.get(cname):
                for cname_synonym in synonyms:
                    if cname in cat.colnames:
                        selected_columns[cname] = cname_synonym
                        break

            if not selected_columns.get(cname) and (strict_search == 'all' or cname in strict_search):
                logging.error('Column `{}` or its equivalents not found in the catalogue'.format(cname))
                return

        cat = cat[list(selected_columns.values())]
        cat.rename_columns(tuple(selected_columns.values()), tuple(selected_columns.keys()))

    # scan the data folder and retrieve a list of IDs
    if data_folder is not None:
        spec_files = sorted(pathlib.Path(data_folder).glob('*.fits'))
        spec_ids = np.unique([int(filename_parser(p)) for p in spec_files])

        if not spec_ids.size:
            logging.error('No IDs retrieved from the data folder')
            return

        # filter objects using a list of IDs retrieved from the data folder
        cat = cat[np.in1d(cat['id'], spec_ids, assume_unique=True)]

    if len(cat) == 0:
        logging.error('The processed catalogue is empty')
        return

    return cat
