import logging

import numpy as np
import pyqtgraph as pg
from astropy.visualization import ZScaleInterval
from scipy.ndimage import gaussian_filter

from pgcolorbar.colorlegend import ColorLegendItem

from ..utils.widget_tools import wrap_widget

from .ViewerElement import ViewerElement
from ..runtime.appdata import AppData
from ..runtime import config


logger = logging.getLogger(__name__)


class Image2D(ViewerElement):
    def __init__(self, rd: AppData, cfg: config.Image, alias: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, alias=alias, parent=parent)

        self.cfg = cfg

        # add a widget for the image
        self._image_2d_widget = pg.GraphicsView()
        self._image_2d_layout = pg.GraphicsLayout()
        self._image_2d_widget.setCentralItem(self._image_2d_layout)

        if self.cfg.interactive:
            # set up the color map
            self._cmap = pg.colormap.get('viridis')

            # set up the image and the view box
            self.image_2d_plot = self._image_2d_layout.addPlot(name=alias)

            self.image_2d = pg.ImageItem(border='k')
            self.image_2d.setLookupTable(self._cmap.getLookupTable())
            self.image_2d_plot.addItem(self.image_2d)

            # set up the color bar
            self._cbar = ColorLegendItem(imageItem=self.image_2d, showHistogram=True, histHeightPercentile=99.0)
            self._image_2d_layout.addItem(self._cbar, 0, 1)

            # lock the aspect ratio
            self.image_2d_plot.setAspectLocked(True)

        else:
            self.smoothing_slider.setHidden(True)

            self._view_box = pg.ViewBox()
            self._image_2d_layout.setContentsMargins(0, 0, 0, 0)
            self._view_box.setAspectLocked(True)
            self.image_2d = pg.ImageItem()
            self._view_box.addItem(self.image_2d)
            self._image_2d_layout.addItem(self._view_box)

    def init_ui(self):
        self.layout.addLayout(wrap_widget(self.smoothing_slider), 1, 1)
        self.layout.addWidget(self._image_2d_widget, 1, 2)

    def load_data(self):
        super().load_data()
        if self.data is None:
            return

        # rotate the image
        if self.cfg.rotate is not None:
            self.rotate(self.cfg.rotate)

        # scale the data points
        if self.cfg.scale is not None:
            self.scale(self.cfg.scale)

    def validate(self):
        return True

    def display(self):
        self.image_2d.setImage(self.data)

    def reset_view(self):
        if self.cfg.interactive:
            # TODO: allow to choose between min/max and zscale?
            self._cbar.setLevels(ZScaleInterval().get_limits(self.data))
            self.image_2d_plot.autoRange()
        else:
            self._view_box.autoRange(padding=0)

    def clear_content(self):
        self.image_2d.clear()

    def smooth(self, sigma: float):
        self.image_2d.setImage(gaussian_filter(self.data, sigma) if sigma > 0 else self.data)

    def rotate(self, angle: int):
        self.data = np.rot90(self.data, k=angle // 90)

    def scale(self, scale: float):
        self.data *= scale
