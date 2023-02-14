import logging
import pathlib
from dataclasses import dataclass
from platformdirs import user_config_dir, user_cache_dir

import pandas as pd
from astropy.table import Table

from .utils.params import LocalFile, Config, Cache
from .io import loader, writer


logger = logging.getLogger(__name__)


@dataclass
class RuntimeData:
    config_file: LocalFile = LocalFile(user_config_dir('specvizitor'), signature='Configuration file')
    cache_file: LocalFile = LocalFile(user_cache_dir('specvizitor'), signature='Cache')

    config: Config = Config.read(config_file)
    cache: Cache = Cache.read(cache_file)

    output_path: pathlib.Path | None = None  # the path to the output (a.k.a. inspection) file
    cat: Table | None = None                 # the catalogue
    df: pd.DataFrame | None = None           # inspection results

    j: int = None  # the index of the current object

    @property
    def id(self) -> int | None:
        """
        @return: the ID of the current object.
        """
        try:
            return self.df.index[self.j]
        except (TypeError, IndexError):
            return

    @property
    def n_objects(self) -> int | None:
        """
        @return: the total number of objects loaded to the GUI.
        """
        return len(self.df)

    def create(self):
        """
        Create a new dataframe containing:
            - a column of IDs;
            - a column for user comments;
            - one column per each checkbox.
        """
        df = pd.DataFrame(index=self.cat['id']).sort_index()
        df['comment'] = ''
        for i, cname in enumerate(self.config.review_form.checkboxes.keys()):
            df[cname] = False

        self.df = df

    def read(self):
        """ Read the inspection file and store inspection data to the dataframe. If the catalogue hasn't been already
        initialized, load it from the disk. If unsuccessful, create a new catalogue with a single column of IDs given
        by the inspection file.
        """
        if self.output_path is not None:
            # TODO: validate the input
            df = pd.read_csv(self.output_path, index_col='id')
            df['comment'] = df['comment'].fillna('')

            # update the checkboxes
            checkboxes = {key: value for key, value in self.config.review_form.checkboxes.items() if key in df.columns}
            for cname in df.columns:
                if pd.api.types.is_bool_dtype(df[cname]) and cname not in checkboxes.keys():
                    checkboxes[cname] = cname.capitalize()

            self.config.review_form.checkboxes = checkboxes
            self.config.save(self.config_file)

            self.df = df

            if self.cat is None:
                # load the catalogue
                cat = loader.load_cat(self.config.loader.cat.filename,
                                      translate=self.config.loader.cat.translate)

                if cat is None:
                    # create a catalogue with a single column of IDs
                    cat = Table([self.df.index.values], names=('id',))
                    cat.add_index('id')

                self.cat = cat

    def save(self):
        """ Save the inspection results to the output file.
        """
        if self.output_path is not None:
            writer.save(self.df, self.output_path)
            logger.info('Project saved (path: {})'.format(self.output_path))
