import importlib
from qtpy import QtWidgets, QtCore

from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea

from ..utils import AbstractWidget
from .ViewerElement import ViewerElement
from .LazyViewerElement import LazyViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D

from ..appdata import AppData
from ..io.viewer_data import add_enabled_aliases


class DataViewer(AbstractWidget):
    new_object_selected = QtCore.Signal(AppData)
    reset_view_triggered = QtCore.Signal()

    def __init__(self, rd: AppData, parent=None):
        super().__init__(layout=QtWidgets.QGridLayout(), parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.set_geometry(spacing=0, margins=0)

        self.rd = rd

        # register units
        if self.rd.config.data.defined_units is not None:
            add_enabled_aliases(self.rd.config.data.defined_units)

        # register plugins
        plugins = self.rd.config.plugins
        self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin()
                         for plugin_name in plugins] if plugins is not None else []

        self.dock_area = DockArea()
        self.added_docks: list[str] = []

        self.core_widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        self.create_all()

        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `state`
            self.dock_area.restoreState(self.rd.cache.dock_state, missing='ignore', extra=None)
        except (KeyError, ValueError, TypeError):
            self.reset_dock_state()

    @property
    def widgets(self) -> list[LazyViewerElement]:
        lazy_widgets = []
        for w in self.core_widgets.values():
            lazy_widgets.extend(w.lazy_widgets)

        return list(self.core_widgets.values()) + lazy_widgets

    def init_ui(self):
        self.layout().addWidget(self.dock_area, 1, 1, 1, 1)

    def create_widgets(self):
        # delete previously created widgets
        if self.widgets:
            self.new_object_selected.disconnect()
            self.reset_view_triggered.disconnect()

            for w in self.widgets:
                w.graphics_layout.clear()
                w.deleteLater()

        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        if self.rd.docks.images is not None:
            for name, image_cfg in self.rd.docks.images.items():
                widgets[name] = Image2D(cfg=image_cfg, title=name, global_viewer_config=self.rd.config.data_viewer,
                                        parent=self)

        # create widgets for 1D spectra
        if self.rd.docks.spectra is not None:
            for name, spec_cfg in self.rd.docks.spectra.items():
                widgets[name] = Spec1D(lines=self.rd.lines, cfg=spec_cfg, title=name,
                                       global_viewer_config=self.rd.config.data_viewer, parent=self)

        for w in widgets.values():
            w.init_ui()

        for w in widgets.values():
            self.new_object_selected.connect(w.load_object)
            self.reset_view_triggered.connect(w.reset_view)

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

    def create_all(self):
        self.create_widgets()
        self.create_docks()
        self.add_docks()

        if self.rd.df is not None:
            self.load_object()

    def update_dock_titles(self):
        for core_widget in self.core_widgets.values():
            for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                if core_widget.filename is not None and core_widget.data is not None:
                    self.docks[w.title].setTitle(core_widget.filename.name)
                else:
                    self.docks[w.title].setTitle(w.title)

    def reset_dock_state(self):
        self.create_docks()
        self.add_docks()
        self.update_dock_titles()

    def save_dock_state(self):
        self.rd.cache.dock_state = self.dock_area.saveState()
        self.rd.cache.save()

    def load_object(self):
        # cache the dock state
        self.save_dock_state()

        # load the object to the widgets
        self.new_object_selected.emit(self.rd)

        # update the dock titles
        self.update_dock_titles()

        for plugin in self._plugins:
            plugin.link(self.core_widgets, label_style=self.rd.config.data_viewer.label_style)

    def reset_view(self):
        self.reset_view_triggered.emit()

    def take_screenshot(self, filename: str):
        self.grab().save(filename)
