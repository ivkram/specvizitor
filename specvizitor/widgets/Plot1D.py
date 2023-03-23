from astropy.table import Table
import astropy.units as u
from astropy.units import UnitConversionError
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
class DefaultLimits:
    values: tuple[float, float]
    editable: tuple[bool, bool] = (False, False)

    def set(self, min_value: float | None, max_value: float | None):
        self.values = (min_value if min_value else self.values[0],
                       max_value if max_value else self.values[1])

        self.editable = (min_value is None, max_value is None)

    def update(self, limits: tuple[float, float]):
        self.values = (limits[0] if self.editable[0] else self.values[0],
                       limits[1] if self.editable[1] else self.values[1])


@dataclass
class AxisData:
    name: str
    value: np.ndarray
    unit: u.Unit | None = None
    unc: np.ndarray | None = None
    default_lims: DefaultLimits = field(init=False)
    log_allowed: bool = True

    def __post_init__(self):
        self.init_default_lims()

    def init_default_lims(self):
        self.default_lims = DefaultLimits(self.get_min_max(self.value))

    @staticmethod
    def get_min_max(data: np.ndarray) -> tuple[float, float]:
        return np.nanmin(data), np.nanmax(data)

    @property
    def label(self):
        label = f'{self.name}'
        if self.unit is not None:
            label += f' [{self.unit}]'
        return label

    def configure(self, cfg: docks.Axis):
        if cfg.unit:
            self.convert_units(cfg.unit)
        if cfg.scale == 'log':
            self.apply_log_scale()
        self.default_lims.set(cfg.limits[0], cfg.limits[1])

    def convert_units(self, new_unit: str):
        new_unit = u.Unit(new_unit)
        q = u.Quantity(1 * self.unit)

        try:
            q = q.to(new_unit).value
        except UnitConversionError as e:
            logger.error(e)
            return

        self.unit = new_unit
        self.value = self.value * q

        if self.unc is not None:
            self.unc = self.unc * q

        self.init_default_lims()

    def apply_log_scale(self):
        if not self.log_allowed:
            logger.error(f'Axis "{self.name}" cannot be converted to logarithmic scale')
            return

        self.name = f'log {self.name}'
        if self.unit:
            self.name += f' / {self.unit}'
            self.unit = None

        with np.errstate(invalid='ignore', divide='ignore'):
            self.value = np.log10(self.value)
        self.value[self.value == -np.inf] = 0

        self.unc = None
        self.init_default_lims()


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
        self._y_unc_plot: pg.PlotDataItem | None = None

    def set_plot_data(self, data: PlotData):
        self.data = data

    def configure_axes(self, x_cfg: docks.Axis, y_cfg: docks.Axis):
        self.data.x.configure(x_cfg)
        self.data.y.configure(y_cfg)

    def update_labels(self):
        self.setLabel('bottom', self.data.x.label, **self.appearance.label_style)
        self.setLabel('right', self.data.y.label, **self.appearance.label_style)

    def add_items(self):
        self._y_plot = self.plot(pen='k' if self.appearance.theme == 'light' else 'w')
        self._y_unc_plot = self.plot(pen='r')

    def plot_all(self):
        self._y_plot.setData(self.data.x.value, self.data.y.value)
        if self.data.y.unc is not None:
            self._y_unc_plot.setData(self.data.x.value, self.data.y.unc)

    def display(self):
        self.update_labels()
        self.add_items()
        self.plot_all()

    def reset_x_range(self):
        self.setXRange(*self.data.x.default_lims.values, padding=0)

    def reset_y_range(self):
        self.setYRange(*self.data.y.default_lims.values)

    def reset(self):
        self.reset_x_range()
        self.reset_y_range()

    def smooth(self, sigma: float):
        y_smoothed = gaussian_filter1d(self.data.y.value, sigma) if sigma > 0 else self.data.y.value

        self.data.y.default_lims.update(AxisData.get_min_max(y_smoothed))
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
