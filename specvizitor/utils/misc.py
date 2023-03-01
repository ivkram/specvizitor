from astropy.table import Table


def translate(t: Table, dictionary: dict):
    for cname, cname_synonyms in dictionary.items():
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
        return '`{}` column and its equivalences ({}) not found'.format(cname, ", ".join(dictionary[cname]))
