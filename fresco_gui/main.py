import sys
import logging
from functools import partial

import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy import wcs
from astropy.coordinates import Angle
from astropy import units as u
from astropy.coordinates import SkyCoord

from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton)
from PyQt5.QtCore import pyqtSignal
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

from .utils.config import read_yaml
from .loader import load_phot_cat
from .widgets import ImageCutout, Spec2D, Spec1D


pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def pix_scale(header):
    """
    Prints out averaged pixel scale in arcseconds at reference pixel.
    Ignores dissortions, but this OK considering our small field of view.

    In:
    ---
    header ... an astropy.io.fits header object

    Out:
    ---
    pix_scale ... average linear extent of a pixel in arc-seconds
    """

    wcs_obj = wcs.WCS(header, relax=False)
    scale_deg_xy = wcs.utils.proj_plane_pixel_scales(wcs_obj)
    scale_deg = np.sum(scale_deg_xy[:2]) / 2.

    scale_deg = Angle(scale_deg,unit=u.deg)
    scale_asec = scale_deg.arcsec

    return scale_asec


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()

        # size, title and logo
        self.setGeometry(600, 500, 2550, 1450)  # position and size of the window
        self.setWindowTitle('FRESCO')  # title of the window
        self.setWindowIcon(QtGui.QIcon('logo2_2.png'))  # logo in upper left corner
        self.show()

        # status bar
        self.statusBar().showMessage("Message in statusbar.")

        self.main_GUI = FRESCO()
        # self.main_GUI.signal1.connect(self.show_status)
        self.setCentralWidget(self.main_GUI)


class FRESCO(QWidget):
    objectChanged = pyqtSignal()
    idClicked = pyqtSignal()

    def __init__(self):
        # load the configuration file
        self.config = read_yaml('config.yml')

        # load the photometric catalogue
        muse_fresco_cat = Table(fits.getdata(self.config['data']['MUSE_LAEs']))
        ids = muse_fresco_cat['id']
        self.cat = load_phot_cat(ids=ids, **self.config)

        if not self.cat:
            logging.error("The input catalogue is empty!")

        # initialise the widget
        super().__init__()

        # set up the widget layout
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        # initialise the index of the current object
        self.j = 0

        # add a widget for the image cutout
        self.image_cutout = ImageCutout(self)
        grid.addWidget(self.image_cutout, 1, 1, 6, 1)

        # add a widget for the 2D spectrum
        self.spec_2D = Spec2D(self)
        grid.addWidget(self.spec_2D, 7, 1, 1, 2)

        # add a widget for the 1D spectrum
        self.spec_1D = Spec1D(self)
        grid.addWidget(self.spec_1D, 9, 1, 1, 2)

        # add a reset button
        self.reset_button = QPushButton()
        self.reset_button.setToolTip('Reset view')
        self.reset_button.clicked.connect(self.idClicked.emit)
        grid.addWidget(self.reset_button, 1, 3, 1, 2)

        # add a widget displaying the index of the current object and the total number of objects in the catalogue
        self.number_of_obj_label = QtGui.QLabel()
        grid.addWidget(self.number_of_obj_label, 1, 5, 1, 1)

        # TODO: add a close button
        # close_button = QPushButton('Close')
        # close_button.clicked.connect(self.close_prog)
        # close_button.setToolTip('Close the program.')
        # grid.addWidget(close_button, 1,31,1,1)

        # set buttons for next or previous object
        np_buttons = {'previous': {'shortcut': 'left', 'layout': (2, 3, 1, 2)},
                      'next': {'shortcut': 'right', 'layout': (2, 5, 1, 2)}}

        for np_text, np_properties in np_buttons.items():
            b = QtGui.QPushButton('', self)
            b.setIcon(QtGui.QIcon(np_text + '.png'))
            b.setToolTip('Look at the {} object.'.format(np_text))
            b.setText(np_text)
            b.clicked.connect(partial(self.change_object, np_text))
            b.setShortcut(np_properties['shortcut'])
            grid.addWidget(b, *np_properties['layout'])

        # display RA
        self.ra_label = QtGui.QLabel()
        grid.addWidget(self.ra_label, 3, 3, 1, 4)

        # display Dec
        self.dec_label = QtGui.QLabel()
        grid.addWidget(self.dec_label, 4, 3, 1, 4)

        # add a multi-line text editor for writing comments
        self.comments = QtGui.QTextEdit(self)
        grid.addWidget(QtGui.QLabel('Comments:', self), 5, 3, 1, 4)
        grid.addWidget(self.comments, 6, 3, 1, 4)

        ### eazy results
        self.eazy_fig_widget = pg.GraphicsLayoutWidget(self)
        self.eazy_z_widget = pg.GraphicsLayoutWidget(self)
        grid.addWidget(self.eazy_fig_widget, 7, 3, 2, 4)
        grid.addWidget(self.eazy_z_widget, 9, 3, 2, 4)
        # self.show_eazy_fig()

        ### Write eazy results

        '''
        z_raw_chi2 = np.round(self.zout['z_raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtGui.QLabel('Chi2: '+str(z_raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,7,31,1,1)

        raw_chi2 = np.round(self.zout['raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtGui.QLabel('Chi2: '+str(raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,8,31,1,1)
        '''

        # self.z_phot_chi2 = np.round(self.zout['z_phot_chi2'][self.j], 3)
        # eazy_raw_chi2 = QtGui.QLabel('Chi2: ' + str(self.z_phot_chi2), self)
        # grid.addWidget(eazy_raw_chi2, 9, 31, 1, 1)
        #
        # self.sfr = np.round(self.zout['sfr'][self.j], 3)
        # eazy_sfr = QtGui.QLabel('SFR: ' + str(self.sfr), self)
        # grid.addWidget(eazy_sfr, 10, 31, 1, 1)
        #
        # self.mass = np.round(self.zout['mass'][self.j] / 10 ** 9, 3)
        # eazy_mass = QtGui.QLabel('mass: ' + str(self.mass), self)
        # grid.addWidget(eazy_mass, 11, 31, 1, 1)

        self.show_info()

        self.objectChanged.connect(self.image_cutout.load)
        self.objectChanged.connect(self.spec_2D.load)
        self.objectChanged.connect(self.spec_1D.load)

    @property
    def id(self):
        """
        @return: ID of the current object.
        """
        return self.cat['id'][self.j]

    #############################################################################
    # functions

    def show_info(self):
        self.reset_button.setText('ID {}'.format(self.id))
        self.number_of_obj_label.setText('(#{} of {} objects)'.format(self.j + 1, len(self.cat)))

        c = SkyCoord(ra=self.cat['ra'][self.j], dec=self.cat['dec'][self.j], frame='icrs', unit='deg')
        ra, dec = c.to_string('hmsdms').split(' ')
        self.ra_label.setText("RA: {}".format(ra))
        self.dec_label.setText("Dec: {}".format(dec))

    def change_object(self, command: str):
        if command == 'next':
            self.j += 1
        elif command == 'previous':
            self.j -= 1
        else:
            return

        self.j = self.j % len(self.cat)

        self.objectChanged.emit()

        self.show_info()
        self.comments.clear()

    def close_prog(self):
        # TODO: save catalogue!
        logging.info('Well done! :)')
        # self.close()

    def save_now(self):
        self.cat['SFR'][self.j] = 0  # self.sfr
        self.cat['mass'][self.j] = 0  # self.mass
        self.cat['chi2'][self.j] = 0  # self.z_phot_chi2
        # write_output(input_cat, comments, 'test.fits')


def main():

    # for key in ('SFR', 'mass', 'chi2'):
    #     input_cat.add_column(-99., name=key)

    # initiate lists and variables
    # comments = np.asarray(['-' for i in range(len(ID))])
    # # This makes sure that if the comments were restricted to some length before,
    # # this restriction is now lifted
    # lines_comment_new = ['-' for a in comments]
    # lines_comment_new[:] = comments
    # comments = lines_comment_new

    width_window = [8.]  # width of the thumbnail cut-out windows in arcsec

    # set colours
    c_data_crossline = 'r'

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
