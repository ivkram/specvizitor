from qtpy import QtWidgets

import abc

from ..utils.widget_tools import get_widgets


class QtAbcMeta(type(QtWidgets.QWidget), type(abc.ABC)):
    pass


class AbstractWidget(QtWidgets.QWidget, abc.ABC, metaclass=QtAbcMeta):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setEnabled(False)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        self.layout().setSpacing(spacing)

        if isinstance(margins, int):
            margins = tuple(margins for _ in range(4))
        self.layout().setContentsMargins(*margins)

    @abc.abstractmethod
    def populate(self):
        pass

    def reset_layout(self):
        for widget in get_widgets(self.layout()):
            self.layout().removeWidget(widget)
        self.populate()
