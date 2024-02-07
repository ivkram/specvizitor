from astropy.io import fits
from astropy.table import Table, Row
import numpy as np

import logging

from .viewer_data import get_ids_from_dir
from ..utils import table_tools
from ..utils.widgets import FileBrowser

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
        cat = Table.read(filename)
    except OSError as e:
        logger.error(f'Failed to load the catalogue: {e}')
        return

    # rename columns
    if translate is not None:
        table_tools.translate(cat, translate)
        cat.meta['aliases'] = translate

    # check that the ID column is present in the catalogue
    if 'id' not in cat.colnames:
        logger.error(table_tools.column_not_found_message('id', translate))
        return

    if data_dir is not None:
        ids = get_ids_from_dir(data_dir, id_pattern)
        if ids is None:
            return

        # filter objects based on the list of IDs
        cat = cat[np.in1d(cat['id'], ids, assume_unique=False)]

    if len(cat) == 0:
        logger.error('The processed catalogue is empty')
        return

    # adding indices
    cat.add_index('id')
    indices = ['id']
    for i in range(2, 11):
        if f'id{i}' in cat.colnames:
            cat.add_index(f'id{i}')
            indices.append(f'id{i}')
    cat.meta['indices'] = indices

    return cat


def create_cat(ids) -> Table:
    colnames = ('id',)
    if isinstance(ids[0], tuple):
        colnames += tuple(f'id{i + 1}' for i in range(1, len(ids[0])))
        table_data = list(zip(*ids))
    else:
        table_data = [ids]

    cat = Table(table_data, names=colnames)

    for cname in colnames:
        cat.add_index(cname)

    return cat


def get_obj_cat(cat: Table, obj_id: str | int | tuple) -> Row | None:
    obj_cat = None
    try:
        obj_cat = table_tools.loc_full(cat, obj_id)
    except KeyError:
        logger.error(f'Object not found in the catalogue (ID: {obj_id})')
    except TypeError as msg:
        logger.error(msg)

    if isinstance(obj_cat, Table):
        logger.error(f'Object corresponds to multiple entries in the catalogue (ID: {obj_id})')
        obj_cat = None

    return obj_cat


def cat_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                       default_path=default_path, **kwargs)
