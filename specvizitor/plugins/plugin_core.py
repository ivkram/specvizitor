from pyqtgraph.dockarea.Dock import Dock

from abc import ABC, abstractmethod

from ..widgets.ViewerElement import ViewerElement


class PluginCore(ABC):
    @abstractmethod
    def overwrite_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    @abstractmethod
    def tweak_widgets(self, widgets: dict[str, ViewerElement]):
        pass
