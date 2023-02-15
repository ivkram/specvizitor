from qtpy import QtWidgets

from ..appdata.runtime import RuntimeData
from ..appdata import config
from ..utils.widgets import get_widgets


class AbstractWidget(QtWidgets.QWidget):
    def __init__(self, rd: RuntimeData, cfg: config.AbstractWidget, parent=None):
        self.rd = rd

        super().__init__(parent)

        if cfg.min_width:
            self.setMinimumWidth(cfg.min_width)
        if cfg.min_height:
            self.setMinimumHeight(cfg.min_height)

        self.setEnabled(False)

    @property
    def widgets(self) -> list[QtWidgets.QWidget]:
        """
        @return: a list of widgets added to the instance of the AbstractWidget class.
        """
        return get_widgets(self.layout)

    def init_ui(self):
        for widget in self.widgets:
            self.layout.removeWidget(widget)
            widget.destroy()

    def dump(self):
        pass

    def load_object(self):
        pass

    def load_project(self):
        self.setEnabled(True)
