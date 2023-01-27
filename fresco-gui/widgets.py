import pathlib

import numpy as np
from astropy.io import fits
from astropy import wcs

from PyQt5.QtWidgets import QWidget
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore


from colormaps_fresco import viridis_simple as viridis
import colormaps as cmaps
import colors as cl


class MySlider(QtGui.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=0, **kwargs):
        super().__init__(*args, **kwargs)

        self.min = min_value
        self.max = max_value
        self.step = step
        self.default = default_value

        self.setRange(0, self.n)
        self.setSingleStep(1)

        self.index = default_value

    @property
    def n(self):
        return int((self.max - self.min) / self.step)

    @property
    def arr(self):
        return np.linspace(self.min, self.max, self.n + 1)

    @property
    def value(self):
        return self.arr[self.index]


class ImageCutout(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
        grid = QtGui.QGridLayout()

        # add a label
        grid.addWidget(QtGui.QLabel('Image: {}'.format(self._filename.name)), 1, 1, 1, 1)

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
        self._image_widget.setMinimumSize(*map(int, self.parent.config['gui']['image_cutout']['size']))
        self._image_widget.setMaximumSize(*map(int, self.parent.config['gui']['image_cutout']['size']))  # freeze the size
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
        return pathlib.Path(self.parent.config['data']['grizli_fit_products']) /\
            '{}_{:05d}.beams.fits'.format(self.parent.config['data']['prefix'], self.parent.id)

    @property
    def _data(self):
        # TODO: get data from other grism exposures?
        data = fits.getdata(self._filename)
        data_band_flipped = np.rot90(np.fliplr(data))

        return data_band_flipped

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
            line_edit.setText(str(self.parent.config['gui']['image_cutout']['cuts'][i]))

    def _reset_image_levels(self):
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

        self._reset_image_levels()

    def reset_view(self):
        self._reset_cuts()
        self._reset_image_levels()
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


class Spec2D(QWidget):
    def __init__(self):
        super().__init__()
        grid = QtGui.QGridLayout()

        # add a slider for changing the cuts in the 2D spectrum
        self.slider = MySlider(self.parent.config['gui']['spec_2D']['slider'], QtCore.Qt.Vertical)
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


class Spec1D(QWidget):
    def __init__(self):
        super().__init__()
        grid = QtGui.QGridLayout()

        self.spec = pg.GraphicsLayoutWidget(self)
        self.spec.setMinimumSize(*map(int, self.config['gui']['spec_1D']['size']))
        grid.addWidget(self.spec, 12, 2, 4, 8)

        # add a redshift slider
        self.redshift_slider = MySlider(self.config['gui']['spec_1D']['slider'], QtCore.Qt.Horizontal)
        self.redshift_slider.valueChanged[int].connect(self.changeValue_sld_redshift)
        self.redshift_slider.setToolTip('Slide to redshift.')
        grid.addWidget(self.redshift_slider, 18, 1, 1, 8)

        # add a line edit for changing the redshift
        self.editors['redshift'] = QtGui.QLineEdit(self)
        grid.addWidget(QtGui.QLabel('z = ', self), 18, 10, 1, 1)
        grid.addWidget(self.editors['redshift'], 18, 11, 1, 1)

    def plot(self):
        self.spec.clear()
        pfs = self.spec.addPlot()
        zline = pg.InfiniteLine(angle=0, movable=False, pen=(50, 100, 100))

        spec1 = pathlib.Path(self.config['data']['grizli_fit_products']) / "gds-grizli-v5.1_{:05d}.1D.fits".format(
            self.id)
        infos_dict_spec, header = self.read_redshift(spec1)

        lines_Pen2 = pg.mkPen(color='r', width=4, alpha=0.7)
        pfs.plot(infos_dict_spec['wave'], infos_dict_spec['flux'], pen='k')
        pfs.plot(infos_dict_spec['wave'], infos_dict_spec['error'], pen='r')
        pfs.addItem(zline, ignoreBounds=True)
        # pfs.setYRange(-yrange[0]/4., yrange[0]*(3./4.))
        pfs.setYRange(-0.08, 0.18)
        pfs.setXRange(infos_dict_spec['wave'][0], infos_dict_spec['wave'][-1])

        wave_unit = header['TUNIT1']
        flux_unit = header['TUNIT2']
        styles = {'color': 'r', 'font-size': '20px'}
        pfs.setLabel('bottom', wave_unit, **styles)
        pfs.setLabel('left', flux_unit, **styles)

        # lines for all other lines
        c_otherlines = np.asarray(cl.viridis_more[9]) * 255
        lines_Pen = pg.mkPen(color=c_otherlines, width=1)
        for j in self.lines['lambda']:
            vLines_all = pg.InfiniteLine(angle=90, movable=False,
                                         pen=lines_Pen)
            line_pos = self.lines['lambda'][j] * (1 + self.redshift_slider.value)
            vLines_all.setPos(line_pos)
            pfs.addItem(vLines_all, ignoreBounds=True)
            line_name_text = j
            annotate2 = pg.TextItem(text=line_name_text, color=c_otherlines,
                                    anchor=(1, 1), angle=-90)
            annotate2.setPos(line_pos, 0.1)
            pfs.addItem(annotate2)

    @staticmethod
    def read_redshift(infile):
        hdu = fits.open(infile)
        header = hdu[1].header
        data = hdu[1]._data
        hdu.close()

        wave = np.asarray([i[0] for i in data])
        flux = np.asarray([i[1] for i in data])
        error = np.asarray([i[2] for i in data])

        infos_dict = {'wave': wave,
                      'flux': flux,
                      'error': error}

        return infos_dict, header