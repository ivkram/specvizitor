import abc
from abc import ABC

from qtpy import QtWidgets

from ..runtime import config
from ..utils.widgets import get_widgets


class QtAbcMeta(type(QtWidgets.QWidget), type(ABC)):
    pass


class AbstractWidget(QtWidgets.QWidget, ABC, metaclass=QtAbcMeta):
    def __init__(self, cfg: config.AbstractWidget, parent=None):
        super().__init__(parent)

        if cfg.min_width:
            self.setMinimumWidth(cfg.min_width)
        if cfg.min_height:
            self.setMinimumHeight(cfg.min_height)

        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)

        self.setEnabled(False)

    @abc.abstractmethod
    def init_ui(self):
        pass

    @abc.abstractmethod
    def load_object(self):
        pass

    def reset_layout(self):
        for widget in get_widgets(self.layout):
            self.layout.removeWidget(widget)
            widget.destroy()
        self.init_ui()

    def activate(self):
        self.setEnabled(True)
