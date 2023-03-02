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
        self.cfg = cfg

        if plugins is not None:
            self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin() for plugin_name in plugins]
        else:
            self._plugins = []

        self.layout.setSpacing(10)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.dock_area = DockArea()
        self.dock_widgets = self.create_widgets()
        self.docks = self.create_docks()

    def init_ui(self):
        self.layout.addWidget(self.dock_area, 1, 1, 1, 1)
        self.add_docks()

        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `state`
            self.dock_area.restoreState(self.rd.cache.dock_state, missing='ignore', extra=None)
        except (KeyError, ValueError, TypeError):
            for d in self.docks.values():
                d.close()
            self.docks = self.create_docks()
            self.add_docks()

        for w in self.dock_widgets.values():
            w.init_ui()

    def create_widgets(self) -> dict[str, ViewerElement]:
        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        if self.cfg.images is not None:
            for name, image_cfg in self.cfg.images.items():
                widgets[name] = Image2D(rd=self.rd, cfg=image_cfg, name=name, parent=self)

        # create widgets for 1D spectra
        if self.cfg.spectra is not None:
            for name, spec_cfg in self.cfg.spectra.items():
                widgets[name] = Spec1D(rd=self.rd, cfg=spec_cfg, name=name, parent=self)

        return widgets

    def create_docks(self) -> dict[str, Dock]:
        docks = {}
        for name, widget in self.dock_widgets.items():
            dock = Dock(name)
            dock.addWidget(widget)
            docks[name] = dock
        return docks

    def add_docks(self):
        for name, d in self.docks.items():
            position = self.dock_widgets[name].cfg.position
            self.dock_area.addDock(dock=d,
                                   position=position if position is not None else 'bottom',
                                   relativeTo=self.dock_widgets[name].cfg.relative_to)

    def save_dock_state(self):
        self.rd.cache.dock_state = self.dock_area.saveState()
        self.rd.cache.save(self.rd.cache_file)

    def load_object(self):
        self.save_dock_state()

        for name, w in self.dock_widgets.items():
            w.load_object()

            # update the titles of the docks
            if w.filename is not None and w.data is not None:
                self.docks[name].setTitle(self.dock_title(w=w))
            else:
                self.docks[name].setTitle(name)

        for plugin in self._plugins:
            plugin.link(self.dock_widgets)

    @staticmethod
    def dock_title(w: ViewerElement) -> str:
        if w.cfg.ext_name is not None and w.cfg.ext_ver is None:
            return f"{w.filename.name} [{w.cfg.ext_name}]"
        elif w.cfg.ext_name is not None and w.cfg.ext_ver is not None:
            return f"{w.filename.name} [{w.cfg.ext_name}, {w.cfg.ext_ver}]"
        elif len(w.hdul) > 2:
            return f"{w.filename.name} [HDU #1]"
        else:
            return w.filename.name

    def reset_view(self):
        for w in self.dock_widgets.values():
            w.reset_view()

    def take_screenshot(self, filename: str):
        self.grab().save(filename)
