from astropy.io import fits
from astropy.table import Table
import numpy as np

import logging

from .viewer_data import get_ids_from_dir
from ..utils import table_tools
from ..widgets.FileBrowser import FileBrowser

logger = logging.getLogger(__name__)


def read_cat(filename=None,
             translate: dict[str, list[str]] | None = None,
             data_dir=None,
             id_pattern=r'\d+') -> [Table, None]:

    """ Read and filter the catalogue.
    @param filename: the catalogue filename
    @param translate:
    @param data_dir:
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
        table_tools.translate(cat, translate)
        cat.meta['aliases'] = translate

    # check that the ID column is present in the catalogue
    if 'id' not in cat.colnames:
        logger.error(table_tools.column_not_found_message('id', translate))
        return
    cat.add_index('id')

    if data_dir is not None:
        ids = get_ids_from_dir(data_dir, id_pattern)
        if ids is None:
            return

        # filter objects based on the list of IDs
        cat = cat[np.in1d(cat['id'], ids, assume_unique=True)]

    if len(cat) == 0:
        logger.error('The processed catalogue is empty')
        return

    return cat


def create_cat(ids) -> Table:
    cat = Table([ids], names=('id',))
    cat.add_index('id')

    return cat


def cat_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                       default_path=default_path, **kwargs)
