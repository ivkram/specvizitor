import pyqtgraph as pg

from ..utils import AbstractWidget
from ..appdata import AppData
from ..config import docks


class LazyViewerElement(AbstractWidget):
    def __init__(self, rd: AppData, cfg: docks.LazyViewerElement, title: str, parent=None):
        super().__init__(parent=parent)

        self.rd = rd
        self.cfg = cfg
        self.title: str = title

        self.layout.setSpacing(self.rd.config.data_viewer.spacing)
        self.layout.setContentsMargins(*(self.rd.config.data_viewer.margins for _ in range(4)))

        # create a central widget
        self.graphics_view = pg.GraphicsView()
        self.graphics_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.graphics_layout)

        self.graphics_layout.setSpacing(5)
        self.graphics_layout.setContentsMargins(5, 5, 5, 5)

    def init_ui(self):
        self.layout.addWidget(self.graphics_view, 1, 1, 1, 1)
