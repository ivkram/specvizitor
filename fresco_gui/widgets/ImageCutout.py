import pathlib

import numpy as np
from astropy import wcs
from astropy.io import fits

from PyQt5.QtWidgets import QWidget
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

from .colormaps_fresco import viridis_simple as viridis


class ImageCutout(QWidget):
    def __init__(self, parent):
        super().__init__()
        self._parent = parent

        grid = QtGui.QGridLayout()

        # add a label
        grid.addWidget(QtGui.QLabel('Image: {}'.format(self._filename.name)), 1, 1, 1, 4)

        # add two line edits for changing the min and the max cuts
        self._edits = [QtGui.QLineEdit(), QtGui.QLineEdit()]
        for line_edit in self._edits:
            line_edit.returnPressed.connect(self._update_view)

        grid.addWidget(QtGui.QLabel('Cut min'), 2, 1, 1, 1)
        grid.addWidget(QtGui.QLabel('Cut max'), 2, 3, 1, 1)
        grid.addWidget(self._edits[0], 2, 2, 1, 1)
        grid.addWidget(self._edits[1], 2, 4, 1, 1)

        # add a widget for the image
        self._image_widget = pg.GraphicsLayoutWidget()
        self._image_widget.setMinimumSize(*map(int, self._parent.config['gui']['image_cutout']['size']))
        # self._image_widget.setMaximumSize(*map(int, self._parent.config['gui']['image_cutout']['size']))
        grid.addWidget(self._image_widget, 3, 1, 1, 4)

        self.setLayout(grid)

        # set up the image
        self._image = pg.ImageItem(border='k')
        self._image.setLookupTable(viridis)

        self._view_box = self._image_widget.addViewBox()
        self._view_box.addItem(self._image)
        self._view_box.setAspectLocked(True)

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
        data_flipped = np.rot90(np.fliplr(data))

        return data_flipped

    @property
    def _cuts(self):
        return self._edits[0].text(), self._edits[1].text()

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

    def _reset_cuts(self):
        for i, line_edit in enumerate(self._edits):
            line_edit.setText(str(self._parent.config['gui']['image_cutout']['cuts'][i]))

    def _update_levels(self):
        p1, p2 = map(float, self._cuts)
        self._image.setLevels([np.percentile(self._data, p1), np.percentile(self._data, p2)])

    def _update_view(self):
        try:
            p1, p2 = map(float, self._cuts)
        except ValueError:
            self._reset_cuts()
        else:
            if not (0 <= float(p1) < float(p2) <= 100):
                self._reset_cuts()

        self._update_levels()

    def reset_view(self):
        self._reset_cuts()
        self._update_levels()
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
