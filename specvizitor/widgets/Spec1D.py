import logging
from dataclasses import asdict

import numpy as np
from scipy.ndimage import gaussian_filter1d
from astropy.utils.decorators import lazyproperty
from astropy import units as u

import pyqtgraph as pg
from qtpy import QtCore

from ..utils import SmartSlider
from ..utils.table_tools import column_not_found_message

from .ViewerElement import ViewerElement
from ..appdata import AppData
from ..config import docks


logger = logging.getLogger(__name__)


class Spec1D(ViewerElement):
    def __init__(self, rd: AppData, cfg: docks.Spectrum, title: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, title=title, parent=parent)

        self.cfg = cfg

        # create a widget for the spectrum
        self._spec_1d_widget = pg.GraphicsView()
        self.core_widget = self._spec_1d_widget
        self._spec_1d_layout = pg.GraphicsLayout()
        self._spec_1d_widget.setCentralItem(self._spec_1d_layout)

        # create a redshift slider
        self._z_slider = SmartSlider(parameter='z', full_name='redshift', parent=self,
                                     **asdict(self.cfg.redshift_slider))
        self._z_slider.value_changed[float].connect(self._update_redshift)
        self.sliders.append(self._z_slider)

        # set up the plot
        self._spec_1d = self._spec_1d_layout.addPlot(name=title)
        self._spec_1d.setMouseEnabled(True, True)
        # self._spec_1d.hideAxis('left')
        self._spec_1d.showAxis('right')
        self._label_style = {'color': 'r', 'font-size': '20px'}

        # set up the spectral lines
        self._line_artists = {}
        # TODO: store colors in config
        line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self.rd.lines.list.items():
            line = pg.InfiniteLine(angle=90, movable=False, pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)

            self._line_artists[line_name] = {'line': line, 'label': label}

    @lazyproperty
    def default_xrange(self):
        return np.nanmin(self.data['wavelength']), np.nanmax(self.data['wavelength'])

    @lazyproperty
    def default_yrange(self):
        return np.nanmin(self.data['flux']), np.nanmax(self.data['flux'])

    @lazyproperty
    def _label_height(self):
        y_min, y_max = self.default_yrange
        return y_min + 0.6 * (y_max - y_min)

    def _plot_spec_1d(self, wave, flux):
        self._spec_1d_plot = self._spec_1d.plot(wave, flux, pen='k')

    def _plot_spec_1d_err(self, wave, flux_err):
        if 'flux_error' in self.data.colnames:
            self._spec_1d.plot(wave, flux_err, pen='r')

    def _update_redshift(self, redshift: float):
        try:
            scale = u.Unit(self.meta['TUNIT1']) / u.Unit(self.rd.lines.units)
        except (KeyError, ValueError):
            scale = 1

        for line_name, line_artist in self._line_artists.items():
            line_wave = self.rd.lines.list[line_name] * (1 + redshift) * scale
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(QtCore.QPointF(line_wave, self._label_height))

    def validate(self):
        for cname in ('wavelength', 'flux'):
            if cname not in self.data.colnames:
                logger.error(column_not_found_message(cname, self.rd.config.data.translate))
                return False
        return True

    def display(self):
        self._plot_spec_1d(self.data['wavelength'], self.data['flux'])
        self._plot_spec_1d_err(self.data['wavelength'], self.data['flux_error'])

        for line_name, line_artist in self._line_artists.items():
            self._spec_1d.addItem(line_artist['line'], ignoreBounds=True)
            self._spec_1d.addItem(line_artist['label'])

        for keyword, position in {'TUNIT1': 'bottom', 'TUNIT2': 'right'}.items():
            if self.meta.get(keyword):
                self._spec_1d.setLabel(position, self.meta[keyword], **self._label_style)

    def reset_view(self):
        self._z_slider.reset()
        self._spec_1d.setXRange(*self.default_xrange, padding=0)
        self._spec_1d.setYRange(*self.default_yrange)

    def clear_content(self):
        del self.default_xrange
        del self.default_yrange
        del self._label_height

        self._spec_1d.clear()

    def smooth(self, sigma: float):
        self._spec_1d.removeItem(self._spec_1d_plot)
        self._plot_spec_1d(self.data['wavelength'],
                           gaussian_filter1d(self.data['flux'], sigma) if sigma > 0 else self.data['flux'])
