from astropy.table import Table
from platformdirs import user_config_dir, user_cache_dir

from dataclasses import dataclass
import logging
import pathlib

from .config import Config, Docks, SpectralLines, Cache
from .io.inspection_data import InspectionData
from .utils.params import LocalFile

logger = logging.getLogger(__name__)


@dataclass
class AppData:
    config: Config
    cache: Cache

    docks: Docks
    lines: SpectralLines

    output_path: pathlib.Path | None = None  # the path to the output (a.k.a. inspection) file
    cat: Table | None = None                 # the catalogue
    notes: InspectionData | None = None      # inspection results

    j: int = None  # the index of the current object

    @classmethod
    def init_from_disk(cls, purge=False):

        user_files: dict[str, LocalFile] = {
            'config': LocalFile(user_config_dir('specvizitor'), full_name='Settings file'),
            'docks': LocalFile(user_config_dir('specvizitor'), filename='docks.yml',
                               full_name='Dock configuration file'),
            'lines': LocalFile(user_config_dir('specvizitor'), filename='lines.yml',
                               full_name='List of spectral lines'),
            'cache': LocalFile(user_cache_dir('specvizitor'), full_name='Cache file', auto_backup=False)
        }

        if purge:
            for f in user_files.values():
                f.delete()

        return cls(config=Config.read_user_params(user_files['config'], default='default_config.yml'),
                   docks=Docks.read_user_params(user_files['docks'], default='default_docks.yml'),
                   lines=SpectralLines.read_user_params(user_files['lines'], default='default_lines.yml'),
                   cache=Cache.read_user_params(user_files['cache']))

    def create(self):
        """ Create an object for storing inspection data.
        """
        if self.cat is None:
            logger.error("Failed to create a new object for storing inspection data: the catalogue is not loaded"
                         "to the memory")
            return

        self.notes = InspectionData.create(self.cat['id'], self.config.review_form.default_checkboxes)

    def read(self):
        """ Read the inspection file. If the catalogue hasn't been already initialized, load it from the disk. If
        unsuccessful, create a new catalogue with a single column of IDs given by the inspection file.
        """
        if self.output_path is None:
            logger.error("Failed to read the inspection file: the file path is not specified")
            return

        self.notes = InspectionData.read(self.output_path)

    def save(self):
        """ Save inspection data to the output file.
        """
        if self.output_path is None:
            logger.error("Failed to save the inspection data: the output path is not specified")
            return

        self.notes.write(self.output_path)
        logger.info('Project saved (path: {})'.format(self.output_path))
