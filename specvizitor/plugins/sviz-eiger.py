import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from qtpy import QtCore

import logging

from ..io.catalog import Catalog
from .plugin_core import PluginCore
from ..widgets.ViewerElement import ViewerElement

from specvizitor.widgets.Image2D import Image2D

logger = logging.getLogger(__name__)


class Plugin(PluginCore):
    def overwrite_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    def tweak_docks(self, docks: dict[str, Dock]):
        pass

    def tweak_widgets(self, widgets: dict[str, ViewerElement], cat_entry: Catalog | None = None):
        spec_2d_stack: Image2D | None = widgets.get('Spectrum 2D [Stack]')
        spec_2d_mods: tuple[Image2D | None, Image2D | None] = (widgets.get(f'Spectrum 2D [Module A]'),
                                                               widgets.get(f'Spectrum 2D [Module B]'))

        spec_2d_array = tuple(spec_2d for spec_2d in (spec_2d_stack,) + spec_2d_mods if spec_2d is not None)

        if cat_entry:
            coords = self.get_emline_coords(cat_entry)
            for i, c in enumerate(coords):
                self.mark_emline(c[0], c[1], spec_2d_array, zoom=True if i == 0 else False,
                                 color='r' if i == 0 else 'white')

    @staticmethod
    def mark_emline(x0: float, y0: float, spec2d_array: tuple[Image2D], zoom=False, color='r'):
        zoom_level = 25
        dx, dy = 5, 5
        x1, x2 = x0 - zoom_level * dx, x0 + zoom_level * dx

        for spec_2d in spec2d_array:
            pen = pg.mkPen(color, width=2, style=QtCore.Qt.DashLine)

            spec_2d.register_item(pg.PlotCurveItem([x0 - dx, x0 + dx], [y0, y0], pen=pen))
            spec_2d.register_item(pg.PlotCurveItem([x0, x0], [y0 - dy, y0 + dy], pen=pen))

            if zoom:
                yrange = (0., float(spec_2d.data.shape[0]))
                spec_2d.set_default_range(xrange=(x1, x2), yrange=yrange, apply_qtransform=True, update=True)

    @staticmethod
    def get_emline_coords(cat_entry: Catalog | None) -> list[tuple[float, float]]:
        coords_array = []
        coord_colnames = [('X_IMAGE', 'Y_IMAGE')] + list((f'X_IMAGE_{i}', f'Y_IMAGE_{i}') for i in range(11))

        for i, cname_pair in enumerate(coord_colnames):
            try:
                x, y = cat_entry.get_col(cname_pair[0]), cat_entry.get_col(cname_pair[1])
            except KeyError:
                break
            else:
                # skip masked elements
                if np.ma.is_masked(x) or np.ma.is_masked(y):
                    continue

                # convert line coordinates to float
                try:
                    line_coords = (float(x), float(y))
                except TypeError as msg:
                    logger.error(msg)
                else:
                    coords_array.append(line_coords)

        return coords_array
