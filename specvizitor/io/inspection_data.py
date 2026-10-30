from astropy.table import Table
import numpy as np
import pandas as pd

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import logging
import pathlib


logger = logging.getLogger(__name__)

REDSHIFT_FILL_VALUE = -1.0


class FieldType(Enum):
    """ The type of a user-defined inspection field. An inspection file carries no schema, so the type is
    inferred from the column's dtype.
    """
    BOOLEAN = 'boolean'
    INTEGER = 'integer'
    FLOAT = 'float'
    TEXT = 'text'

    @classmethod
    def of(cls, column: pd.Series) -> 'FieldType':
        if pd.api.types.is_bool_dtype(column):
            return cls.BOOLEAN
        if pd.api.types.is_integer_dtype(column):
            return cls.INTEGER
        if pd.api.types.is_float_dtype(column):
            return cls.FLOAT
        return cls.TEXT

    @property
    def dtype(self) -> str:
        # nullable integers, so that a new integer field can start out empty
        return {FieldType.BOOLEAN: 'bool', FieldType.INTEGER: 'Int64', FieldType.FLOAT: 'float64',
                FieldType.TEXT: 'object'}[self]

    @property
    def fill_value(self):
        return {FieldType.BOOLEAN: False, FieldType.INTEGER: pd.NA, FieldType.FLOAT: np.nan,
                FieldType.TEXT: ''}[self]

    def has_data(self, column: pd.Series) -> bool:
        if self is FieldType.BOOLEAN:
            return bool(column.any())
        if self is FieldType.TEXT:
            return bool((column.fillna('').astype(str).str.strip() != '').any())
        return bool(column.notna().any())


class WriterBase(ABC):
    @abstractmethod
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        pass


class CSVWriter(WriterBase):
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        df.to_csv(filename)


class FITSWriter(WriterBase):
    def write(self, df: pd.DataFrame, filename: pathlib.Path):
        t: Table = Table.from_pandas(df.reset_index())
        t.write(filename, overwrite=True)


@dataclass
class InspectionData:
    df: pd.DataFrame
    default_columns: list[str] = field(default_factory=lambda: ['starred', 'z_sviz', 'comment'])

    @staticmethod
    def _add_default_columns(df: pd.DataFrame):
        # objects starred by the user
        if 'starred' not in df.columns:
            df['starred'] = False

        # redshifts saved by the user
        if 'z_sviz' not in df.columns:
            df['z_sviz'] = REDSHIFT_FILL_VALUE

        # column for user comments
        if 'comment' not in df.columns:
            df['comment'] = ''
        else:
            df['comment'] = df['comment'].fillna('')

        return df

    @classmethod
    def create(cls, *args, flags: list[str] | None = None):
        """ Create a new instance of the InspectionData class with a Pandas dataframe containing:
              - a column of IDs;
              - a column for comments;
              - one column per each user-defined flag.
        @param flags: the list of user-defined flags
        @return: an instance of the InspectionData class
        """

        try:
            if len(args) == 1:
                index = pd.Index(args[0], name='id')
            else:
                index = pd.MultiIndex.from_arrays(args, names=('id',) + tuple(f'id{i + 1}' for i in range(1, len(args))))
        except TypeError as e:
            logger.error(f'Failed to create the inspection file: {e}')
            return None

        df = pd.DataFrame(index=index)
        df = cls._add_default_columns(df)

        review = cls(df=df)

        if flags is not None:
            for cname in flags:
                review.add_field(cname, FieldType.BOOLEAN)

        return review

    @classmethod
    def read(cls, filename: str | pathlib.Path):
        """ Read an existing inspection file
        @param filename: the input filename
        @return: an instance of the InspectionData class
        """

        # TODO: validate the input
        df = pd.read_csv(filename, index_col='id')

        i = 1
        while f'id{i + 1}' in df.columns:
            df.set_index(f'id{i + 1}', append=True, inplace=True)
            i += 1

        df = cls._add_default_columns(df)

        review = cls(df=df)
        review.reorder_columns()

        return review

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
    def ids(self):
        """ Primary IDs.
        """
        return self.df.index.get_level_values(0)

    @property
    def ids_full(self):
        """ All available IDs.
        """
        return self.df.index.values

    @property
    def ids_are_int(self) -> bool:
        return pd.api.types.is_integer_dtype(self.ids)

    @property
    def indices(self) -> list[str]:
        return self.df.index.names

    @property
    def user_defined_columns(self) -> list[str]:
        return [cname for cname in self.df.columns if cname not in self.default_columns]

    @property
    def fields(self) -> dict[str, FieldType]:
        """ User-defined inspection fields and their types.
        """
        return {cname: FieldType.of(self.df[cname]) for cname in self.user_defined_columns}

    @property
    def flag_columns(self) -> list[str]:
        return [cname for cname, field_type in self.fields.items() if field_type is FieldType.BOOLEAN]

    @property
    def n_starred(self) -> int:
        return self.df["starred"].sum()

    def add_field(self, name: str, field_type: FieldType):
        self.df[name] = pd.Series(field_type.fill_value, index=self.df.index, dtype=field_type.dtype)

    def reorder_columns(self):
        self.df = self.df[self.default_columns + self.user_defined_columns]

    def rename_columns(self, new_names: dict[str, str]):
        # all at once, so that two columns can swap their names
        for old_name in new_names:
            if old_name not in self.user_defined_columns:
                logger.error(f"Failed to rename a column: Column not found (column: {old_name})")
                return
        self.df.rename(columns=new_names, inplace=True)

    def delete_column(self, column_name: str):
        if column_name not in self.user_defined_columns:
            logger.error(f"Failed to delete a column: Column not found (column: {column_name})")
            return
        self.df.drop(column_name, axis=1, inplace=True)

    def to_list(self):
        return self.df.values.tolist()

    def has_data(self, column_name: str) -> bool:
        if column_name == 'starred' or column_name in self.user_defined_columns:
            column = self.df[column_name]
            return FieldType.of(column).has_data(column)

        logger.warning(f"Cannot determine if a column has data or not (column: {column_name})")
        return True

    def get_value(self, j: int, cname: str):
        return self.df.iat[j, self.df.columns.get_loc(cname)]

    def get_id(self, j: int, full=False) -> str | int | tuple | None:
        try:
            obj_id = self.ids[j] if not full else self.ids_full[j]
        except (TypeError, IndexError):
            return None

        if self.ids_are_int and not isinstance(obj_id, tuple):
            # convert int64 to int
            obj_id = int(obj_id)

        return obj_id

    def get_id_loc(self, obj_id: str | int) -> int:
        if self.ids_are_int:
            obj_id = int(obj_id)

        j = self.df.index.get_loc(obj_id)
        if isinstance(j, slice):
            j = j.start  # use the first available secondary ID
        elif isinstance(j, np.ndarray):
            j = np.argmax(j)

        return int(j)

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
