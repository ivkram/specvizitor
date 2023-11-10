from astropy.io.fits.header import Header
from astropy.table import Table
from qtpy import QtWidgets, QtCore

import abc
from dataclasses import asdict
import logging
import pathlib

from ..config import Cache, data_widgets
from ..io.inspection_data import InspectionData
from ..io.viewer_data import get_matching_filename, load

from .LazyViewerElement import LazyViewerElement
from .SmartSlider import SmartSliderWithEditor

logger = logging.getLogger(__name__)


class ViewerElement(LazyViewerElement, abc.ABC):
    content_added = QtCore.Signal()
    view_reset = QtCore.Signal()
    content_cleared = QtCore.Signal()
    smoothing_applied = QtCore.Signal(float)

    def __init__(self, cfg: data_widgets.ViewerElement, **kwargs):
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

    @abc.abstractmethod
    def post_init(self):
        """ This method is evoked after initializing all data widgets and can be used e.g. to link views
        """
        pass

    @QtCore.Slot(int, InspectionData, Table, list)
    def load_object(self, j: int, review: InspectionData, cat: Table, data_files: list[str]):
        # clear the widget content
        if self.data is not None:
            self.clear_content()
            for s in self.sliders:
                s.clear()

        # load catalogue values to the sliders
        for s in self.sliders:
            if s.name_in_catalogue is not None:
                s.update_default_value(cat, review.get_id(j))

        # load data to the widget
        self.load_data(obj_id=review.get_id(j), data_files=data_files)

        # display the data
        if self.data is not None:
            self.setEnabled(True)
            self.add_content()

            for s in self.sliders:
                s.update_from_slider()

            self.reset_view()
        else:
            self.setEnabled(False)

    def load_data(self, obj_id: str | int, data_files: list[str]):
        if self.cfg.data.filename_keyword is None:
            logger.error(f'Filename keyword not specified (object ID: {self.title})')
            self.data, self.meta = None, None
            return

        loader_params = {} if self.cfg.data.loader_params is None else self.cfg.data.loader_params

        self.filename = get_matching_filename(data_files, self.cfg.data.filename_keyword)
        if self.filename is None:
            if not loader_params.get('silent'):
                logger.error('{} not found (object ID: {})'.format(self.title, obj_id))
            self.data, self.meta = None, None
            return

        self.data, self.meta = load(self.cfg.data.loader, self.filename, self.title, **loader_params)

        if not self.validate_dtype(self.data):
            self.data, self.meta = None, None

    def validate_dtype(self, data) -> bool:
        if self.allowed_data_types is not None:
            if not any(isinstance(data, t) for t in self.allowed_data_types):
                logger.error(f'Invalid input data type: {type(data)} (widget: {self.title}). '
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
