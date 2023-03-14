import pyqtgraph as pg
from qtpy import QtWidgets

from ..config import docks, config
from .AbstractWidget import AbstractWidget


class LazyViewerElement(AbstractWidget):
    def __init__(self, title: str, cfg: docks.LazyViewerElement, inspector_config: config.DataViewer, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QtWidgets.QGridLayout())

        self.title = title
        self.cfg = cfg
        self.inspector_config = inspector_config

        # create a central widget
        self.graphics_view = pg.GraphicsView(parent=self)
        self.graphics_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.graphics_layout)

        self.set_geometry(spacing=self.inspector_config.spacing, margins=self.inspector_config.margins)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        super().set_geometry(spacing=spacing, margins=margins)

        self.graphics_layout.setSpacing(spacing)
        self.graphics_layout.setContentsMargins(0, 0, 5, 5)

    def populate(self):
        self.layout().addWidget(self.graphics_view, 1, 1, 1, 1)
