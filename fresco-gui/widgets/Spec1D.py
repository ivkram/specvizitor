import pathlib

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget
from astropy.io import fits
from pyqtgraph.Qt import QtGui, QtCore


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
