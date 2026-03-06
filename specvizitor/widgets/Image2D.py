from astropy.convolution import convolve_fft, Gaussian2DKernel
from astropy.coordinates import SkyCoord
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS, FITSFixedWarning
import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
import logging
import warnings

from ..config import data_widgets
from ..io.catalog import Catalog
from ..io.viewer_data import get_wcs
from ..utils.qt_tools import get_qtransform_from_wcs
from ..utils.widgets import ColorBar, MyTextItem

from .ViewerElement import ViewerElement, LinkableItem


__all__ = [
    "Image2D"
]

logger = logging.getLogger(__name__)


@dataclass
class Image2DLevels:
    min: float = 0
    max: float = 1


class CentralAxis(Enum):
    X = auto()
    Y = auto()


class Image2D(ViewerElement):
    allowed_data_types: tuple[type] = (np.ndarray,)
    allowed_cbar_lims: tuple[str] = ('minmax', 'zscale', 'user')

    def __init__(self, cfg: data_widgets.Image, **kwargs):
        self.cfg = cfg

        self.image_item: pg.ImageItem | None = None

        self._cmap = pg.colormap.get('viridis')
        self.cbar: ColorBar | None = None
        self._default_levels: Image2DLevels | None = None

        super().__init__(cfg=cfg, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.container.setAspectLocked(True)

        self.image_item = pg.ImageItem()
        self.image_item.setLookupTable(self._cmap.getLookupTable())
        self.image_item.setBorder('k')  # add a border to the image

        self.cbar = ColorBar(imageItem=self.image_item, showHistogram=True, histHeightPercentile=99.0)
        self.cbar.setVisible(self.cfg.color_bar.visible)
        self.cbar.axisItem.setVisible(False)

    def populate(self):
        super().populate()

        self.graphics_layout.addItem(self.cbar, 0, 1)

    def init_view(self):
        super().init_view()
        self._default_levels = Image2DLevels()

    def _add_central_axes(self, axis=None):
        pen = pg.mkPen('w', width=1)
        nx, ny = self.data.shape[1], self.data.shape[0]

        if axis is CentralAxis.X:
            self.register_item((pg.PlotCurveItem([0, nx], [ny / 2, ny / 2], pen=pen)))
        elif axis is CentralAxis.Y:
            self.register_item((pg.PlotCurveItem([nx / 2, nx / 2], [0, ny], pen=pen)))

    def _add_central_crosshair(self):
        pen = pg.mkPen('w', width=1, style=QtCore.Qt.DashLine)
        x0, y0 = self.data.shape[1] // 2, self.data.shape[0] // 2
        dx, dy = 0.15 * x0, 0.15 * y0

        self.register_item(pg.PlotCurveItem([0, x0 - dx], [y0, y0], pen=pen))
        self.register_item(pg.PlotCurveItem([x0, x0], [0, y0 - dy], pen=pen))

    def _add_sources(self, cat: Catalog):
        try:
            ra = cat.get_col("ra")
            dec = cat.get_col("dec")
        except KeyError as e:
            logger.error(e)
            return

        try:
            wcs = get_wcs(self.meta)
        except Exception as e:
            logger.error(f"Failed to create the WCS object: {e} (widget: {self.title})")
            return

        try:
            coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            x, y = wcs.world_to_pixel(coord)
        except Exception as e:
            logger.error(f"Failed to calculate pixel coordinates of the sources: {e}")
            return

        nx, ny = self.data.shape[1], self.data.shape[0]
        mask = (x >= 0) & (x < nx) & (y >= 0) & (y < ny)
        x, y = x[mask], y[mask]
        source_ids = cat.get_col("id")[mask]

        s = 5
        for sid, xi, yi in zip(source_ids, x, y):
            reg_item = QtWidgets.QGraphicsEllipseItem(xi-s/2+0.5, yi-s/2+0.5, s, s)
            self.register_item(reg_item)

            text_item = MyTextItem(text=str(sid))
            self.register_item(text_item)
            text_item.setPos(xi, yi)
            text_item.clicked.connect(partial(self.id_selected.emit, str(sid)))
            text_item.color_changed.connect(partial(self._set_reg_color, reg_item))
            text_item.setColor("w")

    @QtCore.Slot(object)
    def _set_reg_color(self, reg_item: QtWidgets.QGraphicsItem, color):
        reg_item.setPen(pg.mkPen(color, width=2))

    def add_content(self, cat: Catalog | None):
        self.image_item.setImage(self.data, autoLevels=False)
        self.register_item(self.image_item)

        if self.cfg.central_axes.x:
            self._add_central_axes(CentralAxis.X)
        if self.cfg.central_axes.y:
            self._add_central_axes(CentralAxis.Y)

        if self.cfg.central_crosshair:
            self._add_central_crosshair()

        if self.cfg.show_sources and cat is not None:
            self._add_sources(cat)

    @property
    def has_defined_levels(self) -> bool:
        return np.any(np.isfinite(self.data)) and np.any(np.nonzero(self.data))

    def setup_view(self, cat_entry: Catalog | None):
        self.set_qtransform(cat_entry)
        self.set_default_range((0., float(self.data.shape[1])), (0., float(self.data.shape[0])),
                               apply_qtransform=True)

        # compute default image levels
        if self.has_defined_levels:
            limits_cfg = self.cfg.color_bar.limits
            if limits_cfg.type not in self.allowed_cbar_lims:
                logger.error(f'Unknown type of colorbar limits: {limits_cfg}.'
                             f'Supported types: {self.allowed_cbar_lims}')
            else:
                if limits_cfg.type == 'minmax':
                    l1, l2 = np.nanmin(self.data), np.nanmax(self.data)
                elif limits_cfg.type == 'zscale':
                    l1, l2 = ZScaleInterval().get_limits(self.data)
                else:
                    l1 = limits_cfg.min if limits_cfg.min is not None else np.nanmin(self.data)
                    l2 = limits_cfg.max if limits_cfg.max is not None else np.nanmax(self.data)

                self.set_default_levels((l1, l2))

        super().setup_view(cat_entry)

    def set_qtransform(self, cat_entry: Catalog | None):
        qtransform = QtGui.QTransform()

        if self.cfg.wcs_transform and self.meta is not None:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', FITSFixedWarning)
                w = WCS(self.meta)

            qtransform *= get_qtransform_from_wcs(w)

        rotation_angle = self.cfg.rotate
        if self.cfg.rotate == "auto":
            try:
                rotation_angle = float(cat_entry.get_col("PA"))
            except (TypeError, KeyError) as e:
                logger.warning(e)
                rotation_angle = None
        if rotation_angle:
            qtransform = qtransform.rotate(rotation_angle)

        self._qtransform = qtransform

    def set_default_levels(self, levels: tuple[float, float]):
        self._default_levels.min = levels[0]
        self._default_levels.max = levels[1]

    def set_levels(self, levels: tuple[float, float]):
        self.cbar.setLevels(levels)
        self.cbar._updateHistogram()  # the histogram is calculated using the current image levels

    def apply_qtransform(self, **kwargs):
        super().apply_qtransform(**kwargs)
        self.container.setAspectLocked(lock=True, ratio=self._qtransform.m22() / self._qtransform.m11())

    def smooth_data(self, sigma: float):
        if sigma > 0:
            gauss_kernel = Gaussian2DKernel(sigma)

            # FFT algorithm is faster for large arrays (n > 500), which is a typical case for astronomy images
            smoothed_data = convolve_fft(self.data, gauss_kernel, preserve_nan=True)
            logger.debug(f"Image smoothing applied (sigma: {sigma:.2f}, widget: {self.title})")
        else:
            smoothed_data = self.data

        self.image_item.setImage(smoothed_data, autoLevels=False)

    def reset_levels(self):
        self.set_levels((self._default_levels.min, self._default_levels.max))

    @QtCore.Slot(object)
    def reset_view(self, widget_links: dict | None = None):
        super().reset_view(widget_links=widget_links)

        if widget_links is None:
            widget_links = dict()

        if self.title not in widget_links.get(LinkableItem.COLORBAR, dict()):
            self.reset_levels()

    def _enter_zen_mode(self):
        super()._enter_zen_mode()
        self.cbar.setVisible(False)

    def _update_visibility(self):
        super()._update_visibility()
        self.cbar.setVisible(self.cfg.color_bar.visible)
