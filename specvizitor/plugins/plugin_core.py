from pyqtgraph.dockarea.Dock import Dock

from abc import ABC, abstractmethod

from specvizitor.io.catalog import Catalog
from specvizitor.widgets.ViewerElement import ViewerElement


class PluginCore(ABC):
    @abstractmethod
    def override_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    @abstractmethod
    def update_docks(self, docks: dict[str, Dock], cat_entry: Catalog | None = None):
        pass

    @abstractmethod
    def update_active_widgets(self, widgets: dict[str, ViewerElement], cat_entry: Catalog | None = None):
        pass

    @staticmethod
    def get_stacked_docks(docks: dict[str, Dock]) -> dict[str, Dock] | None:
        """Locate a stack of docks, if exists. If multiple stacked are found, return the largest stack.
        """

        dock_in_stack = None
        max_stack_count = 0

        # find the largest stack
        for i, d in enumerate(docks.values()):
            if hasattr(d.container(), 'stack'):
                stack = d.container().stack
                if stack.count() > max_stack_count:
                    dock_in_stack = d
                    max_stack_count = stack.count()

        if dock_in_stack is None:
            return None

        stack = dock_in_stack.container().stack

        # find the stacked docks
        stacked_docks = {}
        for title, d in docks.items():
            if hasattr(d.container(), 'stack') and d.container().stack is stack:
                stacked_docks[title] = d

        return stacked_docks
