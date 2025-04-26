from pyqtgraph.dockarea.Container import StackedWidget
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
    def get_dock_stack(docks: dict[str, Dock]) -> StackedWidget | None:
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

        return dock_in_stack.container().stack

    @staticmethod
    def fix_dock_stack_labels(stack: StackedWidget):
        """
        * patching a pyqtgraph bug *
        when the dock area state is restored, the current active widget of the line map stack is changed to Line Map 1,
        however the last Line Map remains active (i.e. its label is still highlighted). therefore, when Line Map 1 is
        raised to the top, the last Line Map remains active
        """
        if stack.count() <= 1:
            return
        for i in range(stack.count()):
            stack.widget(i).label.setDim(True)
        stack.widget(0).raiseDock()
