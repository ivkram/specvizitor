import pathlib

import numpy as np
from astropy.io import fits

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtWidgets

from ..utils.config import read_yaml
from ..utils.CustomSlider import CustomSlider
from .colors import viridis_more


class Spec1D(QtWidgets.QWidget):
    def __init__(self, parent):
        # load the list of spectral lines
        self._lines = read_yaml('lines.yml')

        super().__init__()
        self._parent = parent

        grid = QtWidgets.QGridLayout()

        # add a label
        grid.addWidget(QtWidgets.QLabel('1D spectrum: {}'.format(self._filename.name)), 1, 1)

        # add a widget for the spectrum
        self._spec_1d_widget = pg.GraphicsLayoutWidget(self)
        self._spec_1d_widget.setMinimumSize(*map(int, self._parent.config['gui']['spec_1D']['min_size']))
        grid.addWidget(self._spec_1d_widget, 2, 1, 1, 3)

        # add a redshift slider
        self._redshift_slider = CustomSlider(QtCore.Qt.Horizontal, **self._parent.config['gui']['spec_1D']['slider'])
        self._redshift_slider.valueChanged[int].connect(self._update_from_slider)
        self._redshift_slider.setToolTip('Slide to redshift.')
        grid.addWidget(self._redshift_slider, 3, 1, 1, 1)

        # add a line edit for changing the redshift
        self._redshift_editor = QtWidgets.QLineEdit(self)
        self._redshift_editor.returnPressed.connect(self._update_from_editor)
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

        # load the data and plot the spectrum
        self.load()

    @property
    def _filename(self):
        return pathlib.Path(self._parent.config['data']['grizli_fit_products']) / \
            '{}_{:05d}.1D.fits'.format(self._parent.config['data']['prefix'], self._parent.id)

    @property
    def _hdu(self):
        with fits.open(self._filename) as hdul:
            header, data = hdul[1].header, hdul[1].data
        return header, data

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
            line_wave = self._lines['lambda'][line_name] * (1 + self._redshift_slider.value)
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(line_wave, 0.1)

    def _update_from_slider(self, index=None):
        if index:
            self._redshift_slider.index = index
        self._redshift_editor.setText("{:.4f}".format(self._redshift_slider.value))
        self._update_view()

    def _update_from_editor(self):
        try:
            self._redshift_slider.update_index(float(self._redshift_editor.text()))
        except ValueError:
            self._redshift_slider.reset()
            self._update_from_slider()
        else:
            self._redshift_editor.setText("{:.4f}".format(self._redshift_slider.value))
            self._update_view()

    def reset_view(self):
        self._redshift_slider.reset()
        self._update_from_slider()

        self._spec_1d.setXRange(self._hdu[1]['wave'][0], self._hdu[1]['wave'][-1])
        self._spec_1d.setYRange(np.min(self._hdu[1]['flux']), np.max(self._hdu[1]['flux']))

    def load(self):
        self._spec_1d.clear()
        self._plot()
        self.reset_view()
