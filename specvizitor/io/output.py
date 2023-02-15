import pathlib
import pandas as pd


def create(ids, checkboxes: dict[str, str] | None) -> pd.DataFrame:
    """ Create a new dataframe containing:
          - a column of IDs;
          - a column for user comments;
          - an extra column per each checkbox.
    @param ids: the list of IDs
    @param checkboxes: the checkboxes to be displayed in the review form
    @return: the dataframe for storing inspection results
    """

    df = pd.DataFrame(index=ids).sort_index()
    df['comment'] = ''

    if checkboxes is not None:
        for i, cname in enumerate(checkboxes.keys()):
            df[cname] = False

    return df


def save(df: pd.DataFrame, filename: str | pathlib.Path):
    """ Save inspection results to the output file.
    @param df: the dataframe containing inspection results
    @param filename: the output filename
    @return: None
    """

    df.to_csv(filename, index_label='id')


def get_checkboxes(df: pd.DataFrame, configured_checkboxes: dict[str, str] | None = None) -> dict[str, str]:
    """ Get checkboxes from the dataframe. By default, each checkbox is automatically assigned a label to be displayed
    in the GUI by a simple capitalization of the column name, e.g. a checkbox named `extended` will get a label
    `Extended`. The `configured_checkboxes` parameter is used to overrides these labels.
    @param df: the dataframe containing inspection results
    @param configured_checkboxes: the checkboxes used to override automatically created labels
    @return: the checkboxes parsed from the dataframe
    """

    if configured_checkboxes is None:
        checkboxes = {}
    else:
        checkboxes = {key: value for key, value in configured_checkboxes.items() if key in df.columns}

    for cname in df.columns:
        if pd.api.types.is_bool_dtype(df[cname]) and cname not in checkboxes.keys():
            checkboxes[cname] = cname.capitalize()

    return checkboxes
