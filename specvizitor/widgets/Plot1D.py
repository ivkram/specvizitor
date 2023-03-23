from astropy.table import Table
import astropy.units as u
import numpy as np
import pyqtgraph as pg
from scipy.ndimage import gaussian_filter1d
from qtpy import QtCore

from dataclasses import dataclass, field
import logging

from ..config import config, docks
from ..utils.table_tools import column_not_found_message

from .ViewerElement import ViewerElement

logger = logging.getLogger(__name__)


@dataclass
class AxisData:
    name: str
    value: np.ndarray
    unit: u.Unit | None = None
    unc: np.ndarray | None = None
    default_limits: tuple[float, float] = field(init=False)
    frozen_limits: tuple[bool, bool] = field(init=False)

    def __post_init__(self):
        self.reset_default_limits()

    @staticmethod
    def get_limits(data: np.ndarray) -> tuple[float, float]:
        return np.nanmin(data), np.nanmax(data)

    def reset_default_limits(self):
        self.default_limits = self.get_limits(self.value)
        self.frozen_limits = (False, False)

    def update_default_limits(self, limits: tuple[float, float]):
        self.default_limits = (self.default_limits[0] if self.frozen_limits[0] else limits[0],
                               self.default_limits[1] if self.frozen_limits[1] else limits[1])

    @property
    def label(self):
        label = f'{self.name}'
        if self.unit is not None:
            label += f' [{self.unit}]'
        return label

    def apply_scale(self, scale: 'str'):
        if scale == 'log':
            self.name = f'log {self.name}'
            self.value = np.log10(self.value)
            self.unc = None
        self.reset_default_limits()

    def apply_limits(self, min_value: float | None, max_value: float | None):
        self.default_limits = (self.default_limits[0] if min_value is None else min_value,
                               self.default_limits[1] if max_value is None else max_value)

        self.frozen_limits = (min_value is not None, max_value is not None)


@dataclass
class PlotData:
    x: AxisData
    y: AxisData


class Plot1DItem(pg.PlotItem):
    def __init__(self, appearance: config.Appearance = config.Appearance(), **kwargs):
        self.appearance = appearance

        super().__init__(**kwargs)
        self.setMouseEnabled(True, True)
        self.hideButtons()

        self.data: PlotData | None = None

        self._y_plot: pg.PlotDataItem | None = None
        self._y_err_plot: pg.PlotDataItem | None = None

    def set_plot_data(self, data: PlotData):
        self.data = data

    def configure_axes(self, x_cfg: docks.Axis, y_cfg: docks.Axis):
        self.data.x.apply_scale(x_cfg.scale)
        self.data.y.apply_scale(y_cfg.scale)

        self.data.x.apply_limits(x_cfg.limits[0], x_cfg.limits[1])
        self.data.y.apply_limits(y_cfg.limits[0], y_cfg.limits[1])

    def update_labels(self):
        self.setLabel('bottom', self.data.x.label, **self.appearance.label_style)
        self.setLabel('right', self.data.y.label, **self.appearance.label_style)

    def add_items(self):
        self._y_plot = self.plot(pen='k' if self.appearance.theme == 'light' else 'w')
        self._y_err_plot = self.plot(pen='r')

    def plot_all(self):
        self._y_plot.setData(self.data.x.value, self.data.y.value)
        if self.data.y.unc is not None:
            self._y_err_plot.setData(self.data.x.value, self.data.y.unc)

    def display(self):
        self.update_labels()
        self.add_items()
        self.plot_all()

    def reset_x_range(self):
        self.setXRange(*self.data.x.default_limits, padding=0)

    def reset_y_range(self):
        self.setYRange(*self.data.y.default_limits)

    def reset(self):
        self.reset_x_range()
        self.reset_y_range()

    def smooth(self, sigma: float):
        y_smoothed = gaussian_filter1d(self.data.y.value, sigma) if sigma > 0 else self.data.y.value

        self.data.y.update_default_limits(AxisData.get_limits(y_smoothed))
        self._y_plot.setData(self.data.x.value, y_smoothed)


class Plot1D(ViewerElement):
    plot_data_loaded = QtCore.Signal(object)

    def __init__(self, cfg: docks.Plot1D, **kwargs):
        self.cfg = cfg
        self.allowed_data_types = (Table,)

        self.plot_1d: Plot1DItem | None = None

        super().__init__(cfg=cfg, **kwargs)

    def create_plot_item(self):
        self.plot_1d = Plot1DItem(name=self.title, appearance=self.appearance)

    def init_ui(self):
        super().init_ui()
        self.create_plot_item()

    def populate(self):
        super().populate()
        self.graphics_layout.addItem(self.plot_1d)

    def init_plot_data(self):
        t: Table = self.data
        x_cname = self.cfg.x_axis.name
        y_cname = self.cfg.y_axis.name

        if x_cname is None:
            x_cname = t.colnames[0]
        if y_cname is None:
            y_cname = t.colnames[1]

        for cname in (x_cname, y_cname):
            if cname not in t.colnames:
                logger.error(column_not_found_message(cname))
                return False

        plot_data = PlotData(x=AxisData(x_cname, t[x_cname]),
                             y=AxisData(y_cname, t[y_cname]))

        return plot_data

    def _load_data(self, *args, **kwargs):
        super()._load_data(*args, **kwargs)
        if self.data is None:
            return

        plot_data = self.init_plot_data()
        if not plot_data:
            self.data, self.meta = None, None
            return
        self.plot_1d.set_plot_data(plot_data)
        self.plot_1d.configure_axes(self.cfg.x_axis, self.cfg.y_axis)
        self.plot_data_loaded.emit(plot_data)

    def add_content(self):
        self.plot_1d.display()
        self.content_added.emit()

    def clear_content(self):
        self.plot_1d.clear()
        self.content_cleared.emit()

    def reset_view(self):
        self.plot_1d.reset()
        self.view_reset.emit()

    def smooth(self, sigma: float):
        self.plot_1d.smooth(sigma)
        self.smoothing_applied.emit(sigma)
