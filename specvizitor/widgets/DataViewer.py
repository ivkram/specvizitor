from astropy.table import Row
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

import logging

from ..config import config
from ..config.data_widgets import DataWidgets
from ..config.spectral_lines import SpectralLines
from ..io.inspection_data import InspectionData
from ..io.viewer_data import get_filenames_from_id
from ..plugins.plugin_core import PluginCore

from .AbstractWidget import AbstractWidget
from .LazyViewerElement import LazyViewerElement
from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Plot1D import Plot1D
from .Spec1D import Spec1D

logger = logging.getLogger(__name__)


class DataViewer(AbstractWidget):
    object_selected = QtCore.Signal(int, InspectionData, object, list)
    view_reset = QtCore.Signal()
    data_collected = QtCore.Signal(dict)

    def __init__(self,
                 viewer_cfg: DataWidgets,
                 appearance: config.Appearance,
                 spectral_lines: SpectralLines | None = None,
                 plugins: list[PluginCore] | None = None,
                 parent=None):

        self._appearance = appearance
        self._viewer_cfg = viewer_cfg
        self._spectral_lines = spectral_lines
        self._plugins: list[PluginCore] = plugins if plugins is not None else []

        self.dock_area = DockArea()
        self.added_docks: list[str] = []

        self.core_widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    @property
    def widgets(self) -> list[LazyViewerElement]:
        lazy_widgets = []
        for w in self.core_widgets.values():
            lazy_widgets.extend(w.lazy_widgets)

        return list(self.core_widgets.values()) + lazy_widgets

    @property
    def active_core_widgets(self) -> dict[str, ViewerElement]:
        return {title: w for title, w in self.core_widgets.items() if w.data is not None}

    def _create_widgets(self):
        # delete previously created widgets
        if self.widgets:
            self.object_selected.disconnect()

            try:
                self.view_reset.disconnect()
            except TypeError:
                pass

            for w in self.widgets:
                w.graphics_layout.clear()
                w.deleteLater()

        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        if self._viewer_cfg.images is not None:
            for name, image_cfg in self._viewer_cfg.images.items():
                widgets[name] = Image2D(cfg=image_cfg, title=name, appearance=self._appearance, parent=self)

        # create widgets for plots (does not include any spectra!)
        if self._viewer_cfg.plots is not None:
            for name, plot_cfg in self._viewer_cfg.plots.items():
                widgets[name] = Plot1D(cfg=plot_cfg, title=name, appearance=self._appearance, parent=self)

        # create widgets for 1D spectra
        if self._viewer_cfg.spectra is not None:
            for name, spec_cfg in self._viewer_cfg.spectra.items():
                widgets[name] = Spec1D(lines=self._spectral_lines, cfg=spec_cfg, title=name,
                                       appearance=self._appearance, parent=self)

        for w in widgets.values():
            w.post_init()

        for w in widgets.values():
            self.object_selected.connect(w.load_object)
        self.core_widgets = widgets

        for plugin in self._plugins:
            plugin.overwrite_widget_configs(self.core_widgets)

    def _create_docks(self):
        # delete previously added docks
        for dock_name in self.added_docks:
            self.docks[dock_name].close()

        docks = {}
        for widget in self.widgets:
            docks[widget.title] = Dock(widget.title, widget=widget)

        self.docks = docks

    def _add_dock(self, widget: LazyViewerElement):
        position = widget.cfg.position if widget.cfg.position is not None else 'bottom'
        relative_to = widget.cfg.relative_to if widget.cfg.relative_to in self.added_docks else None

        self.dock_area.addDock(dock=self.docks[widget.title],
                               position=position,
                               relativeTo=relative_to)

    def _add_docks(self):
        self.added_docks = []

        for widget in self.widgets:
            if widget.cfg.visible:
                self._add_dock(widget)
                self.added_docks.append(widget.title)

        for plugin in self._plugins:
            plugin.tweak_docks(self.docks)

    @QtCore.Slot()
    def init_docks(self):
        self._create_docks()
        self._add_docks()
        self._update_dock_titles()

    @QtCore.Slot(dict)
    def restore_dock_layout(self, layout: dict):
        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `layout`
            self.dock_area.restoreState(layout, missing='ignore', extra=None)
            logger.info('Dock layout restored')

            for plugin in self._plugins:
                plugin.tweak_docks(self.docks)

        except (KeyError, ValueError, TypeError):
            self.init_docks()  # to reset the dock layout
            logger.error('Failed to restore the dock layout')

    def init_ui(self):
        self._create_widgets()
        self.init_docks()

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=0, margins=0)

    def populate(self):
        self.layout().addWidget(self.dock_area, 1, 1, 1, 1)

    @QtCore.Slot(DataWidgets)
    def update_viewer_configuration(self, viewer_cfg: DataWidgets):
        self._viewer_cfg = viewer_cfg
        self.init_ui()

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object, config.Data)
    def load_object(self, j: int, review: InspectionData, obj_cat: Row | None, data_cfg: config.Data):
        # perform search for files containing the object ID in their filename
        discovered_data_files = get_filenames_from_id(data_cfg.dir, review.get_id(j))

        # load the object to the widgets
        self.object_selected.emit(j, review, obj_cat, discovered_data_files)

        try:
            self.view_reset.disconnect()
        except TypeError:
            pass
        for w in self.core_widgets.values():
            if w.data is not None:
                self.view_reset.connect(w.reset_view)

        self._update_dock_titles()

        for plugin in self._plugins:
            plugin.tweak_widgets(self.active_core_widgets, obj_cat)

    @QtCore.Slot()
    def collect(self):
        self.data_collected.emit(self.dock_area.saveState())

    @QtCore.Slot(str)
    def take_screenshot(self, filename: str):
        self.grab().save(filename)

    def _update_dock_titles(self):
        for core_widget in self.core_widgets.values():
            if core_widget.filename is not None and core_widget.data is not None:
                title = core_widget.filename.name

                # adding EXTNAME and EXTVER to the dock title
                fits_meta = core_widget.meta.get('EXTNAME'), core_widget.meta.get('EXTVER')
                j = 0
                while j < len(fits_meta) and fits_meta[j] is not None:
                    j += 1
                title_extra = ', '.join(map(str, fits_meta[:j]))

                if title_extra:
                    if core_widget.cfg.dock_title_fmt == 'short':
                        title = fits_meta[j - 1]
                    else:
                        title += f' [{title_extra}]'

                for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                    self.docks[w.title].setTitle(title)

            else:
                for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                    self.docks[w.title].setTitle(w.title)

