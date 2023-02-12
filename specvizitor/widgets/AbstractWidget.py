from pyqtgraph.Qt import QtWidgets

from ..runtime import RuntimeData
from ..utils import params


class AbstractWidget(QtWidgets.QWidget):
    def __init__(self, rd: RuntimeData, cfg: params.AbstractWidget, parent=None):
        self.rd = rd

        super().__init__(parent)

        if cfg.min_width:
            self.setMinimumWidth(cfg.min_width)
        if cfg.min_height:
            self.setMinimumHeight(cfg.min_height)

        self.setEnabled(False)

    def dump(self):
        pass

    def load_object(self):
        pass

    def load_project(self):
        self.setEnabled(True)
