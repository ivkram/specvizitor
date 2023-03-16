from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

from ..appdata import AppData
from ..config import config
from ..config.docks import Docks
from ..config.spectral_lines import SpectralLines

from .AbstractWidget import AbstractWidget
from .LazyViewerElement import LazyViewerElement
from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D


class DataViewer(AbstractWidget):
    object_selected = QtCore.Signal(AppData)
    view_reset = QtCore.Signal()
    data_captured = QtCore.Signal(dict)

    def __init__(self,
                 cfg: config.DataViewer,
                 dock_cfg: Docks,
                 spectral_lines: SpectralLines = None,
                 plugins=None,
                 parent=None):

        self.cfg = cfg
        self.dock_cfg = dock_cfg

        # register plugins
        self._plugins = plugins if plugins is not None else []

        self.spectral_lines = spectral_lines

        self.dock_area = DockArea()
        self.added_docks: list[str] = []

        self.core_widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        super().__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    @property
    def widgets(self) -> list[LazyViewerElement]:
        lazy_widgets = []
        for w in self.core_widgets.values():
            lazy_widgets.extend(w.lazy_widgets)

        return list(self.core_widgets.values()) + lazy_widgets

    def create_widgets(self):
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
        if self.dock_cfg.images is not None:
            for name, image_cfg in self.dock_cfg.images.items():
                widgets[name] = Image2D(cfg=image_cfg, title=name, inspector_config=self.cfg,
                                        parent=self)

        # create widgets for 1D spectra
        if self.dock_cfg.spectra is not None:
            for name, spec_cfg in self.dock_cfg.spectra.items():
                widgets[name] = Spec1D(lines=self.spectral_lines, cfg=spec_cfg, title=name,
                                       inspector_config=self.cfg, parent=self)

        for w in widgets.values():
            self.object_selected.connect(w.load_object)

        self.core_widgets = widgets

    def create_docks(self):
        # delete previously added docks
        for dock_name in self.added_docks:
            self.docks[dock_name].close()

        docks = {}
        for widget in self.widgets:
            docks[widget.title] = Dock(widget.title, widget=widget)

        self.docks = docks

    def add_dock(self, widget: LazyViewerElement):
        position = widget.cfg.position if widget.cfg.position is not None else 'bottom'
        relative_to = widget.cfg.relative_to if widget.cfg.relative_to in self.added_docks else None

        self.dock_area.addDock(dock=self.docks[widget.title],
                               position=position,
                               relativeTo=relative_to)

    def add_docks(self):
        added_docks = []

        for widget in self.widgets:
            if widget.cfg.visible:
                self.add_dock(widget)
                added_docks.append(widget.title)

        self.added_docks = added_docks

    @QtCore.Slot()
    def reset_dock_state(self):
        self.create_docks()
        self.add_docks()
        self._update_dock_titles()

    @QtCore.Slot(dict)
    def restore_dock_state(self, dock_state: dict):
        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `state`
            self.dock_area.restoreState(dock_state, missing='ignore', extra=None)
        except (KeyError, ValueError, TypeError):
            self.reset_dock_state()

    def init_ui(self):
        self.create_widgets()
        self.create_docks()
        self.add_docks()

    def connect(self):
        pass

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=0, margins=0)

    def populate(self):
        self.layout().addWidget(self.dock_area, 1, 1, 1, 1)

    @QtCore.Slot(Docks)
    def update_dock_configuration(self, dock_cfg: Docks):
        self.dock_cfg = dock_cfg
        self.init_ui()

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(AppData)
    def load_object(self, rd: AppData):

        # load the object to the widgets
        self.object_selected.emit(rd)

        try:
            self.view_reset.disconnect()
        except TypeError:
            pass
        for w in self.core_widgets.values():
            if w.data is not None:
                self.view_reset.connect(w.reset_view)

        for plugin in self._plugins:
            plugin.link(self.core_widgets, label_style=rd.config.data_viewer.label_style)

        # update the dock titles
        self._update_dock_titles()

    @QtCore.Slot()
    def capture(self):
        self.data_captured.emit(self.dock_area.saveState())

    @QtCore.Slot(str)
    def take_screenshot(self, filename: str):
        self.grab().save(filename)

    def _update_dock_titles(self):
        for core_widget in self.core_widgets.values():
            for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                if core_widget.filename is not None and core_widget.data is not None:
                    self.docks[w.title].setTitle(core_widget.filename.name)
                else:
                    self.docks[w.title].setTitle(w.title)
