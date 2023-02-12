import logging

import numpy as np
import pyqtgraph as pg
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from astropy.utils.decorators import lazyproperty

from pyqtgraph.Qt import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem

from .ViewerElement import ViewerElement
from ..runtime import RuntimeData


logger = logging.getLogger(__name__)


class Spec2D(ViewerElement):
    def __init__(self, rd: RuntimeData, parent=None):
        self.cfg = rd.config.viewer.spec_2d
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)

        # add a label
        self._label = QtWidgets.QLabel()
        grid.addWidget(self._label, 1, 1)

        # add a widget for the spectrum
        self._spec_2d_widget = pg.GraphicsLayoutWidget()
        grid.addWidget(self._spec_2d_widget, 2, 1)

        self.setLayout(grid)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self._spec_2d = pg.ImageItem(border='k')
        self._spec_2d.setLookupTable(self._cmap.getLookupTable())
        self._view_box = self._spec_2d_widget.addViewBox(0, 0)
        self._view_box.addItem(self._spec_2d)
        self._view_box.setAspectLocked(True)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self._spec_2d, showHistogram=True, histHeightPercentile=99.0)
        self._spec_2d_widget.addItem(self._cbar, 0, 1)

    @lazyproperty
    def _data(self):
        try:
            data = fits.getdata(self._filename)
            data = np.rot90(data)[::-1]
        except ValueError:
            logger.warning('2D spectrum not found (object ID: {})'.format(self.rd.id))
            return
        else:
            return data

    def reset_view(self):
        if self._data is None:
            return

        # TODO: allow to choose between min/max and zscale?
        self._cbar.setLevels(ZScaleInterval().get_limits(self._data))
        self._view_box.autoRange()

    def load_object(self):
        super().load_object()

        del self._data

        if self._data is not None:
            self.setEnabled(True)

            self._label.setText("2D spectrum: {}".format(self._filename.name))
            self._spec_2d.setImage(self._data)

            self.reset_view()
        else:
            self._label.setText("")
            self._spec_2d.clear()

            self.setEnabled(False)
