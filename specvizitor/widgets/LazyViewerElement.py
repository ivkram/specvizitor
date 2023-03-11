import pyqtgraph as pg

from ..utils import AbstractWidget
from ..config import docks, config


class LazyViewerElement(AbstractWidget):
    def __init__(self, cfg: docks.LazyViewerElement, title: str, global_viewer_config: config.DataViewer, **kwargs):
        super().__init__(**kwargs)

        self.cfg = cfg
        self.title = title
        self.global_config = global_viewer_config

        # create a central widget
        self.graphics_view = pg.GraphicsView()
        self.graphics_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.graphics_layout)

        self.set_geometry(spacing=global_viewer_config.spacing, margins=global_viewer_config.margins)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        super().set_geometry(spacing=spacing, margins=margins)

        self.graphics_layout.setSpacing(spacing)
        self.graphics_layout.setContentsMargins(0, 0, 0, 0)

    def init_ui(self):
        self.layout().addWidget(self.graphics_view, 1, 1, 1, 1)
