import numpy as np
from astropy.io import fits


def write_output(comments, new_catalog):
    # write identifications in fits file

    # make sure that the comments don't get truncated
    max_len = 0
    for comment in comments:
        if len(comment) > max_len:
            max_len = len(comment)
    max_len += 1

    columns = []
    for column in input_cat_keys:
        dtype = type(input_cat_dict[column][0])

        if dtype is np.float64:
            format="D"
        elif dtype is np.int32:
            format="J"
        elif dtype is str:
            format="20A"
        else:
            format="10A"
        c = fits.Column(name=column, format=format, array=input_cat_dict[column])
        columns.append(c)

    c = fits.Column(name='comments', format=str(max_len)+"A", array=comments)
    columns.append(c)

    table_hdu = fits.BinTableHDU.from_columns(columns)
    table_hdu.writeto(new_catalog, overwrite=True)
