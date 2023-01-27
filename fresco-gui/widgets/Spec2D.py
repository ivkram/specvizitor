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
        self.parent = parent

        grid = QtGui.QGridLayout()

        # add a slider for changing the cuts in the 2D spectrum
        self.slider = CustomSlider(self.parent.config['gui']['spec_2D']['slider'], QtCore.Qt.Vertical)
        self.slider.valueChanged[int].connect(self.change_cuts)
        self.slider.setToolTip('Slide to change cuts.')
        grid.addWidget(self.slider, 1, 1, 1, 1)

        # add a widget for the spectrum
        self.spec = pg.GraphicsLayoutWidget()
        self.spec.setMinimumSize(*map(int, self.config['gui']['spec_2D']['size']))
        grid.addWidget(self.spec, 1, 2, 1, 1)

    def plot(self):
        self.spec.clear()

        image_sci = fits.getdata(pathlib.Path(self.config['data']['grizli_fit_products']) / (
            'gds-grizli-v5.1_{:05d}.stack.fits'.format(self.id)))

        img_spec_2D = pg.ImageItem(border='k')
        viridis_lookuptable = np.asarray(
            [np.asarray(cmaps.viridis(k)) * 255 for k in range(int(self.slider.value))])
        img_spec_2D.setLookupTable(viridis_lookuptable)
        img_spec_2D.setImage(np.rot90(image_sci)[::-1])
        self.view_spec_2D = self.spec.addViewBox()
        self.view_spec_2D.addItem(img_spec_2D)
        self.view_spec_2D.setAspectLocked(True)

    def change_cuts(self, index):
        self.slider.index = index
        self.plot()
