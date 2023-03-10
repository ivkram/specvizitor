import logging
import abc
import pathlib
from dataclasses import asdict

import numpy as np
from astropy.table import Table
from astropy.io.fits.header import Header

from qtpy import QtWidgets

from .LazyViewerElement import LazyViewerElement
from ..utils import SmartSlider, table_tools
from ..appdata import AppData
from ..config import docks
from ..io.viewer_data import get_filename, load


logger = logging.getLogger(__name__)


class ViewerElement(LazyViewerElement, abc.ABC):
    def __init__(self, rd: AppData, cfg: docks.ViewerElement, title: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, title=title, parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.lazy_widgets: list[LazyViewerElement] = []
        self.sliders: list[SmartSlider] = []

        self.filename: pathlib.Path | None = None
        self.data: np.ndarray | Table | None = None
        self.meta: dict | Header | None = None

        # create a smoothing slider
        self.smoothing_slider = SmartSlider(parameter='sigma', action='smooth the data', parent=self,
                                            **asdict(self.cfg.smoothing_slider))
        self.smoothing_slider.value_changed[float].connect(self.smooth)
        self.smoothing_slider.setToolTip('Slide to smooth the data')
        self.sliders.append(self.smoothing_slider)

    def init_ui(self):
        sub_layout = QtWidgets.QHBoxLayout()

        # add vertical sliders
        for s in self.sliders:
            if not s.text_editor:
                sub_layout.addWidget(s)
        sub_layout.addWidget(self.graphics_view)  # add the central widget
        self.layout.addLayout(sub_layout, 1, 1, 1, 1)

        sub_layout = QtWidgets.QVBoxLayout()

        # add horizontal sliders
        for s in self.sliders:
            if s.text_editor:
                sub_layout.addWidget(s)
        self.layout.addLayout(sub_layout, 2, 1, 1, 1)

        # init the UI of lazy widgets
        for w in self.lazy_widgets:
            w.init_ui()

        # init the UI of sliders
        for s in self.sliders:
            s.init_ui()

    def load_object(self):
        # clear the widget content
        if self.data is not None:
            self.clear_content()

            for s in self.sliders:
                s.clear()

        # load catalogue values to the sliders
        for s in self.sliders:
            if s.cat_name is not None:
                s.update_from_cat(self.rd.cat, self.rd.id, self.rd.config.cat.translate)

        # load data to the widget
        self._load_data()

        # display the data
        if self.data is not None:
            self.activate()
            self.display()

            for s in self.sliders:
                if s.cat_name is not None:
                    s.reset()
                s.update_from_slider()

            self.reset_view()
        else:
            self.activate(False)

    def _load_data(self):
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

    @abc.abstractmethod
    def smooth(self, sigma: float):
        pass
