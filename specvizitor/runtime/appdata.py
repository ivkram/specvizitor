import logging
import pathlib
from dataclasses import dataclass
from platformdirs import user_config_dir, user_cache_dir

import pandas as pd
from astropy.table import Table

from ..utils.params import LocalFile
from .config import Config
from .cache import Cache
from ..io import catalogue, output


logger = logging.getLogger(__name__)


@dataclass
class AppData:
    config_file: LocalFile = LocalFile(user_config_dir('specvizitor'), full_name='Configuration file')
    cache_file: LocalFile = LocalFile(user_cache_dir('specvizitor'), full_name='Cache')

    config: Config = Config.read(config_file, path_to_default='default_config.yml')
    cache: Cache = Cache.read(cache_file)

    output_path: pathlib.Path | None = None  # the path to the output (a.k.a. inspection) file
    cat: Table | None = None                 # the catalogue
    df: pd.DataFrame | None = None           # inspection results

    j: int = None  # the index of the current object

    @property
    def id(self) -> int | str | None:
        """
        @return: the ID of the current object.
        """
        try:
            current_id = self.df.index[self.j]
        except (TypeError, IndexError):
            return

        if pd.api.types.is_integer(current_id):
            # converting from int64 to int
            return int(current_id)

        return current_id

    @property
    def n_objects(self) -> int | None:
        """
        @return: the total number of objects loaded to the GUI.
        """
        return len(self.df)

    def create(self):
        """ Create a dataframe for storing inspection results.
        """
        if self.cat is None:
            logger.error("Failed to create a new dataframe for storing inspection results: the catalogue is not loaded"
                         "to the memory")
            return

        self.df = output.create(self.cat['id'], self.config.review_form.checkboxes)

    def read(self):
        """ Read the inspection file and load inspection data to the dataframe. If the catalogue hasn't been already
        initialized, load it from the disk. If unsuccessful, create a new catalogue with a single column of IDs given
        by the inspection file.
        """
        if self.output_path is None:
            logger.error("Failed to read the inspection file: the file path is not specified")
            return

        self.df = output.read(self.output_path)

        if self.cat is None:
            # load the catalogue
            cat = catalogue.load_cat(self.config.loader.cat.filename, translate=self.config.loader.cat.translate)

            # create a catalogue with a single column of IDs
            if cat is None:
                cat = catalogue.create_cat(self.df.index.values)

            self.cat = cat

    def save(self):
        """ Save inspection results to the output file.
        """
        if self.output_path is None:
            logger.error("Failed to save the inspection results: the output path is not specified")
            return

        output.save(self.df, self.output_path)
        logger.info('Project saved (path: {})'.format(self.output_path))
