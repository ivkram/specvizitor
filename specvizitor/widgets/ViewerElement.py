from astropy.io.fits.header import Header
from astropy.table import Table
from qtpy import QtWidgets, QtCore

import abc
from dataclasses import asdict
import logging
import pathlib

from ..config import config, docks
from ..io.inspection_data import InspectionData
from ..io.viewer_data import get_filename, load

from .LazyViewerElement import LazyViewerElement
from .SmartSlider import SmartSliderWithEditor

logger = logging.getLogger(__name__)


class ViewerElement(LazyViewerElement, abc.ABC):
    content_added = QtCore.Signal()
    view_reset = QtCore.Signal()
    content_cleared = QtCore.Signal()
    smoothing_applied = QtCore.Signal(float)

    def __init__(self, cfg: docks.ViewerElement, **kwargs):
        self.cfg = cfg

        self.filename: pathlib.Path | None = None
        self.data = None
        self.meta: dict | Header | None = None
        self.allowed_data_types: tuple | None = None

        self.lazy_widgets: list[LazyViewerElement] = []
        self.sliders: list[SmartSliderWithEditor] = []

        self._smoothing_slider: SmartSliderWithEditor | None = None

        super().__init__(cfg=cfg, **kwargs)

    def init_ui(self):
        super().init_ui()

        self._smoothing_slider = SmartSliderWithEditor(parameter='sigma', action='smooth the data', parent=self,
                                                       **asdict(self.cfg.smoothing_slider))
        self._smoothing_slider.setToolTip('Slide to smooth the data')
        self.sliders.append(self._smoothing_slider)

        self._smoothing_slider.value_changed[float].connect(self.smooth)

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()

        # add vertical sliders
        for s in self.sliders:
            if not s.show_text_editor:
                sub_layout.addWidget(s)
        sub_layout.addWidget(self.graphics_view)  # add the central widget
        self.layout().addLayout(sub_layout, 1, 1, 1, 1)

        sub_layout = QtWidgets.QVBoxLayout()

        # add horizontal sliders
        for s in self.sliders:
            if s.show_text_editor:
                sub_layout.addWidget(s)
        self.layout().addLayout(sub_layout, 2, 1, 1, 1)

    @QtCore.Slot(int, InspectionData, Table, config.Data)
    def load_object(self, j: int, notes: InspectionData, cat: Table, data_cfg: config.Data):
        # clear the widget content
        if self.data is not None:
            self.clear_content()
            self.remove_registered_items()

            for s in self.sliders:
                s.clear()

        # load catalogue values to the sliders
        for s in self.sliders:
            if s.name_in_catalogue is not None:
                s.update_default_value(cat, notes.get_id(j))

        # load data to the widget
        self._load_data(j=j, cat=cat, notes=notes, data_cfg=data_cfg)

        # display the data
        if self.data is not None:
            self.setEnabled(True)
            self.add_content()

            for s in self.sliders:
                s.update_from_slider()

            self.reset_view()
        else:
            self.setEnabled(False)

    def _load_data(self, j: int, cat: Table, notes: InspectionData, data_cfg: config.Data):
        if self.cfg.data.filename_keyword is None:
            logger.error(f'Filename keyword not specified (object ID: {self.title})')
            return

        self.filename = get_filename(data_cfg.dir, self.cfg.data.filename_keyword, notes.get_id(j))

        if self.filename is None:
            logger.error('{} not found (object ID: {})'.format(self.title, notes.get_id(j)))
            self.data, self.meta = None, None
            return

        loader_config = {} if self.cfg.data.loader_params is None else self.cfg.data.loader_params

        self.data, self.meta = load(self.cfg.data.loader, self.filename, self.title, **loader_config)
        if self.data is None:
            return

        if not self.validate_dtype():
            self.data, self.meta = None, None
            return

    def validate_dtype(self):
        if self.allowed_data_types is not None:
            if not any(isinstance(self.data, t) for t in self.allowed_data_types):
                logger.error(f'Invalid input data type: {type(self.data)} (widget: {self.title}). '
                             'Try to use a different data loader')
                return False
        return True

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
