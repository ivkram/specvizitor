from astropy.convolution import convolve_fft, Gaussian2DKernel
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS, FITSFixedWarning
import numpy as np
import pyqtgraph as pg
from qtpy import QtCore

from dataclasses import dataclass
import logging
import warnings

from ..config import data_widgets
from ..utils.qt_tools import get_qtransform_matrix_from_wcs
from ..utils.widgets import ColorBar

from .ViewerElement import ViewerElement

logger = logging.getLogger(__name__)


@dataclass
class Image2DLevels:
    min: float = 0
    max: float = 1


class Image2D(ViewerElement):
    ALLOWED_DATA_TYPES = (np.ndarray,)
    ALLOWED_CBAR_LIMS = ('minmax', 'zscale', 'user')

    def __init__(self, cfg: data_widgets.Image, **kwargs):
        self.cfg = cfg

        self.image_item: pg.ImageItem | None = None

        self._cmap = pg.colormap.get('viridis')
        self.cbar: ColorBar | None = None
        self._default_levels: Image2DLevels | None = None

        super().__init__(cfg=cfg, **kwargs)

    def init_ui(self):
        super().init_ui()

        # lock the aspect ratio of the container
        self.container.setAspectLocked(True)

        # create an image item
        self.image_item = pg.ImageItem()
        self.image_item.setLookupTable(self._cmap.getLookupTable())
        self.image_item.setBorder('k')  # add a border to the image

        # create a color bar
        self.cbar = ColorBar(imageItem=self.image_item, showHistogram=True, histHeightPercentile=99.0)
        self.cbar.setVisible(self.cfg.color_bar.visible)

    def populate(self):
        super().populate()

        # add the color bar to the layout
        self.graphics_layout.addItem(self.cbar, 0, 1)

    def add_content(self):
        self.image_item.setImage(self.data, autoLevels=False)
        self.register_item(self.image_item)

        # add axes of symmetry to the image
        if self.cfg.central_axes in ('x', 'y', 'xy'):
            pen = 'w'
            x, y = self.data.shape[1], self.data.shape[0]

            if 'x' in self.cfg.central_axes:
                self.register_item((pg.PlotCurveItem([0, x], [y // 2, y // 2], pen=pen)))
            if 'y' in self.cfg.central_axes:
                self.register_item((pg.PlotCurveItem([x // 2, x // 2], [0, y], pen=pen)))

        # add a crosshair to the image
        if self.cfg.central_crosshair:
            pen = pg.mkPen('w', width=1, style=QtCore.Qt.DashLine)
            x0, y0 = self.data.shape[1] // 2, self.data.shape[0] // 2
            dx, dy = 0.15 * x0, 0.15 * y0

            self.register_item(pg.PlotCurveItem([0, x0 - dx], [y0, y0], pen=pen))
            self.register_item(pg.PlotCurveItem([x0, x0], [0, y0 - dy], pen=pen))

    def setup_view(self):
        # create a transformation matrix from metadata
        if self.cfg.wcs_transform and self.meta is not None:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FITSFixedWarning)
                w = WCS(self.meta)

            transformation_matrix = get_qtransform_matrix_from_wcs(w)
            self._qtransform.setMatrix(*transformation_matrix.flatten())

        self.set_default_range((0., float(self.data.shape[1])), (0., float(self.data.shape[0])),
                               apply_qtransform=True)

        # compute default image levels
        if np.any(np.isfinite(self.data)) and np.any(np.nonzero(self.data)):
            limits_cfg = self.cfg.color_bar.limits
            if limits_cfg.type not in self.ALLOWED_CBAR_LIMS:
                logger.error(f'Unknown type of colorbar limits: {limits_cfg}.'
                             f'Supported types: {self.ALLOWED_CBAR_LIMS}')
            else:
                if limits_cfg.type == 'minmax':
                    l1, l2 = np.nanmin(self.data), np.nanmin(self.data)
                elif limits_cfg.type == 'zscale':
                    l1, l2 = ZScaleInterval().get_limits(self.data)
                else:
                    l1 = limits_cfg.min if limits_cfg.min is not None else np.nanmin(self.data)
                    l2 = limits_cfg.max if limits_cfg.max is not None else np.nanmax(self.data)

                self.set_default_levels((l1, l2))

        super().setup_view()

    def set_default_levels(self, levels: tuple[float, float], update: bool = False):
        self._default_levels.min = levels[0]
        self._default_levels.max = levels[1]

        if update:
            self.reset_levels()

    def apply_qtransform(self, **kwargs):
        super().apply_qtransform(**kwargs)
        self.container.setAspectLocked(lock=True, ratio=self._qtransform.m22() / self._qtransform.m11())

    def smooth(self, sigma: float):
        if sigma > 0:
            # create a smoothing kernel
            gauss_kernel = Gaussian2DKernel(sigma)

            # FFT algorithm is faster for large arrays (n > 500), which is a typical case for astronomy images
            smoothed_data = convolve_fft(self.data, gauss_kernel, preserve_nan=True)
        else:
            smoothed_data = self.data

        self.image_item.setImage(smoothed_data, autoLevels=False)

    def reset_default_display_settings(self):
        super().reset_default_display_settings()
        self._default_levels = Image2DLevels()

    def reset_levels(self):
        self.cbar.setLevels((self._default_levels.min, self._default_levels.max))
        self.cbar._updateHistogram()  # the histogram is calculated using the current image levels

    def reset_view(self):
        super().reset_view()
        self.reset_levels()
