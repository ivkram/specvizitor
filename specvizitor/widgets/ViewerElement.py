import logging
import abc
import pathlib
from dataclasses import asdict

import numpy as np
from astropy.table import Table
from astropy.io.fits.header import Header

from .AbstractWidget import AbstractWidget

from ..appdata import AppData
from ..config import docks
from ..io.viewer_data import get_filename, load
from ..utils import table_tools
from ..utils import SmartSlider


logger = logging.getLogger(__name__)


class ViewerElement(AbstractWidget, abc.ABC):
    def __init__(self, rd: AppData, cfg: docks.ViewerElement, title: str, parent=None):
        super().__init__(parent=parent)

        self.rd = rd
        self.cfg = cfg
        self.title: str = title

        self.filename: pathlib.Path | None = None
        self.data: np.ndarray | Table | None = None
        self.meta: dict | Header | None = None

        self.layout.setSpacing(self.rd.config.viewer_geometry.spacing)
        self.layout.setContentsMargins(*(self.rd.config.viewer_geometry.margins for _ in range(4)))

        self.smoothing_slider = SmartSlider(**asdict(self.cfg.smoothing_slider), parent=self)
        self.smoothing_slider.valueChanged[int].connect(self.smoothing_slider_action)
        self.smoothing_slider.setToolTip('Slide to smooth the data')

    def load_object(self):
        # clear the widget content
        if self.data is not None:
            self.clear_content()

        # load data to the widget
        self.load_data()

        # display the data
        if self.data is not None:
            self.setEnabled(True)
            self.display()
            if self.smoothing_slider.value > 0:
                self.smooth(self.smoothing_slider.value)
            self.reset_view()
        else:
            self.setEnabled(False)

    def load_data(self):
        self.filename = get_filename(self.rd.config.data.dir, self.cfg.filename_keyword, self.rd.id)

        if self.filename is None:
            logger.warning('{} not found (object ID: {})'.format(self.title, self.rd.id))
            self.data, self.meta = None, None
            return

        if self.cfg.loader_config is None:
            loader_config = {}
        else:
            loader_config = self.cfg.loader_config

        try:
            self.data, self.meta = load(self.cfg.loader, self.filename, self.title, **loader_config)
        except TypeError as e:
            # unexpected keyword(s) passed to the loader
            logger.error(e.args[0])
            self.data, self.meta = None, None
            return

        if isinstance(self.data, Table):
            # translate the table columns
            if self.rd.config.data.translate:
                table_tools.translate(self.data, self.rd.config.data.translate)

        if not self.validate():
            self.data, self.meta = None, None
            return

    @abc.abstractmethod
    def validate(self):
        pass

    @abc.abstractmethod
    def display(self):
        pass

    @abc.abstractmethod
    def reset_view(self):
        pass

    @abc.abstractmethod
    def clear_content(self):
        pass

    def smoothing_slider_action(self, index: int):
        self.smoothing_slider.index = index
        self.smooth(self.smoothing_slider.value)

    @abc.abstractmethod
    def smooth(self, sigma: int):
        pass
