from astropy.visualization import ZScaleInterval
import numpy as np
import pyqtgraph as pg
from pgcolorbar.colorlegend import ColorLegendItem
from scipy.ndimage import gaussian_filter
from qtpy import QtGui, QtCore

import logging

from ..config import data_widgets
from .ViewerElement import ViewerElement

logger = logging.getLogger(__name__)


class Image2D(ViewerElement):
    def __init__(self, cfg: data_widgets.Image, **kwargs):
        self.cfg = cfg
        self.allowed_data_types = (np.ndarray,)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        self.image_item: pg.ImageItem | None = None
        self.container: pg.PlotItem | pg.ViewBox | None = None
        self._cbar: ColorLegendItem | None = None

        super().__init__(cfg=cfg, **kwargs)

    def init_ui(self):
        super().init_ui()

        # create an image item
        self.image_item = pg.ImageItem()
        self.image_item.setLookupTable(self._cmap.getLookupTable())

        # create an image container
        if self.cfg.container == 'PlotItem':
            # create a plot item
            self.container = pg.PlotItem(name=self.title)
            # self.container.hideAxis('left')
            self.container.showAxes((False, False, False, True), showValues=(False, False, False, True))
            self.container.hideButtons()

            # add a border to the image
            self.image_item.setBorder('k')
        else:
            # create a view box
            self.container = pg.ViewBox()

        # lock the aspect ratio
        self.container.setAspectLocked(True)

        # add the image to the container
        self.container.addItem(self.image_item)

        # create a color bar
        self._cbar = ColorLegendItem(imageItem=self.image_item, showHistogram=True, histHeightPercentile=99.0)
        self._cbar.setVisible(self.cfg.color_bar.visible)

    def populate(self):
        super().populate()

        # add the container to the layout
        self.graphics_layout.addItem(self.container, 0, 0)

        # add the color bar to the layout
        self.graphics_layout.addItem(self._cbar, 0, 1)

    def _load_data(self, *args, **kwargs):
        super()._load_data(*args, **kwargs)
        if self.data is None:
            return

        # rotate the image
        if self.cfg.rotate is not None:
            self.rotate(self.cfg.rotate)

        # scale the data points
        if self.cfg.scale is not None:
            self.scale(self.cfg.scale)

    def add_content(self):
        self.image_item.setImage(self.data, autoLevels=False)

        # add axes of symmetry to the image
        if self.cfg.central_axes in ('x', 'y', 'xy'):
            pen = 'w'
            x, y = self.data.shape[1], self.data.shape[0]

            axes = []
            if 'x' in self.cfg.central_axes:
                axes.append(pg.PlotCurveItem([0, x], [y // 2, y // 2], pen=pen))
            if 'y' in self.cfg.central_axes:
                axes.append(pg.PlotCurveItem([x // 2, x // 2], [0, y], pen=pen))

            for ax in axes:
                self.register_item(ax)

        # add a crosshair to the image
        if self.cfg.crosshair:
            pen = pg.mkPen('w', width=1, style=QtCore.Qt.DashLine)
            x0, y0 = self.data.shape[1] // 2, self.data.shape[0] // 2
            dx, dy = 0.15 * x0, 0.15 * y0

            crosshair_x = pg.PlotCurveItem([0, x0 - dx], [y0, y0], pen=pen)
            crosshair_y = pg.PlotCurveItem([x0, x0], [0, y0 - dy], pen=pen)

            self.register_item(crosshair_x)
            self.register_item(crosshair_y)

    def reset_view(self):
        # TODO: allow to choose between min/max and zscale?
        if np.any(np.isfinite(self.data)):
            self._cbar.setLevels(ZScaleInterval().get_limits(self.data))
        self.container.autoRange(padding=0)

    def clear_content(self):
        self.image_item.clear()
        self.remove_registered_items()

    def smooth(self, sigma: float):
        self.image_item.setImage(gaussian_filter(self.data, sigma) if sigma > 0 else self.data, autoLevels=False)

    def rotate(self, angle: int):
        self.data = np.rot90(self.data, k=angle // 90)

    def scale(self, scale: float):
        self.data *= scale

    def register_item(self, item: pg.GraphicsItem):
        self.container.addItem(item)
        self._added_items.append(item)

    def apply_qtransform(self, qtransform: QtGui.QTransform):
        self.image_item.setTransform(qtransform)
        for item in self._added_items:
           item.setTransform(qtransform)

    def remove_registered_items(self):
        for item in self._added_items:
            self.container.removeItem(item)
        self._added_items = []
