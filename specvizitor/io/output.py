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
