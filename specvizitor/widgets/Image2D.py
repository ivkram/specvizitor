import logging

import numpy as np
import pyqtgraph as pg
from astropy.visualization import ZScaleInterval
from astropy.utils.decorators import lazyproperty

from qtpy import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem

from .ViewerElement import ViewerElement
from ..runtime.appdata import AppData
from ..runtime import config


logger = logging.getLogger(__name__)


class Image2D(ViewerElement):
    def __init__(self, rd: AppData, cfg: config.Image, name: str, parent=None):
        super().__init__(rd=rd, cfg=cfg, name=name, parent=parent)

        self.cfg = cfg
        self.name = name

        # add a label
        self._label = QtWidgets.QLabel()

        # add a widget for the spectrum
        self._image_2d_widget = pg.GraphicsLayoutWidget()

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self.image_2d_plot = self._image_2d_widget.addPlot(name=name)

        self.image_2d = pg.ImageItem(border='k')
        self.image_2d.setLookupTable(self._cmap.getLookupTable())
        self.image_2d_plot.addItem(self.image_2d)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self.image_2d, showHistogram=True, histHeightPercentile=99.0)
        self._image_2d_widget.addItem(self._cbar, 0, 1)

        # lock the aspect ratio
        self.image_2d_plot.setAspectLocked(True)

    def init_ui(self):
        # self.layout.addWidget(self._label, 1, 1)
        self.layout.addWidget(self._image_2d_widget, 2, 1)

    @lazyproperty
    def data(self):
        data = super().data
        if data is None:
            return

        # rotate the image
        if self.cfg.rotate is not None:
            data = np.rot90(data, k=self.cfg.rotate // 90)

        # scale the data points
        if self.cfg.scale is not None:
            data *= self.cfg.scale

        return data

    def reset_view(self):
        if self.data is None:
            return

        # TODO: allow to choose between min/max and zscale?
        self._cbar.setLevels(ZScaleInterval().get_limits(self.data))

        self.image_2d_plot.autoRange()

    def load_object(self):
        super().load_object()

        if self.data is not None:
            self.setEnabled(True)

            self._label.setText("{}: {}".format(self.name, self.filename.name))
            self.image_2d.setImage(self.data)

            self.reset_view()
        else:
            self._label.setText("")
            self.image_2d.clear()

            self.setEnabled(False)
