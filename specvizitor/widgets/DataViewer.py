import importlib

from qtpy import QtWidgets

from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea

from ..utils import AbstractWidget
from .ViewerElement import ViewerElement
from .LazyViewerElement import LazyViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D

from ..appdata import AppData
from ..config.docks import Docks
from ..io.viewer_data import add_enabled_aliases


class DataViewer(AbstractWidget):
    def __init__(self, rd: AppData, cfg: Docks, plugins=None, parent=None):
        super().__init__(layout=QtWidgets.QGridLayout(), parent=parent)

        self.rd = rd
        self.cfg = cfg

        # register units
        if self.rd.config.data.defined_units is not None:
            add_enabled_aliases(self.rd.config.data.defined_units)

        self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin()
                         for plugin_name in plugins] if plugins is not None else []

        self.set_geometry(spacing=0, margins=0)

        self.dock_area = DockArea()
        self.added_docks: list[str] = []

        self.dock_widgets = self.create_widgets()
        self.docks = self.create_docks()

    def init_ui(self):
        self.layout().addWidget(self.dock_area, 1, 1, 1, 1)
        self.add_docks()

        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `state`
            self.dock_area.restoreState(self.rd.cache.dock_state, missing='ignore', extra=None)
        except (KeyError, ValueError, TypeError):
            self.reset_dock_state()

        for w in self.dock_widgets.values():
            w.init_ui()

    def create_widgets(self) -> dict[str, ViewerElement]:
        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        if self.cfg.images is not None:
            for name, image_cfg in self.cfg.images.items():
                widgets[name] = Image2D(cfg=image_cfg, title=name, global_viewer_config=self.rd.config.data_viewer,
                                        parent=self)

        # create widgets for 1D spectra
        if self.cfg.spectra is not None:
            for name, spec_cfg in self.cfg.spectra.items():
                if spec_cfg.visible:
                    widgets[name] = Spec1D(lines=self.rd.lines, cfg=spec_cfg, title=name,
                                           global_viewer_config=self.rd.config.data_viewer, parent=self)

        return widgets

    def create_docks(self) -> dict[str, Dock]:
        docks = {}
        for widget in self.dock_widgets.values():
            docks[widget.title] = Dock(widget.title, widget=widget)

            for lazy_widget in widget.lazy_widgets:
                docks[lazy_widget.title] = Dock(lazy_widget.title, widget=lazy_widget)

        return docks

    def add_dock(self, widget: LazyViewerElement):
        if widget.cfg.visible:
            self.dock_area.addDock(dock=self.docks[widget.title],
                                   position=widget.cfg.position if widget.cfg.position is not None else 'bottom',
                                   relativeTo=widget.cfg.relative_to if widget.cfg.relative_to in self.added_docks else None)
            self.added_docks.append(widget.title)

    def add_docks(self):
        self.added_docks = []

        for widget in self.dock_widgets.values():
            self.add_dock(widget)
            for lazy_widget in widget.lazy_widgets:
                self.add_dock(lazy_widget)

    def update_dock_titles(self):
        for w in self.dock_widgets.values():
            if w.filename is not None and w.data is not None:
                self.docks[w.title].setTitle(w.filename.name)
                for lazy_widget in w.lazy_widgets:
                    self.docks[lazy_widget.title].setTitle(w.filename.name)
            else:
                self.docks[w.title].setTitle(w.title)
                for lazy_widget in w.lazy_widgets:
                    self.docks[lazy_widget.title].setTitle(lazy_widget.title)

    def reset_dock_state(self):
        for dock_name in self.added_docks:
            self.docks[dock_name].close()
        self.docks = self.create_docks()
        self.add_docks()
        self.update_dock_titles()

    def save_dock_state(self):
        self.rd.cache.dock_state = self.dock_area.saveState()
        self.rd.cache.save()

    def load_object(self):
        self.save_dock_state()

        # load the object to the widget
        for w in self.dock_widgets.values():
            w.load_object(rd=self.rd)

        # update the title of the dock
        self.update_dock_titles()

        for plugin in self._plugins:
            plugin.link(self.dock_widgets, label_style=self.rd.config.data_viewer.label_style)

    def reset_view(self):
        for w in self.dock_widgets.values():
            if w.data is not None:
                w.reset_view()

    def take_screenshot(self, filename: str):
        self.grab().save(filename)
