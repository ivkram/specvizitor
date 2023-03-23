import pyqtgraph as pg
from qtpy import QtWidgets

from ..config import docks, config
from .AbstractWidget import AbstractWidget


class LazyViewerElement(AbstractWidget):
    def __init__(self, title: str, cfg: docks.LazyViewerElement, appearance: config.Appearance, parent=None):
        self.title = title
        self.cfg = cfg
        self.appearance = appearance

        self.graphics_view: pg.GraphicsView | None = None
        self.graphics_layout: pg.GraphicsLayout | None = None

        self._added_items: list[pg.GraphicsItem] = []

        super().__init__(parent=parent)
        self.setEnabled(False)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        super().set_geometry(spacing=spacing, margins=margins)

        self.graphics_layout.setSpacing(spacing)
        self.graphics_layout.setContentsMargins(0, 0, 5, 5)

    def init_ui(self):
        self.graphics_view = pg.GraphicsView(parent=self)
        self.graphics_layout = pg.GraphicsLayout()
        self.graphics_view.setCentralItem(self.graphics_layout)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=self.appearance.viewer_spacing, margins=self.appearance.viewer_margins)

    def populate(self):
        self.layout().addWidget(self.graphics_view, 1, 1, 1, 1)

    def register_item(self, item: pg.GraphicsItem):
        self._added_items.append(item)

    def remove_registered_items(self):
        for item in self._added_items:
            self.container.removeItem(item)
        self._added_items = []
