from astropy.convolution import convolve_fft, Gaussian2DKernel
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS, FITSFixedWarning
import numpy as np
import pyqtgraph as pg
from qtpy import QtGui, QtCore

from dataclasses import dataclass
import logging
import warnings

from ..config import data_widgets
from ..utils.widgets import ColorBar

from .ViewerElement import ViewerElement

logger = logging.getLogger(__name__)


@dataclass
class Image2DRange:
    x: tuple[float, float] | None = None
    y: tuple[float, float] | None = None

    @property
    def is_set(self) -> bool:
        return not (self.x is None and self.y is None)


@dataclass
class Image2DLevels:
    min: float = 0
    max: float = 1


class Image2D(ViewerElement):
    def __init__(self, cfg: data_widgets.Image, **kwargs):
        self.cfg = cfg
        self.allowed_data_types = (np.ndarray,)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        self.image_item: pg.ImageItem | None = None
        self.container: pg.PlotItem | pg.ViewBox | None = None
        self._cbar: ColorBar | None = None

        self.qtransform = QtGui.QTransform()

        self._default_range = Image2DRange()
        self._default_levels = Image2DLevels()

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
        self._cbar = ColorBar(imageItem=self.image_item, showHistogram=True, histHeightPercentile=99.0)
        self._cbar.setVisible(self.cfg.color_bar.visible)

    def populate(self):
        super().populate()

        # add the container to the layout
        self.graphics_layout.addItem(self.container, 0, 0)

        # add the color bar to the layout
        self.graphics_layout.addItem(self._cbar, 0, 1)

    def post_init(self):
        # link view(s)
        if self.cfg.link_view:
            for axis, widget_title in self.cfg.link_view.items():
                if axis == 'x':
                    self.container.setXLink(widget_title)
                elif axis == 'y':
                    self.container.setYLink(widget_title)

    def load_data(self, *args, **kwargs):
        super().load_data(*args, **kwargs)
        if self.data is None:
            return

        # scale the data
        if self.cfg.scale is not None:
            self.scale(self.cfg.scale)

        # create a transformation matrix from the WCS object
        if self.cfg.wcs_transform and self.meta is not None:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FITSFixedWarning)
                w = WCS(self.meta)

            transformation_matrix = np.zeros((3, 3))
            transformation_matrix[:2, :2] = w.pixel_scale_matrix
            # transformation_matrix[:2, 2] = w.wcs.crpix
            transformation_matrix[2, :2] = w.wcs.crval
            transformation_matrix[2, 2] = 1.0

            self.qtransform.setMatrix(*transformation_matrix.flatten())

        if np.any(np.isfinite(self.data)):
            # TODO: allow to choose between min/max and zscale?
            self.set_default_levels(ZScaleInterval().get_limits(self.data[np.nonzero(self.data)]))

    def add_content(self):
        self.image_item.setImage(self.data, autoLevels=False)
        self.apply_qtransform()

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

    def apply_qtransform(self):
        self.image_item.setTransform(self.qtransform)
        self.container.setAspectLocked(lock=True, ratio=self.qtransform.m22() / self.qtransform.m11())
        for item in self._added_items:
            item.setTransform(self.qtransform)
    
    def reset_range(self):
        if self._default_range.is_set:
            self.container.setRange(xRange=self._default_range.x, yRange=self._default_range.y, padding=0)
        else:
            self.container.autoRange(padding=0)

    def reset_levels(self):
        self._cbar.setLevels((self._default_levels.min, self._default_levels.max))
        self._cbar._updateHistogram()  # the histogram is calculated using the current image levels

    def set_default_range(self, xrange: tuple[float, float] | None = None, yrange: tuple[float, float] | None = None,
                          update: bool = False):
        if xrange:
            self._default_range.x = xrange
        if yrange:
            self._default_range.y = yrange

        if update:
            self.reset_range()

    def set_default_levels(self, levels: tuple[float, float], update: bool = False):
        self._default_levels.min = levels[0]
        self._default_levels.max = levels[1]

        if update:
            self.reset_levels()

    def reset_view(self):
        self.reset_range()
        self.reset_levels()

    def clear_content(self):
        self.image_item.clear()
        self.remove_registered_items()

        self.qtransform = QtGui.QTransform()

        self._default_range = Image2DRange()
        self._default_levels = Image2DLevels()
    
    def scale(self, scale: float):
        self.data *= scale

    def smooth(self, sigma: float):
        if sigma > 0:
            # create a smoothing kernel
            gauss_kernel = Gaussian2DKernel(sigma)

            # FFT algorithm is faster for large arrays (n > 500), which is a typical case for astronomy images
            smoothed_data = convolve_fft(self.data, gauss_kernel, preserve_nan=True)
        else:
            smoothed_data = self.data

        self.image_item.setImage(smoothed_data, autoLevels=False)

    def register_item(self, item: pg.GraphicsItem):
        item.setTransform(self.qtransform)
        self.container.addItem(item)
        self._added_items.append(item)

    def remove_registered_items(self):
        for item in self._added_items:
            self.container.removeItem(item)
        self._added_items = []
