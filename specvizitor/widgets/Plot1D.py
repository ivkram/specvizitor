import numpy as np
from astropy.table import Table
import pyqtgraph as pg
from scipy.ndimage import gaussian_filter1d

import logging

from ..config import data_widgets
from ..utils.table_tools import column_not_found_message
from .ViewerElement import ViewerElement

logger = logging.getLogger(__name__)


class Plot1D(ViewerElement):
    ALLOWED_DATA_TYPES = (Table,)

    def __init__(self, cfg: data_widgets.Plot1D, **kwargs):
        self.cfg = cfg

        self.plot_data_items: dict[str, pg.PlotDataItem] = {}

        super().__init__(cfg=cfg, **kwargs)

    def get_plot_data(self, cname: str, scale: str | None = None):
        try:
            plot_data = self.data[cname]
        except KeyError:
            logger.warning(column_not_found_message(cname))
            return None

        if scale == 'log':
            with np.errstate(invalid='ignore', divide='ignore'):
                plot_data = np.log10(plot_data)

        return plot_data

    def add_content(self):
        if self.cfg.plots is None:
            return

        default_pen = pg.getConfigOption('foreground')
        for label, line_plot in self.cfg.plots.items():
            x_data = self.get_plot_data(line_plot.x, scale=self.cfg.x_axis.scale)
            y_data = self.get_plot_data(line_plot.y, scale=self.cfg.y_axis.scale)

            if x_data is None or y_data is None:
                continue

            pen = default_pen if line_plot.color is None else line_plot.color
            name = label if not line_plot.hide_label else None
            if name and self.container.legend is None:
                self.container.addLegend(verSpacing=-10, pen=default_pen)

            plot_data_item = pg.PlotDataItem(x=x_data, y=y_data, pen=pen, name=name)
            self.plot_data_items[label] = plot_data_item
            self.register_item(plot_data_item)

    @staticmethod
    def update_axis_lims(lims_current: tuple[float, float] | None, plot_data: np.ndarray):
        plot_data = plot_data[~np.isinf(plot_data)]
        lims_new = (np.nanmin(plot_data), np.nanmax(plot_data))

        if lims_current is not None:
            lims_new = (min(lims_current[0], lims_new[0]), max(lims_current[1], lims_new[1]))

        return lims_new

    def setup_view(self):
        xlim, ylim = None, None
        for label, plot_data_item in self.plot_data_items.items():
            x_data, y_data = plot_data_item.getData()
            xlim = self.update_axis_lims(xlim, x_data)
            ylim = self.update_axis_lims(ylim, y_data)
        self.set_default_range(xlim, ylim, padding=0.05)

        super().setup_view()

    def smooth(self, sigma: float):
        for label, plot_data_item in self.plot_data_items.items():
            x_data, _ = plot_data_item.getData()
            y_data = self.get_plot_data(self.cfg.plots[label].y, scale=self.cfg.y_axis.scale)

            y_data_smoothed = gaussian_filter1d(y_data, sigma) if sigma > 0 else y_data
            plot_data_item.setData(x=x_data, y=y_data_smoothed)

    def clear_content(self):
        super().clear_content()

        # TODO: submit issue to the pyqtgraph repo
        # if self.container.legend:
        #     self.container.vb.removeItem(self.container.legend)  # removing from the ViewBox, not PlotItem
