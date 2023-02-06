import logging
import pathlib

import numpy as np
from astropy.io import fits
from astropy.table import Table


def load_phot_cat(*args, **kwargs) -> [Table, None]:
    """
    Read and filter the photometric catalogue.

    Filtering is done in two steps. First, objects with no data found among the grizli fit products are excluded from
    the final catalogue. Second, objects are filtered based on the list(s) of IDs passed to the function (optional).
    @param ids:
        Array of IDs used to additionally filter the catalogue.
    @param kwargs: dict
        The configuration data. Must contain a path to the original photometric catalogue and a path to the grizli fit
        products.
    @return:
        The photometric catalogue.
    """

    # read the photometric catalogue
    cat = Table(fits.getdata(pathlib.Path(kwargs['data']['phot_cat']).resolve()))

    # scan a directory with grizli fit products
    spec_files = sorted(pathlib.Path(kwargs['data']['grizli_fit_products']).glob('*.fits'))
    spec_ids = np.unique([int(get_grizli_id(p)) for p in spec_files])

    if spec_ids.size == 0:
        raise FileNotFoundError("No grizli fit products were found")

    # filter objects using the obtained IDs
    cat = cat[np.in1d(cat['id'], spec_ids, assume_unique=True)]

    # filter objects using `ids`
    for a in args:
        cat = cat[np.in1d(cat['id'], a, assume_unique=True)]

    if not cat:
        raise ValueError("The input catalogue is empty")

    return cat


def get_grizli_id(filename: pathlib.Path) -> str:
    """
    Cut out the grizli ID from the file name. The file can be any of the grizli fit products.
    @param filename: `~pathlib.Path`
        The file name to parse.
    @return: str
        The object ID.
    """
    return filename.name.split('_')[1].split('.')[0]
