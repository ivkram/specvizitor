import logging
import abc
import pathlib

import numpy as np
from astropy.table import Table
from astropy.io.fits.header import Header

from .AbstractWidget import AbstractWidget

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.viewer_data import get_filename, load
from ..utils import misc


logger = logging.getLogger(__name__)


class ViewerElement(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ViewerElement, alias: str, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg
        self.alias: str = alias

        self.filename: pathlib.Path | None = None
        self.data: np.ndarray | Table | None = None
        self.meta: dict | Header | None = None

        self.layout.setContentsMargins(0, 0, 0, 0)

    def load_object(self):
        self.filename = get_filename(self.rd.config.data.dir, self.cfg.filename_pattern, self.rd.id)

        if self.filename is None:
            logger.warning('{} not found (object ID: {})'.format(self.alias, self.rd.id))
            self.data, self.meta = None, None
            return

        if self.cfg.loader_config is None:
            loader_config = {}
        else:
            loader_config = self.cfg.loader_config

        try:
            self.data, self.meta = load(self.cfg.loader, self.filename, self.alias, **loader_config)
        except TypeError as e:
            # unexpected keyword(s) passed to the loader
            logger.error(e.args[0])
            self.data, self.meta = None, None
            return

        if isinstance(self.data, Table):
            # translate the table columns
            if self.rd.config.data.translate:
                misc.translate(self.data, self.rd.config.data.translate)

    @abc.abstractmethod
    def display(self):
        pass

    @abc.abstractmethod
    def reset_view(self):
        pass

    @abc.abstractmethod
    def clear_content(self):
        pass
