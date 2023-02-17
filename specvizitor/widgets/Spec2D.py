import logging

import numpy as np
import pyqtgraph as pg
from astropy.visualization import ZScaleInterval
from astropy.utils.decorators import lazyproperty

from qtpy import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem

from .ViewerElement import ViewerElement
from ..runtime.appdata import AppData


logger = logging.getLogger(__name__)


class Spec2D(ViewerElement):
    def __init__(self, rd: AppData, parent=None):
        self.cfg = rd.config.viewer.spec_2d
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        # add a label
        self._label = QtWidgets.QLabel()

        # add a widget for the spectrum
        self._spec_2d_widget = pg.GraphicsLayoutWidget()

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self._spec_2d_plot = self._spec_2d_widget.addPlot(name=self.cfg.title)

        self._spec_2d = pg.ImageItem(border='k')
        self._spec_2d.setLookupTable(self._cmap.getLookupTable())
        self._spec_2d_plot.addItem(self._spec_2d)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self._spec_2d, showHistogram=True, histHeightPercentile=99.0)
        self._spec_2d_widget.addItem(self._cbar, 0, 1)

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self._label, 1, 1)
        self.layout.addWidget(self._spec_2d_widget, 2, 1)

    def reset_view(self):
        if self._data is None:
            return

        # TODO: allow to choose between min/max and zscale?
        self._cbar.setLevels(ZScaleInterval().get_limits(self._data))

        self._spec_2d_plot.autoRange()

    def load_object(self):
        super().load_object()

        if self._data is not None:
            self.setEnabled(True)

            self._label.setText("{}: {}".format(self.cfg.title, self._filename.name))
            self._spec_2d.setImage(self._data)

            self.reset_view()
        else:
            self._label.setText("")
            self._spec_2d.clear()

            self.setEnabled(False)
