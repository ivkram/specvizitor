from astropy.table import Table, Row

import logging

logger = logging.getLogger(__name__)


def get_table_indices(t: Table) -> tuple:
    if t.meta.get('indices'):
        return t.meta['indices']
    else:
        return tuple(ind.columns[0].name for ind in t.indices)


def loc_full(t: Table | Row, obj_id: str | int | tuple, indices: tuple | None = None):
    """ Retrieve rows by (multi)index.
    """

    if isinstance(obj_id, str) or isinstance(obj_id, int):
        return t.loc[obj_id]  # standard .loc method
    elif isinstance(obj_id, tuple):
        if not obj_id:
            return t  # exit recursion

        if indices is None:
            indices = get_table_indices(t)
            if len(indices) != len(obj_id):
                raise KeyError

        if isinstance(t, Row):
            if t[indices[0]] == obj_id[0]:
                return t
            else:
                raise IndexError

        return loc_full(t.loc[indices[0], obj_id[0]], obj_id[1:], indices[1:])
    else:
        raise TypeError(f'Unknown object ID type: {type(obj_id)}')


def translate(t: Table, dictionary: dict):
    for cname, cname_synonyms in dictionary.items():
        if cname in t.colnames:
            continue
        for syn in cname_synonyms:
            if syn in t.colnames:
                t.rename_column(syn, cname)
                break


def column_not_found_message(cname: str, dictionary: dict[str, list[str]] | None = None) -> str:
    """ Create the `column not found` message.
    @param cname: the column name
    @param dictionary:
    @return: the message
    """

    if dictionary is None or cname not in dictionary:
        return '`{}` column not found'.format(cname)
    else:
        return '`{}` column and its aliases ({}) not found'.format(cname, ", ".join(dictionary[cname]))
