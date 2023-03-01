import logging
from dataclasses import asdict

import numpy as np
from astropy.utils.decorators import lazyproperty

import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from ..utils.params import read_yaml
from ..utils import SmartSlider

from .ViewerElement import ViewerElement
from ..runtime.appdata import AppData
from ..runtime import config


logger = logging.getLogger(__name__)


class Spec1D(ViewerElement):
    def __init__(self, rd: AppData, cfg: config.Spectrum, name: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, name=name, parent=parent)

        self.cfg = cfg
        self.name = name

        # load the list of spectral lines
        # TODO: move to the application data
        self._lines = read_yaml('default_lines.yml', in_dist=True)

        # create a label
        self._label = QtWidgets.QLabel()

        # create a widget for the spectrum
        self._spec_1d_widget = pg.GraphicsLayoutWidget()

        # create a redshift slider
        self._z_slider = SmartSlider(QtCore.Qt.Horizontal, **asdict(self.cfg.slider))
        self._z_slider.valueChanged[int].connect(self._update_from_slider)
        self._z_slider.setToolTip('Slide to redshift.')

        # create a line edit for changing the redshift
        self._redshift_editor = QtWidgets.QLineEdit()
        self._redshift_editor.returnPressed.connect(self._update_from_editor)
        self._redshift_editor.setMaximumWidth(120)

        # set up the plot
        self._spec_1d = self._spec_1d_widget.addPlot(name=self.name)
        self._spec_1d.setMouseEnabled(True, True)
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

    def init_ui(self):
        # self.layout.addWidget(self._label, 1, 1)
        self.layout.addWidget(self._spec_1d_widget, 2, 1, 1, 3)
        self.layout.addWidget(self._z_slider, 3, 1, 1, 1)
        self.layout.addWidget(QtWidgets.QLabel('z = ', self), 3, 2, 1, 1)
        self.layout.addWidget(self._redshift_editor, 3, 3, 1, 1)

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

    def _plot(self):
        self._spec_1d.plot(self.data['wavelength'], self.data['flux'], pen='k')

        if 'flux_error' in self.data.colnames:
            self._spec_1d.plot(self.data['wavelength'], self.data['flux_error'], pen='r')

        for line_name, line_artist in self._line_artists.items():
            self._spec_1d.addItem(line_artist['line'], ignoreBounds=True)
            self._spec_1d.addItem(line_artist['label'])

        for keyword, position in {'TUNIT1': 'bottom', 'TUNIT2': 'right'}.items():
            if self.hdu.header.get(keyword):
                self._spec_1d.setLabel(position, self.hdu.header[keyword], **self._label_style)

    def _update_view(self):
        for line_name, line_artist in self._line_artists.items():
            line_wave = self._lines['lambda'][line_name] * (1 + self._z_slider.value)
            line_artist['line'].setPos(line_wave)
            line_artist['label'].setPos(QtCore.QPointF(line_wave, self._label_height))

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
        if self.data is None:
            return

        self._z_slider.reset()
        self._update_from_slider()

        self._spec_1d.setXRange(*self.default_xrange)
        self._spec_1d.setYRange(*self.default_yrange)

    def load_object(self):
        super().load_object()

        del self.default_xrange
        del self.default_yrange
        del self._label_height

        self._spec_1d.clear()
        if self.data is not None:
            self.setEnabled(True)

            self._label.setText("{}: {}".format(self.name, self.filename.name))

            try:
                self._z_slider.default_value = self.rd.cat.loc[self.rd.id]['z']
            except KeyError:
                self._z_slider.default_value = self.cfg.slider.default_value

            self._plot()
            self.reset_view()
        else:
            self._label.setText("")
            self._redshift_editor.setText("")

            self.setEnabled(False)
