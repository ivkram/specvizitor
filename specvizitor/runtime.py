import logging
import pathlib
from dataclasses import dataclass
from platformdirs import user_config_dir, user_cache_dir

import pandas as pd
from astropy.table import Table

from .utils.params import LocalFile, Config, Cache


logger = logging.getLogger(__name__)


@dataclass
class RuntimeData:
    config_file: LocalFile = LocalFile(user_config_dir('specvizitor'), save_msg='Configuration file updated')
    cache_file: LocalFile = LocalFile(user_cache_dir('specvizitor'), save_msg='Cache file updated')

    config: Config = Config.read(config_file, path_to_default='default_config.yml')
    cache: Cache = Cache.read(cache_file)

    project: pathlib.Path = None  # path to the output file
    cat: Table = None  # catalogue
    df: pd.DataFrame = None  # output data

    j: int = None  # index of the current object

    @property
    def id(self) -> int | None:
        try:
            return self.cat['id'][self.j]
        except (TypeError, IndexError):
            return

    def save(self):
        if self.project is not None:
            self.df.to_csv(self.project, index_label='id')
            logger.info('Project saved (path: {})'.format(self.project))
