import pathlib
import logging
import copy

import numpy as np
from astropy.io import fits
from astropy.utils.decorators import lazyproperty

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from ..utils.params import read_yaml
from ..utils.widgets import CustomSlider
from .colors import viridis_more

from ..io.loader import get_filename


logger = logging.getLogger(__name__)


class Spec1D(QtWidgets.QWidget):
    def __init__(self, loader, config, parent=None):
        self._loader = loader
        self._config = config

        self._j = None
        self._cat = None

        # load the list of spectral lines
        self._lines = read_yaml('default_lines.yml', local=True)

        super().__init__(parent)
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        # add a label
        self._label = QtWidgets.QLabel()
        grid.addWidget(self._label, 1, 1)

        # add a widget for the spectrum
        self._spec_1d_widget = pg.GraphicsLayoutWidget()
        self._spec_1d_widget.setMinimumSize(*map(int, self._config['min_size']))
        grid.addWidget(self._spec_1d_widget, 2, 1, 1, 3)

        # add a redshift slider
        self._z_slider = CustomSlider(QtCore.Qt.Horizontal, **self._config['slider'])
        self._z_slider.valueChanged[int].connect(self._update_from_slider)
        self._z_slider.setToolTip('Slide to redshift.')
        grid.addWidget(self._z_slider, 3, 1, 1, 1)

        # add a line edit for changing the redshift
        self._redshift_editor = QtWidgets.QLineEdit()
        self._redshift_editor.returnPressed.connect(self._update_from_editor)
        self._redshift_editor.setMaximumWidth(120)
        grid.addWidget(QtWidgets.QLabel('z = ', self), 3, 2, 1, 1)
        grid.addWidget(self._redshift_editor, 3, 3, 1, 1)

        self.setLayout(grid)

        # set up the plot
        self._spec_1d = self._spec_1d_widget.addPlot()
        self._label_style = {'color': 'r', 'font-size': '20px'}

        # set up the spectral lines
        self._line_artists = {}
        line_color = np.array(viridis_more[9]) * 255
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self._lines['lambda'].items():
            line = pg.InfiniteLine(angle=90, movable=False, pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)

            self._line_artists[line_name] = {'line': line, 'label': label}

    @lazyproperty
    def _filename(self):
        return get_filename(self._loader['data']['dir'], self._config['search_mask'], self._cat['id'][self._j])

    @lazyproperty
    def _hdu(self):
        try:
            with fits.open(self._filename) as hdul:
                header, data = hdul[1].header, hdul[1].data
        except ValueError:
            logger.error('1D spectrum not found (object ID: {})'.format(self._cat['id'][self._j]))
            return
        else:
            return header, data

    @lazyproperty
    def _default_xrange(self):
        return np.nanmin(self._hdu[1]['wave']), np.nanmax(self._hdu[1]['wave'])

    @lazyproperty
    def _default_yrange(self):
        return np.nanmin(self._hdu[1]['flux']), np.nanmax(self._hdu[1]['flux'])

    @lazyproperty
    def _label_height(self):
        y_min, y_max = self._default_yrange
        return y_min + 0.6 * (y_max - y_min)

    def _plot(self):
        self._spec_1d.plot(self._hdu[1]['wave'], self._hdu[1]['flux'], pen='k')
        self._spec_1d.plot(self._hdu[1]['wave'], self._hdu[1]['err'], pen='r')

        for line_name, line_artist in self._line_artists.items():
            self._spec_1d.addItem(line_artist['line'], ignoreBounds=True)
            self._spec_1d.addItem(line_artist['label'])

        self._spec_1d.setLabel('bottom', self._hdu[0]['TUNIT1'], **self._label_style)
        self._spec_1d.setLabel('left', self._hdu[0]['TUNIT2'], **self._label_style)

    def _update_view(self):
        for line_name, line_artist in self._line_artists.items():
            line_wave = self._lines['lambda'][line_name] * (1 + self._z_slider.value)
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(line_wave, self._label_height)

    def _update_from_slider(self, index=None):
        if index is not None:
            self._z_slider.index = index
        self._redshift_editor.setText("{:.6f}".format(self._z_slider.value))
        self._update_view()

    def _update_from_editor(self):
        try:
            self._z_slider.index = self._z_slider.index_from_value(float(self._redshift_editor.text()))
        except ValueError:
            self._z_slider.reset()

        self._update_from_slider()

    def reset_view(self):
        if self._hdu is None:
            return

        self._z_slider.reset()
        self._update_from_slider()

        self._spec_1d.setXRange(*self._default_xrange)
        self._spec_1d.setYRange(*self._default_yrange)

    def load_object(self, j):
        del self._filename
        del self._hdu
        del self._default_xrange
        del self._default_yrange
        del self._label_height

        self._j = j

        self._spec_1d.clear()
        if self._hdu is not None:
            self.setEnabled(True)

            self._label.setText("1D spectrum: {}".format(self._filename.name))
            if 'z' in self._cat.colnames:
                self._z_slider.default_index = self._z_slider.index_from_value(self._cat['z'][self._j])
            elif self._config['slider'].get('default_value'):
                self._z_slider.default_index = self._z_slider.index_from_value(self._config['slider'].get('default_value'))

            self._plot()
            self.reset_view()
        else:
            self._label.setText("")
            self._redshift_editor.setText("")

            self.setEnabled(False)

    def load_project(self, cat):
        self._cat = cat
