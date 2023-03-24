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
class DefaultAxisLimits:
    values: tuple[float, float]
    editable: tuple[bool, bool] = (True, True)

    @classmethod
    def init_from_array(cls, data: np.ndarray):
        return cls(cls.get_min_max(data))

    @staticmethod
    def get_min_max(data: np.ndarray) -> tuple[float, float] | None:
        if np.sum(~np.isnan(data)) == 0:
            return 0, 1
        else:
            return np.nanmin(data), np.nanmax(data)

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
    default_lims: DefaultAxisLimits = field(init=False)
    log_allowed: bool = True

    def __post_init__(self):
        self.default_lims = DefaultAxisLimits.init_from_array(self.value)

    def set_value(self, value: np.ndarray):
        self.value = value
        self.default_lims = DefaultAxisLimits.init_from_array(self.value)

    @property
    def label(self):
        label = self.name
        if self.unit is not None:
            # TODO: convert to inline unicode after next astropy release
            label += f' [{self.unit}]'.replace('Angstrom', 'Å')
        return label

    def apply_settings(self, cfg: docks.Axis):
        if cfg.unit:
            try:
                new_unit = u.Unit(cfg.unit)
            except ValueError:
                logger.error(f'Invalid unit: {cfg.unit}')
            else:
                self.convert_units(new_unit)
        if cfg.scale == 'log':
            self.apply_log_scale()
        self.default_lims.set(cfg.limits.min, cfg.limits.max)

    def scale(self, scaling_factor: float):
        self.set_value(self.value * scaling_factor)
        if self.unc is not None:
            self.unc = self.unc * scaling_factor

    def convert_units(self, new_unit: u.Unit):
        if self.unit is None:
            logger.error(f'Unit conversion failed: axis unit not found (axis name: {self.name})')
            return

        q = u.Quantity(1 * self.unit)
        try:
            q = q.to(new_unit)
        except UnitConversionError as e:
            logger.error(e)
            return

        self.unit = new_unit
        self.scale(q.value)

    def apply_log_scale(self):
        if not self.log_allowed:
            logger.error(f'Axis `{self.name}` cannot be converted to logarithmic scale')
            return

        self.name = f'log {self.name}'
        if self.unit:
            self.name += f' / ({self.unit})'
            self.unit = None

        with np.errstate(invalid='ignore', divide='ignore'):
            new_value = np.log10(self.value)
        new_value[new_value == -np.inf] = 0

        self.set_value(new_value)
        self.unc = None


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

    def update_labels(self, x_label: docks.Label, y_label: docks.Label):
        self.setLabel('bottom' if x_label.position is None else x_label.position, self.data.x.label)
        self.setLabel('left' if y_label.position is None else y_label.position, self.data.y.label)

    def add_items(self):
        self._y_plot = self.plot(pen='k' if self.appearance.theme == 'light' else 'w')
        self._y_unc_plot = self.plot(pen='r')

    def plot_all(self):
        self._y_plot.setData(self.data.x.value, self.data.y.value)
        if self.data.y.unc is not None:
            self._y_unc_plot.setData(self.data.x.value, self.data.y.unc)

    def display(self):
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

        self.data.y.default_lims.update(DefaultAxisLimits.get_min_max(y_smoothed))
        self._y_plot.setData(self.data.x.value, y_smoothed)


class Plot1D(ViewerElement):
    plot_data_loaded = QtCore.Signal(object)
    plot_refreshed = QtCore.Signal()
    labels_updated = QtCore.Signal(docks.Label, docks.Label)

    def __init__(self, cfg: docks.Plot1D, **kwargs):
        self.cfg = cfg
        self.allowed_data_types = (Table,)

        self.plot_item: Plot1DItem | None = None
        self.plot_data: PlotData | None = None

        super().__init__(cfg=cfg, **kwargs)

    def create_plot_item(self):
        self.plot_item = Plot1DItem(name=self.title, appearance=self.appearance)

    def init_ui(self):
        super().init_ui()
        self.create_plot_item()

    def populate(self):
        super().populate()
        self.graphics_layout.addItem(self.plot_item)

    def init_plot_data(self) -> PlotData | None:
        t: Table = self.data
        col_names = []

        for i, cname in enumerate((self.cfg.x_axis.name, self.cfg.y_axis.name)):
            if cname is None:
                col_names.append(t.colnames[i])
            else:
                if cname not in t.colnames:
                    logger.error(column_not_found_message(cname))
                    return
                col_names.append(cname)

        axes_data = [AxisData(cname, t[cname].value, unit=t[cname].unit) for cname in col_names]
        plot_data = PlotData(x=axes_data[0], y=axes_data[1])

        return plot_data

    def set_plot_data(self):
        self.plot_item.set_plot_data(self.plot_data)
        self.plot_data_loaded.emit(self.plot_data)

    def update_labels(self):
        label_cfg = self.cfg.x_axis.label, self.cfg.y_axis.label
        self.plot_item.update_labels(*label_cfg)
        self.labels_updated.emit(*label_cfg)

    def _load_data(self, *args, **kwargs):
        super()._load_data(*args, **kwargs)
        if self.data is None:
            self.plot_data = None
            return

        self.plot_data = self.init_plot_data()
        if not self.plot_data:
            self.data, self.meta = None, None
            return

        self.plot_data.x.apply_settings(self.cfg.x_axis)
        self.plot_data.y.apply_settings(self.cfg.y_axis)

        self.set_plot_data()
        self.update_labels()

    def add_content(self):
        self.plot_item.display()
        self.content_added.emit()

    def clear_content(self):
        self.plot_item.clear()
        self.content_cleared.emit()

    def redraw(self):
        self.plot_item.plot_all()
        self.plot_refreshed.emit()

        for s in self.sliders:
            s.update_from_slider()

    def reset_view(self):
        self.plot_item.reset()
        self.view_reset.emit()

    def smooth(self, sigma: float):
        self.plot_item.smooth(sigma)
        self.smoothing_applied.emit(sigma)
