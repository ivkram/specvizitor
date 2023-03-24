from astropy.table import Table
from astropy import units as u
from astropy.units.core import UnitConversionError
import pyqtgraph as pg
from qtpy import QtCore
from specutils import Spectrum1D

from dataclasses import asdict
from functools import partial
import logging

from ..config import docks
from ..config.spectral_lines import SpectralLines

from .LazyViewerElement import LazyViewerElement
from .Plot1D import AxisData, PlotData, Plot1D, Plot1DItem
from .SmartSlider import SmartSliderWithEditor

logger = logging.getLogger(__name__)


class Spec1DItem(Plot1DItem):
    def __init__(self, lines: SpectralLines | None = None,
                 window: tuple[float, float] | None = None, **kwargs):

        super().__init__(**kwargs)
        self.showAxes((True, True, True, True), showValues=(True, False, True, True))

        self.lines = SpectralLines() if lines is None else lines
        self.window = window

        # set up the spectral lines
        self._line_artists = {}
        # TODO: store colors in config
        line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self.lines.list.items():
            line = pg.InfiniteLine(pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)
            self._line_artists[line_name] = {'line': line, 'label': label}

    def add_items(self):
        for line_name, line_artist in self._line_artists.items():
            self.addItem(line_artist['line'], ignoreBounds=True)
            self.addItem(line_artist['label'])

        super().add_items()

    def fit_in_window(self, window):
        self.setXRange(window[0].to(self.data.x.unit).value,
                       window[1].to(self.data.x.unit).value,
                       padding=0)

    def get_line_label_height(self):
        y_min, y_max = self.data.y.default_lims.values
        return y_min + 0.6 * (y_max - y_min)

    def set_line_positions(self, redshift: float = 0):
        scale0 = 1 + redshift
        label_height = self.get_line_label_height()

        for line_name, line_artist in self._line_artists.items():
            line_wave = (self.lines.list[line_name] * u.Unit(self.lines.wave_unit)).to(self.data.x.unit)
            line_wave = line_wave.value * scale0
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(QtCore.QPointF(line_wave, label_height))

        if self.window is not None:
            self.fit_in_window((scale0 * (self.window[0] + self.window[1]) / 2 - (self.window[1] - self.window[0]) / 2,
                                scale0 * (self.window[0] + self.window[1]) / 2 + (self.window[1] - self.window[0]) / 2))

    def reset_x_range(self):
        if self.window is None:
            super().reset_x_range()


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


class Spec1D(Plot1D):
    redshift_changed = QtCore.Signal(float)

    def __init__(self, cfg: docks.Spectrum, lines: SpectralLines | None = None, **kwargs):
        self.lines = lines
        self.cfg = cfg
        self.allowed_data_types = (Spectrum1D, Table)

        self.plot_item: Spec1DItem | None = None
        self.z_slider: SmartSliderWithEditor | None = None

        self.lazy_widgets: list[Spec1DRegion] = []
        self.region_items: list[pg.LinearRegionItem] = []

        super().__init__(cfg=cfg, **kwargs)

    def create_plot_item(self):
        self.plot_item = Spec1DItem(lines=self.lines, name=self.title, appearance=self.appearance)

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
        self.z_slider = SmartSliderWithEditor(parameter='z', full_name='redshift', parent=self,
                                              **asdict(self.cfg.redshift_slider))
        self.sliders.append(self.z_slider)

        # create widgets zoomed on selected spectral lines
        self.create_spectral_regions()

        # connect signals from the redshift slider to slots
        self.z_slider.value_changed[float].connect(self._redshift_changed_action)

        # connect region items and region widgets between each other
        for i, (w, lr) in enumerate(zip(self.lazy_widgets, self.region_items)):
            self.plot_data_loaded.connect(w.spec_1d.set_plot_data)
            self.labels_updated.connect(w.spec_1d.update_labels)
            self.content_added.connect(w.spec_1d.display)
            self.plot_refreshed.connect(w.spec_1d.plot_all)
            self.view_reset.connect(w.spec_1d.reset)
            self.content_cleared.connect(w.spec_1d.clear)
            self.smoothing_applied.connect(w.spec_1d.smooth)
            self.redshift_changed.connect(w.spec_1d.set_line_positions)

            w.spec_1d.sigXRangeChanged.connect(partial(self._region_widget_changed_action, i))
            lr.sigRegionChanged.connect(partial(self._region_item_changed_action, i))

    def _redshift_changed_action(self, redshift: float):
        self.plot_item.set_line_positions(redshift)
        self.redshift_changed.emit(redshift)

    def _region_item_changed_action(self, n: int):
        region = self.region_items[n].getRegion()
        self.lazy_widgets[n].spec_1d.fit_in_window((region[0] * self.plot_item.data.x.unit,
                                                    region[1] * self.plot_item.data.x.unit))

    def _region_widget_changed_action(self, n: int):
        self.region_items[n].setRegion(self.lazy_widgets[n].spec_1d.getViewBox().viewRange()[0])

    def init_plot_data(self) -> PlotData | None:
        # init plot data from Spectrum 1D
        if isinstance(self.data, Spectrum1D):
            spec = self.data
            plot_data = PlotData(x=AxisData('wavelength', spec.spectral_axis.value, spec.spectral_axis.unit,
                                            log_allowed=False),
                                 y=AxisData('flux', spec.flux.value, spec.flux.unit, spec.uncertainty.array))
            return plot_data

        # init plot data from Table
        plot_data = super().init_plot_data()
        if plot_data is None:
            return plot_data

        # make sure that the spectral axis units are correct
        try:
            q = u.Quantity(plot_data.x.value)
            if plot_data.x.unit is not None:
                q *= plot_data.x.unit
            q.to('AA')
        except UnitConversionError:
            logger.error(f'Invalid spectral axis unit: {plot_data.x.unit}')
            return None

        return plot_data

    def add_content(self):
        for lr in self.region_items:
            self.plot_item.addItem(lr)
        super().add_content()

    def reset_view(self):
        self.z_slider.reset()
        self._redshift_changed_action(self.z_slider.value)
        super().reset_view()
