from astropy.table import Table, Row
import numpy as np

from dataclasses import dataclass, field
import logging

from .viewer_data import get_ids_from_dir
from ..utils.widgets import FileBrowser

logger = logging.getLogger(__name__)


@dataclass
class Catalog:
    table: Table | Row
    indices: list[str] = field(default_factory=list)
    translate: dict[str, list[str]] | None = None

    def __post_init__(self):
        if isinstance(self.table, Table):
            for idx in self.indices:
                self.table.add_index(idx)

    @classmethod
    def create(cls, ids):
        colnames = ['id']
        if isinstance(ids[0], tuple):
            colnames += list(f'id{i + 1}' for i in range(1, len(ids[0])))
            table_data = list(zip(*ids))
        else:
            table_data = [ids]

        table = Table(table_data, names=colnames)
        return cls(table=table, indices=colnames)

    @classmethod
    def read(cls, filename, translate: dict[str, list[str]] | None = None, data_dir=None, id_pattern=r'\d+'):
        """ Read the catalogue from file.
        @param filename: the catalogue filename
        @param translate:
        @param data_dir:
        @param id_pattern:
        @return: the processed catalogue
        """

        if filename is None:
            logger.warning('Catalogue filename not specified')
            return

        try:
            table = Table.read(filename)  # load the catalogue
        except (OSError, ValueError) as e:
            logger.error(f'Failed to load the catalogue: {e}')
            return

        cat = cls(table=table, translate=translate)

        # check that the ID column is present in the catalogue
        try:
            id_col = cat.get_col('id')
        except KeyError as e:
            logger.error(e)
            return

        if data_dir is not None:
            ids = get_ids_from_dir(data_dir, id_pattern)
            if ids is None:
                return

            # filter objects based on the list of IDs
            cat.table = cat.table[np.in1d(cat.get_col('id'), ids, assume_unique=False)]

        if len(cat.table) == 0:
            logger.error('The processed catalogue is empty')
            return

        # add indices
        cat.add_index(id_col.name)
        for i in range(2, 11):
            try:
                id_col = cat.get_col(f'id{i}')
            except KeyError:
                break
            else:
                cat.add_index(id_col.name)

        return cat

    def __len__(self):
        return len(self.table)

    @property
    def colnames(self) -> list:
        return self.table.colnames

    @property
    def extended_colnames(self) -> list:
        colnames = self.colnames

        if self.translate:
            colnames_extension = []
            for cname, cname_aliases in self.translate.items():
                for cname_alias in cname_aliases:
                    if cname_alias in colnames:
                        colnames_extension.append(cname)
                        break
            colnames += colnames_extension

        return colnames

    @property
    def annotated_colnames(self) -> dict[str, str]:
        colnames = {cname: cname for cname in self.colnames}

        if self.translate:
            for cname, cname_aliases in self.translate.items():
                for cname_alias in cname_aliases:
                    if cname_alias in self.colnames:
                        colnames[cname_alias] = f'{cname_alias} ({cname})'
                        break

        return colnames

    def add_index(self, idx):
        self.indices.append(idx)
        self.table.add_index(idx)

    def add_column(self, data, **kwargs):
        self.table.add_column(data, **kwargs)

    def _loc_full_base(self, t: Table, indices: list, obj_id: str | int | tuple):
        if isinstance(obj_id, str) or isinstance(obj_id, int):
            return t.loc[obj_id]  # standard .loc method

        elif isinstance(obj_id, tuple):
            if not obj_id:
                return t  # exit recursion

            if len(indices) != len(obj_id):
                raise KeyError

            if isinstance(t, Row):
                if t[indices[0]] == obj_id[0]:
                    return t
                else:
                    raise KeyError

            return self._loc_full_base(t.loc[indices[0], obj_id[0]], indices[1:], obj_id[1:])
        else:
            raise TypeError(f'Unknown object ID type: {type(obj_id)}')

    def _loc_full(self, obj_id: str | int | tuple):
        """ Retrieve rows by (multi)index.
        """
        if self.indices is None:
            raise ValueError(f'Cannot locate the object: no indices found in the table (ID: {obj_id})')
        return self._loc_full_base(self.table, self.indices, obj_id)

    def get_col(self, cname: str):
        if cname not in self.extended_colnames:
            if self.translate and cname in self.translate:
                raise KeyError('`{}` column and its aliases ({}) not found'.format(cname, ", ".join(self.translate[cname])))
            else:
                raise KeyError('`{}` column not found'.format(cname))

        if cname in self.colnames:
            return self.table[cname]

        for cname_alias in self.translate[cname]:
            if cname_alias in self.colnames:
                return self.table[cname_alias]

    def get_cat_entry(self, obj_id: str | int | tuple, ignore_missing=False):
        try:
            cat_entry = self._loc_full(obj_id)
        except KeyError:
            if not ignore_missing:
                logger.error(f'Object not found in the catalogue (ID: {obj_id})')
            return None
        except (TypeError, ValueError) as e:
            logger.error(e)
            return None

        if isinstance(cat_entry, Table):
            logger.error(f'Object corresponds to multiple entries in the catalogue (ID: {obj_id})')
            return None

        return Catalog(cat_entry, indices=self.indices, translate=self.translate)


def cat_browser(default_path, **kwargs) -> FileBrowser:
    return FileBrowser(filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                       default_path=default_path, **kwargs)
