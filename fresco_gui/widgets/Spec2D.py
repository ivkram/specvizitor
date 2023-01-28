import pathlib

import numpy as np
import pyqtgraph as pg
from astropy.io import fits
from astropy.visualization import ZScaleInterval

from pyqtgraph.Qt import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem


class Spec2D(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self._parent = parent

        grid = QtWidgets.QGridLayout()

        # add a label
        grid.addWidget(QtWidgets.QLabel('2D spectrum: {}'.format(self._filename.name)), 1, 1)

        # add a widget for the spectrum
        self._spec_2d_widget = pg.GraphicsLayoutWidget()
        self._spec_2d_widget.setMinimumSize(*map(int, self._parent.config['gui']['spec_2D']['min_size']))
        grid.addWidget(self._spec_2d_widget, 2, 1)

        self.setLayout(grid)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self._spec_2d = pg.ImageItem(border='k')
        self._spec_2d.setLookupTable(self._cmap.getLookupTable())
        self._view_box = self._spec_2d_widget.addViewBox(0, 0)
        self._view_box.setAspectLocked(True)
        self._view_box.addItem(self._spec_2d)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self._spec_2d, showHistogram=True, histHeightPercentile=99.0)
        self._spec_2d_widget.addItem(self._cbar, 0, 1)

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

    def reset_view(self):
        # TODO: allow to choose between min/max and zscale?
        self._cbar.setLevels(ZScaleInterval().get_limits(self._data))
        self._view_box.autoRange()

    def load(self):
        self._spec_2d.setImage(self._data)
        self.reset_view()
