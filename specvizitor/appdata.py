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
    review: InspectionData | None = None      # inspection results

    j: int = None  # the index of the current object

    def create(self, **kwargs):
        """ Initialize the inspection data object.
        """
        if self.cat is None:
            logger.error("Failed to initialize inspection data: the catalogue not loaded to the memory")
            return

        self.review = InspectionData.create(self.cat['id'], **kwargs)

    def read(self):
        """ Read the inspection file.
        """
        if self.output_path is None:
            logger.error("Failed to read the inspection file: the file path not specified")
            return

        self.review = InspectionData.read(self.output_path)

    def save(self):
        """ Save inspection data to the output file.
        """
        if self.output_path is None:
            logger.error("Failed to save the inspection data: the output path not specified")
            return

        self.review.write(self.output_path)
