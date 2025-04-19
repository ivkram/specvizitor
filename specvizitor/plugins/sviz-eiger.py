import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from qtpy import QtCore

import logging

from specvizitor.io.catalog import Catalog
from specvizitor.plugins.plugin_core import PluginCore

from specvizitor.widgets.ViewerElement import ViewerElement
from specvizitor.widgets.Image2D import Image2D

logger = logging.getLogger(__name__)


class Plugin(PluginCore):
    def override_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    def update_docks(self, docks: dict[str, Dock], cat_entry: Catalog | None = None):
        rgb_stack = self.get_rgb_stack(docks)

        if not rgb_stack:
            return

        # fix a pyqtgraph bug, see the sviz-grizli plugin
        if len(rgb_stack) > 1:
            for d in rgb_stack.values():
                d.label.setDim(True)

        # raise the relevant RGB dock to top
        if rgb_stack and cat_entry:
            self.raise_rgb_dock(rgb_stack, cat_entry)

    def update_active_widgets(self, widgets: dict[str, ViewerElement], cat_entry: Catalog | None = None):

        spec_2d_stack: Image2D | None = widgets.get('Spectrum 2D [Stack]')
        spec_2d_beams: tuple[Image2D | None, ...] = tuple(widgets.get(f'Spectrum 2D [{label}]') for label in
                                                          ['Module A', 'Module B', 'R1, A', 'R1, B', 'R2, A', 'R2, B'])

        spec_2d_arr = tuple(spec_2d for spec_2d in (spec_2d_stack,) + spec_2d_beams if spec_2d is not None)

        # mark emission lines in the 2D spectra
        if cat_entry:
            self.mark_emline_from_cat(spec_2d_arr, cat_entry)

    def mark_emline_from_cat(self, spec_2d_arr: tuple[Image2D], cat_entry: Catalog):
        coords = self.get_emline_coords(cat_entry)
        for i, c in enumerate(coords):
            # add "-0.5" assuming that X_IMAGE and Y_IMAGE are calculated from Source-Extractor
            self.mark_emline_in_spec_2d(c[0]-0.5, c[1]-0.5, spec_2d_arr, zoom=True if i == 0 else False,
                                        color='r' if i == 0 else 'white')

    @staticmethod
    def get_emline_coords(cat_entry: Catalog) -> list[tuple[float, float]]:
        coords_array = []
        coord_colnames = [('X_IMAGE', 'Y_IMAGE')] + list((f'X_IMAGE_{i}', f'Y_IMAGE_{i}') for i in range(2, 11))

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

    def get_rgb_stack(self, docks: dict[str, Dock]):
        rgb_docks = {title: d for title, d in docks.items() if "RGB" in title}
        rgb_stack = self.get_stacked_docks(rgb_docks)

        return rgb_stack

    @staticmethod
    def mark_emline_in_spec_2d(x0: float, y0: float, spec_2d_arr: tuple[Image2D], zoom=False, color='r'):
        zoom_level = 25
        dx, dy = 5, 5
        x1, x2 = x0 - zoom_level * dx, x0 + zoom_level * dx

        for spec_2d in spec_2d_arr:
            pen = pg.mkPen(color, width=2, style=QtCore.Qt.DashLine)

            spec_2d.register_item(pg.PlotCurveItem([x0 - dx, x0 + dx], [y0, y0], pen=pen))
            spec_2d.register_item(pg.PlotCurveItem([x0, x0], [y0 - dy, y0 + dy], pen=pen))

            if zoom:
                yrange = (0., float(spec_2d.data.shape[0]))
                spec_2d.set_default_range(xrange=(x1, x2), yrange=yrange, apply_qtransform=True, update=True)

    @staticmethod
    def raise_rgb_dock(rgb_stack: dict[str, Dock], cat_entry: Catalog):
        try:
            field = cat_entry.get_col('FIELD')
        except KeyError:
            return

        for title, d in rgb_stack.items():
            if field in title:
                d.raiseDock()
                return
