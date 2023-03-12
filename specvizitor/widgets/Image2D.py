import logging

import numpy as np
import pyqtgraph as pg
from astropy.visualization import ZScaleInterval
from scipy.ndimage import gaussian_filter

from pgcolorbar.colorlegend import ColorLegendItem

from .ViewerElement import ViewerElement
from ..config import docks
from ..appdata import AppData


logger = logging.getLogger(__name__)


class Image2D(ViewerElement):
    def __init__(self, cfg: docks.Image, **kwargs):
        super().__init__(cfg=cfg, **kwargs)

        self.cfg = cfg

        self.allowed_data_types = (np.ndarray,)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # create an image item
        self.image_2d = pg.ImageItem()
        self.image_2d.setLookupTable(self._cmap.getLookupTable())

        # create an image container
        if self.cfg.container == 'PlotItem':
            # create a plot item
            self.container = pg.PlotItem(name=self.title)
            # self.container.hideAxis('left')
            self.container.showAxes((False, False, False, True), showValues=(False, False, False, True))
            self.container.hideButtons()

            # add a border to the image
            self.image_2d.setBorder('k')
        else:
            # create a view box
            self.container = pg.ViewBox()

        # add the image to the container
        self.container.addItem(self.image_2d)

        # lock the aspect ratio
        self.container.setAspectLocked(True)

        # add the container to the layout
        self.graphics_layout.addItem(self.container, 0, 0)

        # create a color bar
        self._cbar = ColorLegendItem(imageItem=self.image_2d, showHistogram=True, histHeightPercentile=99.0)
        self._cbar.setVisible(self.cfg.color_bar.visible)

        # add the color bar to the layout
        self.graphics_layout.addItem(self._cbar, 0, 1)

    def _load_data(self, rd: AppData):
        super()._load_data(rd=rd)
        if self.data is None:
            return

        # rotate the image
        self.rotate(self.cfg.rotate)

        # scale the data points
        self.scale(self.cfg.scale)

    def display(self):
        self.image_2d.setImage(self.data)

    def reset_view(self):
        # TODO: allow to choose between min/max and zscale?
        self._cbar.setLevels(ZScaleInterval().get_limits(self.data))
        self.container.autoRange(padding=0)

    def clear_content(self):
        self.image_2d.clear()

    def smooth(self, sigma: float):
        self.image_2d.setImage(gaussian_filter(self.data, sigma) if sigma > 0 else self.data)

    def rotate(self, angle: int):
        self.data = np.rot90(self.data, k=angle // 90)

    def scale(self, scale: float):
        self.data *= scale
