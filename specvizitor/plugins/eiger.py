from astropy.table import Row
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from qtpy import QtCore

import logging

from .plugin_core import PluginCore
from ..widgets.ViewerElement import ViewerElement

from specvizitor.widgets.Image2D import Image2D

logger = logging.getLogger(__name__)


class Plugin(PluginCore):
    def overwrite_widget_configs(self, widgets: dict[str, ViewerElement]):
        pass

    def tweak_docks(self, docks: dict[str, Dock]):
        pass

    def tweak_widgets(self, widgets: dict[str, ViewerElement], obj_cat: Row | None = None):
        spec_2d_stack: Image2D | None = widgets.get('Spectrum 2D [Stack]')
        spec_2d_mods: tuple[Image2D | None, Image2D | None] = (widgets.get(f'Spectrum 2D [Module A]'),
                                                               widgets.get(f'Spectrum 2D [Module B]'))

        x0, y0 = self.get_emline_coords(obj_cat)
        if x0 is not None and y0 is not None:
            dx, dy = 5, 5

            for spec_2d in (spec_2d_stack,) + spec_2d_mods:
                if spec_2d is None:
                    continue

                pen = pg.mkPen('r', width=2, style=QtCore.Qt.DashLine)

                crosshair_x = pg.PlotCurveItem([x0 - dx, x0 + dx], [y0, y0], pen=pen)
                crosshair_y = pg.PlotCurveItem([x0, x0], [y0 - dy, y0 + dy], pen=pen)

                spec_2d.register_item(crosshair_x)
                spec_2d.register_item(crosshair_y)

    @staticmethod
    def get_emline_coords(obj_cat: Row | None) -> tuple[float | None, float | None]:
        if obj_cat is None:
            return None, None

        coords = ()
        keywords = ('X_IMAGE', 'Y_IMAGE')

        for i, coord_keyword in enumerate(keywords):
            coord = None

            for cname in obj_cat.colnames:
                if coord_keyword in cname:
                    try:
                        coord = float(obj_cat[cname])
                    except TypeError as msg:
                        logger.error(msg)
                    break

            if coord is None:
                logger.error(f'Object coordinates not found (coordinate: {coord_keyword})')
                return None, None
            else:
                coords += (coord,)

        return coords
