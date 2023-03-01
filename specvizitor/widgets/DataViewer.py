import importlib

from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea

from .AbstractWidget import AbstractWidget
from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D

from ..runtime.appdata import AppData
from ..runtime import config


class DataViewer(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.Viewer, plugins=None, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd

        if plugins is not None:
            self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin() for plugin_name in plugins]
        else:
            self._plugins = []

        self.layout.setSpacing(10)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.dock_area = DockArea()
        self.docks: dict[str, Dock] = {}
        self.dock_widgets: dict[str, ViewerElement] = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        for name, image_cfg in cfg.images.items():
            self.dock_widgets[name] = Image2D(rd=rd, cfg=image_cfg, name=name, parent=self)

        # create widgets for 1D spectra
        for name, spec_cfg in cfg.spectra.items():
            self.dock_widgets[name] = Spec1D(rd=rd, cfg=spec_cfg, name=name, parent=self)

        for name, widget in self.dock_widgets.items():
            dock = Dock(name)
            dock.addWidget(widget)
            self.docks[name] = dock

    def init_ui(self):
        self.layout.addWidget(self.dock_area, 1, 1, 1, 1)

        for name, d in self.docks.items():
            position = self.dock_widgets[name].cfg.position
            self.dock_area.addDock(dock=d,
                                   position=position if position is not None else 'bottom',
                                   relativeTo=self.dock_widgets[name].cfg.relative_to)

        try:
            self.dock_area.restoreState(self.rd.cache.dock_state, missing='ignore')
        except (ValueError, TypeError):
            self.save_dock_state()

        for w in self.dock_widgets.values():
            w.init_ui()

    def save_dock_state(self):
        self.rd.cache.dock_state = self.dock_area.saveState()
        self.rd.cache.save(self.rd.cache_file)

    def load_object(self):
        self.save_dock_state()

        for name, w in self.dock_widgets.items():
            w.load_object()

            # update the titles of the docks
            if w.filename is not None:
                self.docks[name].setTitle(str(w.filename.name))
            else:
                self.docks[name].setTitle(name)

        for plugin in self._plugins:
            plugin.link(self.dock_widgets)

    def reset_view(self):
        for w in self.dock_widgets.values():
            w.reset_view()

    def take_screenshot(self, filename: str):
        self.grab().save(filename)
