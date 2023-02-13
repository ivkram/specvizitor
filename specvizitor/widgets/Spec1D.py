import logging
from dataclasses import asdict

import numpy as np
from astropy.io import fits
from astropy.utils.decorators import lazyproperty

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from ..utils.params import read_yaml
from ..utils import SmartSlider

from .ViewerElement import ViewerElement
from ..runtime import RuntimeData


logger = logging.getLogger(__name__)


class Spec1D(ViewerElement):
    def __init__(self, rd: RuntimeData, parent=None):
        self.cfg = rd.config.viewer.spec_1d
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        # load the list of spectral lines
        # TODO: move to the runtime data
        self._lines = read_yaml('default_lines.yml', in_dist=True)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)

        # add a label
        self._label = QtWidgets.QLabel()
        grid.addWidget(self._label, 1, 1)

        # add a widget for the spectrum
        self._spec_1d_widget = pg.GraphicsLayoutWidget()
        grid.addWidget(self._spec_1d_widget, 2, 1, 1, 3)

        # add a redshift slider
        self._z_slider = SmartSlider(QtCore.Qt.Horizontal, **asdict(self.cfg.slider))
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
        # TODO: store colors in config
        line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)
        for line_name, lambda0 in self._lines['lambda'].items():
            line = pg.InfiniteLine(angle=90, movable=False, pen=line_pen)
            label = pg.TextItem(text=line_name, color=line_color, anchor=(1, 1), angle=-90)

            self._line_artists[line_name] = {'line': line, 'label': label}

    @lazyproperty
    def _hdu(self):
        try:
            with fits.open(self._filename) as hdul:
                header, data = hdul[1].header, hdul[1].data
        except ValueError:
            logger.warning('1D spectrum not found (object ID: {})'.format(self.rd.id))
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
            logger.error('Invalid redshift value: {}'.format(self._redshift_editor.text()))
            self._z_slider.reset()

        self._update_from_slider()

    def reset_view(self):
        if self._hdu is None:
            return

        self._z_slider.reset()
        self._update_from_slider()

        self._spec_1d.setXRange(*self._default_xrange)
        self._spec_1d.setYRange(*self._default_yrange)

    def load_object(self):
        super().load_object()

        del self._hdu
        del self._default_xrange
        del self._default_yrange
        del self._label_height

        self._spec_1d.clear()
        if self._hdu is not None:
            self.setEnabled(True)

            self._label.setText("1D spectrum: {}".format(self._filename.name))

            if 'z' in self.rd.cat.colnames:
                self._z_slider.default_value = self.rd.cat['z'][self.rd.j]
            else:
                self._z_slider.default_value = self.cfg.slider.default_value

            self._plot()
            self.reset_view()
        else:
            self._label.setText("")
            self._redshift_editor.setText("")

            self.setEnabled(False)
