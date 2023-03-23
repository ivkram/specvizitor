from abc import ABC, abstractmethod

from ..widgets.ViewerElement import ViewerElement


class PluginCore(ABC):
    @abstractmethod
    def invoke(self, widgets: dict[str, ViewerElement]):
        pass
