import pathlib
import pandas as pd


def save(df: pd.DataFrame, filename: str | pathlib.Path):
    df.to_csv(filename, index_label='id')
