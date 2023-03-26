from astropy.table import Table

from dataclasses import dataclass
import logging
import pathlib

from .io.inspection_data import InspectionData

logger = logging.getLogger(__name__)


@dataclass
class AppData:

    output_path: pathlib.Path | None = None  # the path to the output (a.k.a. inspection) file
    cat: Table | None = None                 # the catalogue
    notes: InspectionData | None = None      # inspection results

    j: int = None  # the index of the current object

    def create(self, **kwargs):
        """ Create an object for storing inspection data.
        """
        if self.cat is None:
            logger.error("Failed to create a new object for storing inspection data: the catalogue is not loaded"
                         "to the memory")
            return

        self.notes = InspectionData.create(self.cat['id'], **kwargs)

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
