from pyqtgraph.dockarea.Dock import Dock

from abc import ABC, abstractmethod

from ..widgets.ViewerElement import ViewerElement


class PluginCore(ABC):
    @abstractmethod
    def override_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    @abstractmethod
    def tweak_widgets(self, widgets: dict[str, ViewerElement]):
        pass

    @abstractmethod
    def refine_dock_titles(self, docks: dict[str, Dock], widgets: dict[str, ViewerElement]):
        pass
