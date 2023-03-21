from astropy.table import Table
import numpy as np
import pandas as pd

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
import pathlib


logger = logging.getLogger(__name__)


class WriterBase(ABC):
    @abstractmethod
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        pass


class CSVWriter(WriterBase):
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        df.to_csv(filename, index_label='id')


class FITSWriter(WriterBase):
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        t: Table = Table.from_pandas(df)
        t.write(filename, overwrite=True)


@dataclass
class InspectionData:
    df: pd.DataFrame
    default_columns: list[str] = field(default_factory=lambda: ['starred', 'comment'])

    @classmethod
    def create(cls, ids, flags: list[str] | None):
        """ Create a new instance of the InspectionData class with a Pandas dataframe containing:
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

    def write(self, filename: pathlib.Path, fmt: str = 'csv'):
        """ Write inspection data to the output file.
        @param filename: the output filename
        @param fmt: the output format
        @return: None
        """

        writers: dict[str, type[WriterBase]] = {
            'csv': CSVWriter,
            'fits': FITSWriter
        }

        if writers.get(fmt):
            writers[fmt]().write(self.df, filename)
        else:
            logger.error(f"Unknown output format: {fmt}")

    @property
    def n_objects(self) -> int | None:
        """
        @return: the total number of objects under inspection.
        """
        return len(self.df)

    @property
    def ids(self) -> np.array:
        return self.df.index.values

    @property
    def ids_are_int(self) -> bool:
        return pd.api.types.is_integer_dtype(self.df.index)

    @property
    def user_defined_columns(self) -> list[str]:
        return [cname for cname in self.df.columns if cname not in self.default_columns]

    @property
    def flag_columns(self) -> list[str]:
        return [cname for cname in self.user_defined_columns if pd.api.types.is_bool_dtype(self.df[cname])]

    @property
    def has_starred(self) -> bool:
        return self.df['starred'].sum() > 0

    def reorder_columns(self):
        self.df = self.df[self.default_columns + self.user_defined_columns]

    def get_value(self, j: int, cname: str):
        return self.df.iat[j, self.df.columns.get_loc(cname)]

    def get_id(self, j: int) -> int | str | None:
        try:
            obj_id = self.ids[j]
        except (TypeError, IndexError):
            return

        if self.ids_are_int:
            # convert from int64 to int
            obj_id = int(obj_id)

        return obj_id

    def get_id_loc(self, obj_id: str):
        if self.ids_are_int:
            obj_id = int(obj_id)

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

    def update_value(self, j: int, cname: str, value):
        self.df.iat[j, self.df.columns.get_loc(cname)] = value

    def validate_id(self, obj_id: str | int) -> bool:
        if self.ids_are_int:
            try:
                obj_id = int(obj_id)
            except ValueError:
                logger.error(f'Invalid ID: {obj_id}')
                return False

        if obj_id not in self.ids:
            logger.error(f'ID `{obj_id}` not found')
            return False

        return True

    def validate_index(self, index: int) -> bool:

        if not 0 < index <= self.n_objects:
            logger.error(f'Index `{index}` out of range')
            return False

        return True
