import logging
from dataclasses import asdict
from copy import deepcopy

from specutils import Spectrum1D
from astropy.nddata import StdDevUncertainty

import numpy as np
from scipy.ndimage import gaussian_filter1d
from astropy.utils.decorators import lazyproperty
from astropy import units as u

import pyqtgraph as pg
from qtpy import QtCore

from ..utils import SmartSlider
from ..utils.table_tools import column_not_found_message

from .ViewerElement import ViewerElement
from .LazyViewerElement import LazyViewerElement
from ..appdata import AppData
from ..config import docks
from ..config.spectral_lines import SpectralLines


logger = logging.getLogger(__name__)


class Spec1DItem(pg.PlotItem):
    def __init__(self, spec: Spectrum1D | None = None, lines: SpectralLines | None = None,
                 window: tuple[float, float] | None = None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.setMouseEnabled(True, True)
        self.showAxis('right')

        self.spec = spec
        self.lines = SpectralLines() if lines is None else lines
        self.window = window

        self._flux_plot = None
        self._flux_err_plot = None

        self._label_style = {'color': 'r', 'font-size': '20px'}
        # set up the spectral lines
        self._line_artists = {}
        # TODO: store colors in config
        line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self.lines.list.items():
            line = pg.InfiniteLine(angle=90, movable=False, pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)
            self._line_artists[line_name] = {'line': line, 'label': label}

    @lazyproperty
    def default_xrange(self):
        return np.nanmin(self.spec.spectral_axis.value), np.nanmax(self.spec.spectral_axis.value)

    @lazyproperty
    def default_yrange(self):
        return np.nanmin(self.spec.flux.value), np.nanmax(self.spec.flux.value)

    @lazyproperty
    def _label_height(self):
        y_min, y_max = self.default_yrange
        return y_min + 0.6 * (y_max - y_min)

    def update_labels(self):
        self.setLabel('bottom', self.spec.spectral_axis.unit, **self._label_style)
        self.setLabel('right', self.spec.flux.unit, **self._label_style)

    def add_items(self):
        self._flux_plot = self.plot(pen='k')
        self._flux_err_plot = self.plot(pen='r')

        for line_name, line_artist in self._line_artists.items():
            self.addItem(line_artist['line'], ignoreBounds=True)
            self.addItem(line_artist['label'])

    def set_line_positions(self, scale0: float = 1):
        scale = scale0 * self.spec.spectral_axis.unit / u.Unit(self.lines.units)

        for line_name, line_artist in self._line_artists.items():
            line_wave = self.lines.list[line_name] * scale
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(QtCore.QPointF(line_wave, self._label_height))

        if self.window is not None:
            self.setXRange(*map(lambda x: x * scale, self.window), padding=0)

    def plot_all(self):
        self._flux_plot.setData(self.spec.wavelength.value, self.spec.flux.value)
        if self.spec.uncertainty is not None:
            self._flux_err_plot.setData(self.spec.wavelength.value, self.spec.uncertainty.array)

    def display(self):
        self.update_labels()
        self.add_items()
        self.plot_all()

    def reset(self):
        if self.window is None:
            self.setXRange(*self.default_xrange, padding=0)
        self.setYRange(*self.default_yrange)

    def clear(self):
        del self.default_xrange
        del self.default_yrange
        del self._label_height

        super().clear()

    def smooth(self, sigma: float):
        self._flux_plot.setData(self.spec.wavelength.value,
                                gaussian_filter1d(self.spec.flux.value, sigma) if sigma > 0 else self.spec.flux.value)


class Spec1DRegion(LazyViewerElement):
    def __init__(self, line: str, rd: AppData, cfg: docks.SpectrumRegion, title: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, title=title, parent=parent)

        self.cfg = cfg
        self.line = line

        # set up the plot
        lines = deepcopy(self.rd.lines)
        lines = SpectralLines(units=lines.units, list={line: lines.list[line]})
        window = (lines.list[line] - self.cfg.window / 2, lines.list[line] + self.cfg.window / 2)

        self.spec_1d = Spec1DItem(lines=lines, window=window, name=title)
        self.graphics_layout.addItem(self.spec_1d)


class Spec1D(ViewerElement):
    def __init__(self, rd: AppData, cfg: docks.Spectrum, title: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, title=title, parent=parent)

        self.cfg = cfg

        self.lazy_widgets: list[Spec1DRegion] = []

        # create viewer elements zoomed on various spectral regions
        if self.cfg.follow is not None:
            for line, line_cfg in self.cfg.follow.items():
                self.lazy_widgets.append(Spec1DRegion(line=line, rd=rd, cfg=line_cfg, title=f"{title} [{line}]",
                                                      parent=parent))

        # create a redshift slider
        self._z_slider = SmartSlider(parameter='z', full_name='redshift', parent=self,
                                     **asdict(self.cfg.redshift_slider))
        self._z_slider.value_changed[float].connect(self._redshift_changed_action)
        self.sliders.append(self._z_slider)

        # set up the plot
        self.spec_1d = Spec1DItem(lines=self.rd.lines, name=title)
        self.graphics_layout.addItem(self.spec_1d)

    def _redshift_changed_action(self, redshift: float):
        self.spec_1d.set_line_positions(1 + redshift)
        for w in self.lazy_widgets:
            w.spec_1d.set_line_positions(1 + redshift)

    def _load_data(self):
        super()._load_data()
        if self.data is None:
            spec = None
        else:
            # create a Spectrum1D object
            try:
                spectral_axis_unit = u.Unit(self.meta[f'TUNIT{self.data.colnames.index("wavelength") + 1}'])
            except (KeyError, ValueError):
                logger.warning('Failed to read spectral axis units')
                spectral_axis_unit = u.Unit(self.rd.lines.units)

            try:
                flux_unit = u.Unit(self.meta[f'TUNIT{self.data.colnames.index("flux") + 1}'])
            except (KeyError, ValueError):
                logger.warning('Failed to read flux units')
                flux_unit = u.Unit('1e-17 erg cm-2 s-1 AA-1')

            unc = StdDevUncertainty(self.data['flux_error']) if 'flux_error' in self.data.colnames else None

            spec = Spectrum1D(spectral_axis=self.data['wavelength'] * spectral_axis_unit,
                              flux=self.data['flux'] * flux_unit, uncertainty=unc)

        self.spec_1d.spec = spec
        for w in self.lazy_widgets:
            w.spec_1d.spec = spec

    def validate(self):
        for cname in ('wavelength', 'flux'):
            if cname not in self.data.colnames:
                logger.error(column_not_found_message(cname, self.rd.config.data.translate))
                return False
        return True

    def display(self):
        self.spec_1d.display()
        for w in self.lazy_widgets:
            w.spec_1d.display()

    def reset_view(self):
        self.spec_1d.reset()
        for w in self.lazy_widgets:
            w.spec_1d.reset()

        self._z_slider.reset()

    def clear_content(self):
        self.spec_1d.clear()
        for w in self.lazy_widgets:
            w.spec_1d.clear()

    def smooth(self, sigma: float):
        self.spec_1d.smooth(sigma)
        for w in self.lazy_widgets:
            w.spec_1d.smooth(sigma)
