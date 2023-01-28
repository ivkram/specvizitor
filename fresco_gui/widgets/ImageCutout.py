import pathlib

from astropy import wcs
from astropy.io import fits
from astropy.visualization import ZScaleInterval

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from pgcolorbar.colorlegend import ColorLegendItem


class ImageCutout(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()
        self._parent = parent

        grid = QtWidgets.QGridLayout()

        # add a label
        grid.addWidget(QtWidgets.QLabel('Image: {}'.format(self._filename.name)), 1, 1)

        # add a widget for the image
        self._image_widget = pg.GraphicsLayoutWidget()
        self._image_widget.setMinimumSize(*map(int, self._parent.config['gui']['image_cutout']['size']))
        # self._image_widget.setMaximumSize(*map(int, self._parent.config['gui']['image_cutout']['size']))
        grid.addWidget(self._image_widget, 2, 1)

        self.setLayout(grid)

        # set up the color map
        self._cmap = pg.colormap.get('viridis')

        # set up the image and the view box
        self._image = pg.ImageItem(border='k')
        self._image.setLookupTable(self._cmap.getLookupTable())
        self._view_box = self._image_widget.addViewBox(0, 0)
        self._view_box.setAspectLocked(True)
        self._view_box.addItem(self._image)

        # set up the color bar
        self._cbar = ColorLegendItem(imageItem=self._image, showHistogram=True)
        self._image_widget.addItem(self._cbar, 0, 1)

        # load the data and plot the image
        self.load()

    @property
    def _filename(self):
        return pathlib.Path(self._parent.config['data']['grizli_fit_products']) /\
            '{}_{:05d}.beams.fits'.format(self._parent.config['data']['prefix'], self._parent.id)

    @property
    def _data(self):
        # TODO: get data from other grism exposures?
        data = fits.getdata(self._filename)
        data = data * 1e21
        return data

    def reset_view(self):
        self._cbar.setLevels(ZScaleInterval().get_limits(self._data))
        self._view_box.autoRange()

    def load(self):
        self._image.setImage(self._data)
        self.reset_view()

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