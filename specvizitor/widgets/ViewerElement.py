from astropy.io.fits.header import Header
from qtpy import QtWidgets, QtCore

import abc
from dataclasses import asdict
import logging
import pathlib

from ..appdata import AppData
from ..config import docks
from ..io.viewer_data import get_filename, load

from .LazyViewerElement import LazyViewerElement
from .SmartSlider import SmartSliderWithEditor

logger = logging.getLogger(__name__)


class ViewerElement(LazyViewerElement, abc.ABC):
    data_loaded = QtCore.Signal(object)
    content_added = QtCore.Signal()
    view_reset = QtCore.Signal()
    content_cleared = QtCore.Signal()
    smoothing_applied = QtCore.Signal(float)

    def __init__(self, cfg: docks.ViewerElement, **kwargs):
        self.lazy_widgets: list[LazyViewerElement] = []
        self.sliders: list[SmartSliderWithEditor] = []

        super().__init__(cfg=cfg, **kwargs)

        self.cfg = cfg

        self.filename: pathlib.Path | None = None
        self.data = None
        self.meta: dict | Header | None = None
        self.allowed_data_types: tuple | None = None

        # create a smoothing slider
        self.smoothing_slider = self.create_smoothing_slider(**asdict(self.cfg.smoothing_slider))
        self.sliders.append(self.smoothing_slider)

    def create_smoothing_slider(self, **kwargs):
        smoothing_slider = SmartSliderWithEditor(parameter='sigma', action='smooth the data', parent=self, **kwargs)
        smoothing_slider.value_changed[float].connect(self.smooth)
        smoothing_slider.setToolTip('Slide to smooth the data')
        return smoothing_slider

    def init_ui(self):
        sub_layout = QtWidgets.QHBoxLayout()

        # add vertical sliders
        for s in self.sliders:
            if not s.text_editor:
                sub_layout.addWidget(s)
        sub_layout.addWidget(self.graphics_view)  # add the central widget
        self.layout().addLayout(sub_layout, 1, 1, 1, 1)

        sub_layout = QtWidgets.QVBoxLayout()

        # add horizontal sliders
        for s in self.sliders:
            if s.text_editor:
                sub_layout.addWidget(s)
        self.layout().addLayout(sub_layout, 2, 1, 1, 1)

        # init the UI of lazy widgets
        for w in self.lazy_widgets:
            w.init_ui()

        # init the UI of sliders
        for s in self.sliders:
            s.init_ui()

    def load_object(self, rd: AppData):
        # clear the widget content
        if self.data is not None:
            self.clear_content()

            for s in self.sliders:
                s.clear()

        # load catalogue values to the sliders
        for s in self.sliders:
            if s.cat_name is not None:
                s.update_default_value(rd.cat, rd.id, rd.config.catalogue.translate)

        # load data to the widget
        self._load_data(rd=rd)

        # display the data
        if self.data is not None:
            self.setEnabled(True)
            self.add_content()

            for s in self.sliders:
                s.update_from_slider()

            self.reset_view()
        else:
            self.setEnabled(False)

    def _load_data(self, rd: AppData):
        self.filename = get_filename(rd.config.data.dir, self.cfg.filename_keyword, rd.id)

        if self.filename is None:
            logger.error('{} not found (object ID: {})'.format(self.title, rd.id))
            self.data, self.meta = None, None
            return

        loader_config = {} if self.cfg.data_loader_params is None else self.cfg.data_loader_params

        self.data, self.meta = load(self.cfg.data_loader, self.filename, self.title, **loader_config)
        if self.data is None:
            return

        if self.allowed_data_types is not None:
            if not any(isinstance(self.data, t) for t in self.allowed_data_types):
                logger.error(f'Invalid input data type: {type(self.data)} (widget: {self.title}). '
                             'Try to use a different data loader')
                self.data, self.meta = None, None
                return

    def setEnabled(self, a0: bool = True):
        super().setEnabled(a0)
        for w in self.lazy_widgets:
            w.setEnabled(a0)
        for s in self.sliders:
            s.setEnabled(a0)

    @abc.abstractmethod
    def add_content(self):
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
