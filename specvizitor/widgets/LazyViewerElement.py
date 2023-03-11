import pyqtgraph as pg

from ..utils import AbstractWidget
from ..config import docks, config


class LazyViewerElement(AbstractWidget):
    def __init__(self, cfg: docks.LazyViewerElement, title: str, global_config: config.DataViewer, parent=None):
        super().__init__(parent=parent)

        self.cfg = cfg
        self.title = title
        self.global_config = global_config

        # create a central widget
        self.graphics_view = pg.GraphicsView()
        self.graphics_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.graphics_layout)

        self.set_geometry(spacing=global_config.spacing, margins=global_config.margins)

    def set_geometry(self, spacing: int, margins: int):
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(*(margins for _ in range(4)))

        self.graphics_layout.setSpacing(spacing)
        self.graphics_layout.setContentsMargins(0, 0, 0, 0)

    def init_ui(self):
        self.layout.addWidget(self.graphics_view, 1, 1, 1, 1)
