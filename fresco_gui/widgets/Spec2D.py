import pathlib

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget
from astropy.io import fits
from pyqtgraph.Qt import QtGui, QtCore

from ..utils import CustomSlider
from . import colormaps as cmaps


class Spec2D(QWidget):
    def __init__(self, parent):
        super().__init__()
        self._parent = parent

        grid = QtGui.QGridLayout()

        # add a slider for changing the cuts in the 2D spectrum
        self._slider = CustomSlider(QtCore.Qt.Vertical, **self._parent.config['gui']['spec_2D']['slider'])
        self._slider.valueChanged[int].connect(self._update_view)
        self._slider.setToolTip('Slide to change cuts.')
        grid.addWidget(self._slider, 1, 1, 1, 1)

        # add a widget for the spectrum
        self._spec_2d_widget = pg.GraphicsLayoutWidget()
        self._spec_2d_widget.setMinimumSize(*map(int, self._parent.config['gui']['spec_2D']['size']))
        grid.addWidget(self._spec_2d_widget, 1, 2, 1, 1)

        self.setLayout(grid)

        # set up the image
        self._spec_2d = pg.ImageItem(border='k')
        self._spec_2d.setImage(self._data)

        self._view_box = self._spec_2d_widget.addViewBox()
        self._view_box.addItem(self._spec_2d)
        self._view_box.setAspectLocked(True)

        # load the data and plot the spectrum
        self.load()

    @property
    def _filename(self):
        return pathlib.Path(self._parent.config['data']['grizli_fit_products']) / \
            '{}_{:05d}.stack.fits'.format(self._parent.config['data']['prefix'], self._parent.id)

    @property
    def _data(self):
        data = fits.getdata(self._filename)
        return np.rot90(data)[::-1]

    def _reset_slider(self):
        self._slider.index = self._slider.default_index
        self._slider.setValue(self._slider.index)

    def _reset_lookup_table(self):
        viridis_lookuptable = np.asarray([np.asarray(cmaps.viridis(k)) * 255 for k in range(int(self._slider.value))])
        self._spec_2d.setLookupTable(viridis_lookuptable)

    def _update_view(self, index):
        self._slider.index = index
        self._reset_lookup_table()

    def reset_view(self):
        self._reset_slider()
        self._reset_lookup_table()
        self._view_box.autoRange()

    def load(self):
        self._spec_2d.setImage(self._data)
        self.reset_view()
