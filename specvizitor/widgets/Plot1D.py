import numpy as np
from astropy.table import Table
from astropy.units import Quantity
import pyqtgraph as pg
from scipy.ndimage import gaussian_filter1d

import logging

from ..config import data_widgets
from ..io.catalog import Catalog

from .ViewerElement import ViewerElement


__all__ = ["Plot1D"]

logger = logging.getLogger(__name__)


class Plot1D(ViewerElement):
    allowed_data_types = (Table,)

    def __init__(self, cfg: data_widgets.Plot1D, **kwargs):
        self.cfg = cfg

        self.plot_data_items: dict[str, pg.PlotDataItem] = {}

        super().__init__(cfg=cfg, **kwargs)

    def get_plot_data(self, cname: str) -> Quantity | None:
        try:
            plot_data = self.data[cname].quantity
        except KeyError:
            logger.warning(f"Column not found: {cname} (widget: {self.title})")
            return None

        return Quantity(plot_data)  # return a copy to prevent any modifications to self.data

    def add_content(self):
        default_pen = pg.getConfigOption('foreground')
        for label, line_plot in self.cfg.plots.items():
            x_data, y_data = self.get_plot_data(line_plot.x), self.get_plot_data(line_plot.y)
            if x_data is None or y_data is None:
                continue

            # if axis labels are not set, adopt the plot labels
            if not self._axes.x.label:
                self._axes.x.label = line_plot.x
            if not self._axes.y.label:
                self._axes.y.label = line_plot.y

            # if axis units are not set, adopt the units of the data
            if not self._axes.x.unit:
                self._axes.x.unit = x_data.unit
            if not self._axes.y.unit:
                self._axes.y.unit = y_data.unit

            # apply scaling and unit conversion
            x_data, y_data = self.apply_xdata_transform(x_data), self.apply_ydata_transform(y_data)

            # add a legend to the plot
            pen = default_pen if line_plot.color is None else line_plot.color
            name = label if not line_plot.hide_label else None
            if name and self.container.legend is None:
                self.container.addLegend(verSpacing=-10, pen=default_pen)

            # create and register a plot data item
            plot_data_item = pg.PlotDataItem(x=x_data, y=y_data, pen=pen, name=name)
            self.plot_data_items[label] = plot_data_item
            self.register_item(plot_data_item)

    @staticmethod
    def calc_axis_lims(lims_current: tuple[float, float] | None, plot_data: np.ndarray):
        plot_data = plot_data[~np.isinf(plot_data)]
        if all(np.isnan(plot_data)):
            return lims_current
        lims_new = (np.nanmin(plot_data), np.nanmax(plot_data))

        if lims_current is not None:
            lims_new = (min(lims_current[0], lims_new[0]), max(lims_current[1], lims_new[1]))

        return lims_new

    def setup_view(self, cat_entry: Catalog | None):
        xlim, ylim = None, None
        for label, plot_data_item in self.plot_data_items.items():
            x_data, y_data = plot_data_item.getData()
            xlim = self.calc_axis_lims(xlim, x_data)
            ylim = self.calc_axis_lims(ylim, y_data)

        self.set_default_range(xlim, ylim)
        self.set_content_padding(ypad=0.05)

        super().setup_view(cat_entry)

    def smooth_data(self, sigma: float):
        for label, plot_data_item in self.plot_data_items.items():
            x_data, _ = plot_data_item.getData()
            y_data = self.get_plot_data(self.cfg.plots[label].y)
            y_data = self.apply_ydata_transform(y_data)

            y_data_smoothed = gaussian_filter1d(y_data, sigma) if sigma > 0 else y_data
            plot_data_item.setData(x=x_data, y=y_data_smoothed)

    def clear_content(self):
        # TODO: submit issue to the pyqtgraph repo
        # if self.container.legend:
        #     self.container.vb.removeItem(self.container.legend)  # removing from the ViewBox, not PlotItem

        super().clear_content()
