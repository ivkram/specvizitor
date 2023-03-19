from astropy.table import Table
import pandas as pd

from dataclasses import dataclass
import logging
import pathlib

from .config import Config, Docks, SpectralLines, Cache
from .io import catalogue
from .io.inspection_data import InspectionData

logger = logging.getLogger(__name__)


@dataclass
class AppData:
    config: Config
    docks: Docks
    lines: SpectralLines

    cache: Cache

    output_path: pathlib.Path | None = None  # the path to the output (a.k.a. inspection) file
    cat: Table | None = None                 # the catalogue
    notes: InspectionData | None = None      # inspection results

    j: int = None  # the index of the current object

    @property
    def id(self) -> int | str | None:
        """
        @return: the ID of the current object.
        """
        try:
            current_id = self.notes.ids[self.j]
        except (TypeError, IndexError):
            return

        if pd.api.types.is_integer(current_id):
            # converting from int64 to int
            return int(current_id)

        return current_id

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

        if self.cat is None:
            # load the catalogue
            cat = catalogue.load_cat(self.config.catalogue.filename, translate=self.config.catalogue.translate)

            # create a catalogue with a single column of IDs
            if cat is None:
                cat = catalogue.create_cat(self.notes.ids)

            self.cat = cat

    def save(self):
        """ Save inspection data to the output file.
        """
        if self.output_path is None:
            logger.error("Failed to save the inspection data: the output path is not specified")
            return

        self.notes.save(self.output_path)
        logger.info('Project saved (path: {})'.format(self.output_path))
