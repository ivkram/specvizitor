import logging
import pathlib
from dataclasses import dataclass

from .io.catalog import Catalog
from .io.inspection_data import InspectionData

logger = logging.getLogger(__name__)


@dataclass
class AppData:

    inspection_file: pathlib.Path | None = None
    cat: Catalog | None = None
    inspection_data: InspectionData | None = None

    j: int = None  # the index of the current object
    cat_entry: Catalog | None = None  # the catalog entry of the current object

    def create(self, **kwargs):
        """ Initialize the inspection data object.
        """
        if self.cat is None:
            logger.error("Failed to initialize inspection data: Catalog not loaded")
            return

        ids = [list(self.cat.get_col(ind)) for ind in self.cat.indices]
        self.inspection_data = InspectionData.create(*ids, **kwargs)
        logger.info(f"Inspection file created (path: {self.inspection_file})")

    def read(self):
        """ Read the inspection file.
        """
        if self.inspection_file is None:
            logger.error("Failed to read the inspection file: File path not specified")
            return

        self.inspection_data = InspectionData.read(self.inspection_file)
        logger.info(f"Inspection file loaded (path: {self.inspection_file})")

    def save(self):
        """ Save inspection data to the inspection file.
        """
        if self.inspection_file is None:
            logger.error("Failed to save the inspection data: File path not specified")
            return

        if self.inspection_data.write(self.inspection_file):
            logger.info(f"Inspection file saved (path: {self.inspection_file})")

    def select(self, j: int):
        """ Make the object at index `j` the current one.
        """
        self.j = j
        self.cat_entry = self.cat.get_cat_entry(self.inspection_data.get_id(j, full=True))
