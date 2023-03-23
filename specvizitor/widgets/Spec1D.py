from astropy import units as u
import numpy as np
import pyqtgraph as pg
from qtpy import QtCore
from scipy.ndimage import gaussian_filter1d
from specutils import Spectrum1D

from dataclasses import asdict
from functools import partial
import logging

from ..config import config, docks
from ..config.spectral_lines import SpectralLines

from .LazyViewerElement import LazyViewerElement
from .ViewerElement import ViewerElement
from .SmartSlider import SmartSliderWithEditor

logger = logging.getLogger(__name__)


class Spec1DItem(pg.PlotItem):
    def __init__(self, spec: Spectrum1D | None = None, lines: SpectralLines | None = None,
                 window: tuple[float, float] | None = None,
                 appearance: config.Appearance = config.Appearance(),
                 *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.setMouseEnabled(True, True)
        self.showAxes((True, True, True, True), showValues=(True, False, True, True))
        self.hideButtons()

        self.spec = spec
        self.lines = SpectralLines() if lines is None else lines
        self.window = window

        self.appearance = appearance

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
            line = pg.InfiniteLine(pen=line_pen)
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
        self.setLabel('bottom', self.spec.spectral_axis.unit, **self.appearance.label_style)
        self.setLabel('right', self.spec.flux.unit, **self.appearance.label_style)

    def add_items(self):
        self._flux_plot = self.plot(pen='k' if self.appearance.theme == 'light' else 'w')
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
    def __init__(self, title: str, line: tuple[str, u.Quantity], cfg: docks.SpectrumRegion, **kwargs):

        self.cfg = cfg
        self.line = line

        window_center = line[1]
        window_size = u.Quantity(self.cfg.window_size)
        self.window = (window_center - window_size / 2, window_center + window_size / 2)

        self.spec_1d: Spec1DItem | None = None

        super().__init__(title=title, cfg=cfg, **kwargs)

    def init_ui(self):
        super().init_ui()

        lines = SpectralLines(wave_unit=self.line[1].unit, list={self.line[0]: self.line[1].value})
        self.spec_1d = Spec1DItem(lines=lines, window=self.window, name=self.title, appearance=self.appearance)

    def populate(self):
        super().populate()
        self.graphics_layout.addItem(self.spec_1d)


class Spec1D(ViewerElement):
    redshift_changed = QtCore.Signal(float)

    def __init__(self, cfg: docks.Spectrum, lines: SpectralLines | None = None, **kwargs):
        self.lines = lines
        self.cfg = cfg

        self.allowed_data_types = (Spectrum1D,)

        self._z_slider: SmartSliderWithEditor | None = None
        self.spec_1d: Spec1DItem | None = None

        self.lazy_widgets: list[Spec1DRegion] = []
        self.region_items: list[pg.LinearRegionItem] = []

        super().__init__(cfg=cfg, **kwargs)

    def create_spectral_regions(self):
        if self.lines is None or self.cfg.tracked_lines is None:
            return

        region_widgets = []
        region_items = []

        for line, line_cfg in self.cfg.tracked_lines.items():
            if line in self.lines.list.keys():
                spec_region = Spec1DRegion(title=f"{self.title} [{line}]",
                                           line=(line, self.lines.list[line] * u.Unit(self.lines.wave_unit)),
                                           cfg=line_cfg, appearance=self.appearance,
                                           parent=self.parent())

                region_widgets.append(spec_region)

                lr = pg.LinearRegionItem()
                region_items.append(lr)
            else:
                logger.warning(f'Unknown spectral line: {line}')

        self.lazy_widgets = region_widgets
        self.region_items = region_items

    def init_ui(self):
        super().init_ui()

        # create a redshift slider
        self._z_slider = SmartSliderWithEditor(parameter='z', full_name='redshift', parent=self,
                                               **asdict(self.cfg.redshift_slider))
        self.sliders.append(self._z_slider)

        # set up the plot
        self.spec_1d = Spec1DItem(lines=self.lines, name=self.title, appearance=self.appearance)

        # create widgets zoomed on selected spectral lines
        self.create_spectral_regions()

        # connect signals from the redshift slider to slots
        self._z_slider.value_changed[float].connect(self._redshift_changed_action)

        # connect region items and region widgets between each other
        for i, (w, lr) in enumerate(zip(self.lazy_widgets, self.region_items)):
            self.data_loaded.connect(w.spec_1d.set_spec)
            self.content_added.connect(w.spec_1d.display)
            self.view_reset.connect(w.spec_1d.reset)
            self.content_cleared.connect(w.spec_1d.clear)
            self.smoothing_applied.connect(w.spec_1d.smooth)
            self.redshift_changed.connect(w.spec_1d.set_line_positions)

            w.spec_1d.sigXRangeChanged.connect(partial(self._region_widget_changed_action, i))
            lr.sigRegionChanged.connect(partial(self._region_item_changed_action, i))

    def populate(self):
        super().populate()
        self.graphics_layout.addItem(self.spec_1d)

    def _redshift_changed_action(self, redshift: float):
        self.spec_1d.set_line_positions(redshift)
        self.redshift_changed.emit(redshift)

    def _region_item_changed_action(self, n: int):
        region = self.region_items[n].getRegion()
        self.lazy_widgets[n].spec_1d.fit_in_window((region[0] * self.spec_1d.spec.spectral_axis.unit,
                                                    region[1] * self.spec_1d.spec.spectral_axis.unit))

    def _region_widget_changed_action(self, n: int):
        self.region_items[n].setRegion(self.lazy_widgets[n].spec_1d.getViewBox().viewRange()[0])

    def _load_data(self, *args, **kwargs):
        super()._load_data(*args, **kwargs)
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
