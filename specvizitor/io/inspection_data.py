import numpy as np
import pandas as pd

from dataclasses import dataclass
import logging
import pathlib


logger = logging.getLogger(__name__)


@dataclass
class InspectionData:
    df: pd.DataFrame

    @classmethod
    def create(cls, ids, flags: list[str] | None):
        """ Create a new instance of the InspectionData class with a dataframe containing:
              - a column of IDs;
              - a column for comments;
              - one column per each user-defined flag.
        @param ids: the list of IDs
        @param flags: the list of user-defined flags
        @return: an instance of the InspectionData class
        """

        df = pd.DataFrame(index=ids).sort_index()
        df['starred'] = False
        df['comment'] = ''

        if flags is not None:
            for cname in flags:
                df[cname] = False

        return cls(df=df)

    @classmethod
    def read(cls, filename: str | pathlib.Path):
        """ Read an existing inspection file
        @param filename: the input filename
        @return: an instance of the InspectionData class
        """

        # TODO: validate the input
        df = pd.read_csv(filename, index_col='id')

        if 'starred' not in df.columns:
            df['starred'] = False

        df['comment'] = '' if 'comment' not in df.columns else df['comment'].fillna('')

        notes = cls(df=df)
        notes.reorder_columns()

        return notes

    def save(self, filename: str | pathlib.Path):
        """ Save inspection data to the output file.
        @param filename: the output filename
        @return: None
        """

        self.df.to_csv(filename, index_label='id')

    @property
    def ids(self) -> np.array:
        return self.df.index.values

    @property
    def default_columns(self) -> list[str]:
        return ['starred', 'comment']

    @property
    def user_defined_columns(self) -> list[str]:
        return [cname for cname in self.df.columns if cname not in self.default_columns]

    @property
    def flag_columns(self) -> list[str]:
        return [cname for cname in self.user_defined_columns if pd.api.types.is_bool_dtype(self.df[cname])]

    @property
    def n_objects(self) -> int | None:
        """
        @return: the total number of objects under inspection.
        """
        return len(self.df)

    @property
    def has_starred(self) -> bool:
        return self.df['starred'].sum() > 0

    def reorder_columns(self):
        self.df = self.df[self.default_columns + self.user_defined_columns]

    def get_single_value(self, j: int, cname: str):
        return self.df.iat[j, self.df.columns.get_loc(cname)]

    def get_id_loc(self, obj_id):
        return self.df.index.get_loc(obj_id)

    def get_checkboxes(self, default_checkboxes: dict[str, str] | None = None) -> dict[str, str]:
        """ Get the full description of checkboxes to be displayed in the review form (column name + label). By default,
        each checkbox is automatically assigned a label by a simple capitalization of the column name, e.g. a flag named
        `extended` would become a checkbox with a label `Extended`. The `default_checkboxes` parameter is used as a
        lookup table to overrides these labels.
        @param default_checkboxes: the description of default checkboxes used to override automatically created labels
        @return: a dictionary describing the checkboxes to be displayed in the review form
        """

        checkboxes = {}

        for cname in self.flag_columns:
            checkboxes[cname] = cname.capitalize()

        if default_checkboxes is not None:
            checkboxes.update({key: value for key, value in default_checkboxes.items()
                               if key in self.user_defined_columns})

        return checkboxes

    def update_single_value(self, j: int, cname: str, value):
        self.df.iat[j, self.df.columns.get_loc(cname)] = value
