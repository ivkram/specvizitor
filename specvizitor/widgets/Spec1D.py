import logging
from dataclasses import asdict
from functools import partial

from specutils import Spectrum1D

import numpy as np
from scipy.ndimage import gaussian_filter1d
from astropy import units as u

import pyqtgraph as pg
from qtpy import QtCore

from ..utils import SmartSliderWithEditor

from .ViewerElement import ViewerElement
from .LazyViewerElement import LazyViewerElement
from ..config import docks
from ..config.spectral_lines import SpectralLines
from ..appdata import AppData


logger = logging.getLogger(__name__)


class Spec1DItem(pg.PlotItem):
    def __init__(self, spec: Spectrum1D | None = None, lines: SpectralLines | None = None,
                 window: tuple[float, float] | None = None,
                 label_style: dict[str, str] | None = None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.setMouseEnabled(True, True)
        self.showAxes((True, True, True, True), showValues=(True, False, True, True))
        self.hideButtons()

        self.spec = spec
        self.lines = SpectralLines() if lines is None else lines
        self.window = window

        self.label_style = {} if label_style is None else label_style

        self._flux_plot = None
        self._flux_err_plot = None

        self._default_xrange = None
        self._default_yrange = None

        # set up the spectral lines
        self._line_artists = {}
        # TODO: store colors in config
        line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self.lines.list.items():
            line = pg.InfiniteLine(angle=90, movable=False, pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)
            self._line_artists[line_name] = {'line': line, 'label': label}

    @staticmethod
    def get_default_range(data: np.ndarray):
        return np.nanmin(data), np.nanmax(data)

    def get_label_height(self):
        y_min, y_max = self._default_yrange
        return y_min + 0.6 * (y_max - y_min)

    def set_spec(self, spec: Spectrum1D | None):
        self.spec = spec

        if spec is not None:
            self._default_xrange = self.get_default_range(self.spec.spectral_axis.value)
            self._default_yrange = self.get_default_range(self.spec.flux.value)

    def update_labels(self):
        self.setLabel('bottom', self.spec.spectral_axis.unit, **self.label_style)
        self.setLabel('right', self.spec.flux.unit, **self.label_style)

    def add_items(self):
        self._flux_plot = self.plot(pen='k' if pg.getConfigOption('background') == 'w' else 'w')
        self._flux_err_plot = self.plot(pen='r')

        for line_name, line_artist in self._line_artists.items():
            self.addItem(line_artist['line'], ignoreBounds=True)
            self.addItem(line_artist['label'])

    def fit_in_window(self, window):
        self.setXRange(window[0].to(self.spec.spectral_axis.unit).value,
                       window[1].to(self.spec.spectral_axis.unit).value,
                       padding=0)

    def set_line_positions(self, redshift: float = 0):
        scale0 = 1 + redshift
        label_height = self.get_label_height()

        for line_name, line_artist in self._line_artists.items():
            line_wave = (self.lines.list[line_name] * u.Unit(self.lines.wave_unit)).to(self.spec.spectral_axis.unit)
            line_wave = line_wave.value * scale0
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(QtCore.QPointF(line_wave, label_height))

        if self.window is not None:
            self.fit_in_window((scale0 * (self.window[0] + self.window[1]) / 2 - (self.window[1] - self.window[0]) / 2,
                                scale0 * (self.window[0] + self.window[1]) / 2 + (self.window[1] - self.window[0]) / 2))

    def plot_all(self):
        self._flux_plot.setData(self.spec.spectral_axis.value, self.spec.flux.value)
        if self.spec.uncertainty is not None:
            self._flux_err_plot.setData(self.spec.spectral_axis.value, self.spec.uncertainty.array)

    def display(self):
        self.update_labels()
        self.add_items()
        self.plot_all()

    def reset(self):
        if self.window is None:
            self.setXRange(*self._default_xrange, padding=0)
        self.setYRange(*self._default_yrange)

    def smooth(self, sigma: float):
        new_flux = gaussian_filter1d(self.spec.flux.value, sigma) if sigma > 0 else self.spec.flux.value

        self._default_yrange = self.get_default_range(new_flux)
        self._flux_plot.setData(self.spec.spectral_axis.value, new_flux)


class Spec1DRegion(LazyViewerElement):
    def __init__(self, line: tuple[str, u.Quantity], cfg: docks.SpectrumRegion, **kwargs):
        super().__init__(cfg=cfg, **kwargs)

        self.line = line
        self.cfg = cfg

        window_center = line[1]
        window_size = u.Quantity(self.cfg.window_size)
        window = (window_center - window_size / 2, window_center + window_size / 2)

        lines = SpectralLines(wave_unit=line[1].unit, list={line[0]: line[1].value})

        self.spec_1d = Spec1DItem(lines=lines, window=window, name=self.title,
                                  label_style=self.global_config.label_style)
        self.graphics_layout.addItem(self.spec_1d)


class Spec1D(ViewerElement):
    redshift_changed = QtCore.Signal(float)

    def __init__(self, cfg: docks.Spectrum, lines: SpectralLines | None = None, **kwargs):
        super().__init__(cfg=cfg, **kwargs)

        self.lines = lines
        self.cfg = cfg

        self.lazy_widgets: list[Spec1DRegion] = []
        self.region_items: list[pg.LinearRegionItem] = []

        self.allowed_data_types = (Spectrum1D,)

        # create a redshift slider
        self._z_slider = self.create_redshift_slider(**asdict(self.cfg.redshift_slider))
        self.sliders.append(self._z_slider)

        # set up the plot
        self.spec_1d = Spec1DItem(lines=self.lines, name=self.title, label_style=self.global_config.label_style)
        self.graphics_layout.addItem(self.spec_1d)

        # create widgets zoomed on selected spectral lines
        if self.lines is not None and self.cfg.tracked_lines is not None:
            self.lazy_widgets, self.region_items = self.create_spectral_regions(self.cfg.tracked_lines, self.lines)

    def create_redshift_slider(self, **kwargs):
        redshift_slider = SmartSliderWithEditor(parameter='z', full_name='redshift', parent=self, **kwargs)
        redshift_slider.value_changed[float].connect(self._redshift_changed_action)
        return redshift_slider

    def create_spectral_regions(self, tracked_lines: dict[str, docks.SpectrumRegion], lines: SpectralLines)\
            -> tuple[list[Spec1DRegion], list[pg.LinearRegionItem]]:

        region_widgets = []
        region_items = []

        n = 0
        for line, line_cfg in tracked_lines.items():
            if line in lines.list.keys():
                spec_region = Spec1DRegion(line=(line, lines.list[line] * u.Unit(lines.wave_unit)), cfg=line_cfg,
                                           title=f"{self.title} [{line}]", global_viewer_config=self.global_config,
                                           parent=self.parent())
                self.data_loaded.connect(spec_region.spec_1d.set_spec)
                self.content_added.connect(spec_region.spec_1d.display)
                self.view_reset.connect(spec_region.spec_1d.reset)
                self.content_cleared.connect(spec_region.spec_1d.clear)
                self.smoothing_applied.connect(spec_region.spec_1d.smooth)
                self.redshift_changed.connect(spec_region.spec_1d.set_line_positions)
                region_widgets.append(spec_region)

                lr = pg.LinearRegionItem()
                region_items.append(lr)

                spec_region.spec_1d.sigXRangeChanged.connect(partial(self._region_widget_changed_action, n))
                lr.sigRegionChanged.connect(partial(self._region_item_changed_action, n))

                n += 1
            else:
                logger.warning(f'Unknown spectral line: {line}')

        return region_widgets, region_items

    def _redshift_changed_action(self, redshift: float):
        self.spec_1d.set_line_positions(redshift)
        self.redshift_changed.emit(redshift)

    def _region_item_changed_action(self, n: int):
        region = self.region_items[n].getRegion()
        self.lazy_widgets[n].spec_1d.fit_in_window((region[0] * self.spec_1d.spec.spectral_axis.unit,
                                                    region[1] * self.spec_1d.spec.spectral_axis.unit))

    def _region_widget_changed_action(self, n: int):
        self.region_items[n].setRegion(self.lazy_widgets[n].spec_1d.getViewBox().viewRange()[0])

    def _load_data(self, rd: AppData):
        super()._load_data(rd=rd)
        if self.data is None:
            return

        self.spec_1d.set_spec(self.data)
        self.data_loaded.emit(self.data)

    def add_content(self):
        self.spec_1d.display()
        for lr in self.region_items:
            self.spec_1d.addItem(lr)

        self.content_added.emit()

    def reset_view(self):
        self.spec_1d.reset()
        self._z_slider.reset()
        self._redshift_changed_action(self._z_slider.value)

        self.view_reset.emit()

    def clear_content(self):
        self.spec_1d.clear()
        self.content_cleared.emit()

    def smooth(self, sigma: float):
        self.spec_1d.smooth(sigma)
        self.smoothing_applied.emit(sigma)
