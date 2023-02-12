import logging

from astropy import wcs
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from astropy.utils.decorators import lazyproperty

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem

from .ViewerElement import ViewerElement
from ..runtime import RuntimeData


logger = logging.getLogger(__name__)


class ImageCutout(ViewerElement):
    def __init__(self, rd: RuntimeData, parent=None):
        self.cfg = rd.config.viewer.image_cutout
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        # TODO: introduce a class attribute `grid` and move it to ViewerElement?
        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)

        # add a label
        self._label = QtWidgets.QLabel()
        grid.addWidget(self._label, 1, 1)

        # add a widget for the image
        self._image_widget = pg.GraphicsLayoutWidget()
        grid.addWidget(self._image_widget, 2, 1)

        self.setLayout(grid)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self._image = pg.ImageItem(border='k')
        self._image.setLookupTable(self._cmap.getLookupTable())
        self._view_box = self._image_widget.addViewBox(0, 0)
        self._view_box.addItem(self._image)
        self._view_box.setAspectLocked(True)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self._image, showHistogram=True)
        self._image_widget.addItem(self._cbar, 0, 1)

    @lazyproperty
    def _data(self):
        try:
            data = fits.getdata(self._filename)
            data = data * 1e21
        except ValueError:
            logger.warning('Image cutout not found (object ID: {})'.format(self.rd.id))
            return
        else:
            return data

    def reset_view(self):
        if self._data is None:
            return

        self._cbar.setLevels(ZScaleInterval().get_limits(self._data))
        self._view_box.autoRange()

    def load_object(self):
        super().load_object()

        del self._data

        if self._data is not None:
            self.setEnabled(True)

            self._label.setText("Image: {}".format(self._filename.name))
            self._image.setImage(self._data)

            self.reset_view()
        else:
            self._label.setText("")
            self._image.clear()
            self.setEnabled(False)

    @staticmethod
    def radec_to_pix(ra_coords, dec_coords, header, origin=0):
        """
        Converts RA & DEC world coordinates to pixel coordinates.

        In:
        ---
        ra_coords ... 1D array of RA in degrees (float)
        dec_coords ... 1D array of corresponding DEC in degrees (float)
        header ... an astropy.io.fits header object
        origin ... output coordinates 0-indexed if 0, or 1-indexed if 1
                   (default: 0)

        Out:
        ---
        x_coords, y_coords ... 2-tuple of 1D arrays with pixel coordinates
        """

        wcs_obj = wcs.WCS(header, relax=False)  # no HST only spec
        # allowed, only WCS
        # standard
        coords = wcs_obj.wcs_world2pix(ra_coords, dec_coords, origin)
        x_coords = coords[0]
        y_coords = coords[1]
        return x_coords, y_coords

    def plot(self):
        # width_window_pix = width_window[0] / band_ps
        # self.view_cutout.setRange(QtCore.QRectF(x_band-width_window_pix/2.,
        #                                     y_band-width_window_pix/2.,
        #                                     width_window_pix,
        #                                     width_window_pix))


        ### TODO: position of lines seems shifted and doesn't match with catalogue

        # test_line = pg.InfiniteLine(angle=90,movable=False,
        #                            pen=pg.mkPen(color=c_data_crossline, width = 1))
        # test_line.setPos([x_band,0])
        # test_line2 = pg.InfiniteLine(angle=0,movable=False,
        #                             pen=pg.mkPen(color=c_data_crossline, width = 1))
        # test_line2.setPos([0,y_band])
        # self.view_cutout.addItem(test_line)
        # self.view_cutout.addItem(test_line2)
        return
