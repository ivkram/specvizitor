import numpy as np
from astropy.io import fits
from astropy.table import Table

from PyQt5.QtWidgets import (QWidget, QPushButton)

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore


from config import read_default_params
from loader import load_phot_cat


import colormaps as cmaps
from colormaps_fresco import viridis_simple as viridis


pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# reading the configuration file
config = read_default_params()


class MainWindow(QtGui.QWindow):
    signal_j = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__(self)
        self.initUI()

    def initUI(self):
        self.j = j
        self.ID_here = ID[self.j]

        # status bar
        self.statusBar().showMessage("Message in statusbar.")

        if self.j == 0:
            self.main_GUI = FRESCO(self, self.j, self.statusBar())
            # self.main_GUI.signal1.connect(self.show_status)
            self.setCentralWidget(self.main_GUI)
            # self.statusBar().showMessage('')

        # size and logo
        self.setGeometry(600, 500, 2550, 1450)  # position and size of the window
        self.setWindowTitle('FRESCO')  # title of the window
        self.setWindowIcon(QtGui.QIcon('logo2_2.png'))  # logo in upper left corner
        self.show()

        self.main_GUI.signal_next_previous[str].connect(self.show_object)

    ####################################################################

    def show_object(self, text):  # Goes to next or previous object

        max_len = len(ID)

        ID_old = ID[self.j]

        if text == 'next':
            forward_back = 1
        elif text == 'previous':
            forward_back = -1
        else:
            forward_back = 0

        if self.j == max_len - 1:  # if the end of the lines is reached
            # stay at this ID (the last)
            ID_new = ID_old
            # if we are going back, it's fine, we go back
            if text == 'previous':
                ID_new = ID[self.j]
            # if we are going forward,go to first object
            if text == 'next':
                print('Went too far!')
                # self.went_through()
        elif self.j < max_len - 1 and self.j >= 0:
            ID_new = ID[self.j + forward_back]
        else:  # if you go back from the first object, to go the last
            ID_new = ID[0]

        self.j += forward_back

        if self.j < 0:
            self.j = max_len - 1
        if self.j >= max_len:
            self.went_through()

        self.main_GUI = FRESCO(self, self.j, self.statusBar())
        self.setCentralWidget(self.main_GUI)
        self.main_GUI.signal_next_previous[str].connect(self.show_object)
        self.signal_j.emit(self.j)
        # self.main_GUI.plot()
        # self.main_GUI.send_message()


### Main GUI

class FRESCO(QWidget):
    signal_next_previous = QtCore.pyqtSignal(str)

    # signal_previous = QtCore.pyqtSignal(str)

    def __init__(self, j, status):
        super().__init__()
        # self.setStyleSheet("background-color: black;")
        self.initUI(j, status)

    def initUI(self, j, status):

        ### initialise
        self.j = j
        self.status = status
        message = 'None'
        self.message = message
        self.z_slider = z_slider[0]

        ### general layout of the window
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        ### write ID as title and reset button
        self.ID_here = ID[self.j]
        reset_button = QPushButton('ID  ' + str(int(self.ID_here)))
        reset_button.clicked.connect(self.np_obj)
        reset_button.setToolTip('Reset plots')
        grid.addWidget(reset_button, 1, 10, 1, 2)
        number_objs_label = QtGui.QLabel(' (#' + str(self.j + 1) + ' of ' + str(total_num_obj) + ' objects)', self)
        grid.addWidget(number_objs_label, 1, 12, 1, 1)

        ### Close button
        # TODO
        # close_button = QPushButton('Close')
        # close_button.clicked.connect(self.close_prog)
        # close_button.setToolTip('Close the program.')
        # grid.addWidget(close_button, 1,31,1,1)

        ### image cutout
        self.cutout = pg.GraphicsLayoutWidget(self)
        cutout_size = 500
        self.cutout.setMinimumSize(cutout_size, cutout_size)
        self.cutout.setMaximumSize(cutout_size, cutout_size)
        grid.addWidget(self.cutout, 4, 1, 5, 5)

        cutout_title = ('Image:')
        cutout_title_label = QtGui.QLabel(cutout_title, self)
        grid.addWidget(cutout_title_label, 2, 1, 1, 1)

        # cuts for the image
        self.cut_cutout1 = cut_cutout1[0]  # np.round(cut_cutout1[0],6)
        self.cut_cutout2 = cut_cutout2[0]  # np.round(cut_cutout2[0],6)

        # enter cuts
        cut_cutout1_comm = QtGui.QLabel('Cut min', self)
        grid.addWidget(cut_cutout1_comm, 3, 1, 1, 1)
        cut_cutout2_comm = QtGui.QLabel('Cut max', self)
        grid.addWidget(cut_cutout2_comm, 3, 3, 1, 1)

        self.le_cut_cutout1 = QtGui.QLineEdit(self)
        grid.addWidget(self.le_cut_cutout1, 3, 2, 1, 1)
        self.le_cut_cutout1.returnPressed.connect(self.show_cutout)
        self.le_cut_cutout2 = QtGui.QLineEdit(self)
        grid.addWidget(self.le_cut_cutout2, 3, 4, 1, 1)
        self.le_cut_cutout2.returnPressed.connect(self.show_cutout)

        empty = QtGui.QLabel(
            '                                                                                                     ',
            self)
        grid.addWidget(empty, 3, 5, 1, 1)

        self.le_cut_cutout1.setText(str(self.cut_cutout1))
        self.le_cut_cutout2.setText(str(self.cut_cutout2))

        self.show_cutout()

        ### 2D spec
        self.spec_2D = pg.GraphicsLayoutWidget(self)
        spec_2D_size = 500
        grid.addWidget(self.spec_2D, 9, 2, 2, 8)

        spec_2D_show = [True]
        if spec_2D_show[0]:
            self.show_spec_2D()

        # set slider to change cuts in 2D spec
        self.cuts_spec_2D = cuts_spec_2D[0]
        sld_spec_2D = QtGui.QSlider(QtCore.Qt.Vertical, self)
        grid.addWidget(sld_spec_2D, 9, 1, 2, 1)
        sld_spec_2D.setRange(10, 1000)
        sld_spec_2D.setValue(self.cuts_spec_2D)
        sld_spec_2D.setSingleStep(1)
        sld_spec_2D.valueChanged[int].connect(self.changeValue_spec_2D_cuts)
        sld_spec_2D.setToolTip('Slide to change cuts.')

        ### set full spectrum
        self.full_spec = pg.GraphicsLayoutWidget(self)
        self.full_spec.setMinimumWidth(1000)
        grid.addWidget(self.full_spec, 12, 2, 4, 8)
        self.plot_spec()

        # set redshift slider
        sld_redshift = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        grid.addWidget(sld_redshift, 18, 1, 1, 8)
        sld_redshift.setRange(z_slider[0] * 1000, 10000)  # large numbers to allow for smaller steps
        sld_redshift.setValue(z_slider[0] * 1000)
        sld_redshift.setSingleStep(1)
        sld_redshift.valueChanged[int].connect(self.changeValue_sld_redshift)
        sld_redshift.setToolTip('Slide to redshift.')

        title_z = QtGui.QLabel('z = ', self)
        self.le_z = QtGui.QLineEdit(self)
        grid.addWidget(title_z, 18, 10, 1, 1)
        grid.addWidget(self.le_z, 18, 11, 1, 1)

        # z_label = QtGui.QLabel('z = ', self)
        # z_label2 = QtGui.QLabel(str(self.z_slider), self)
        # grid.addWidget(z_label,19,10,1,1)
        # grid.addWidget(z_label2,19,11,1,1)

        ### set buttons for next or previous object
        np_name = {0: ['next', 'right'],
                   1: ['previous', 'left']}
        for i in range(2):
            button_np = QtGui.QPushButton('', self)
            button_np.setIcon(QtGui.QIcon(np_name[i][0] + '.png'))
            button_np.setToolTip('Look at ' + np_name[i][0] + ' object.')
            button_np.setText(np_name[i][0])
            button_np.clicked.connect(self.np_obj)
            button_np.setShortcut(np_name[i][1])
            if np_name[i][0] == 'previous':
                grid.addWidget(button_np, 2, 17, 1, 1)
            else:
                grid.addWidget(button_np, 2, 19, 1, 1)

        ### comment line
        title_comm = QtGui.QLabel('Comment:', self)
        self.le_comment = QtGui.QLineEdit(self)
        grid.addWidget(title_comm, 3, 12, 1, 1)
        grid.addWidget(self.le_comment, 4, 12, 1, 3)

        ### Write position (convert to hour)
        RA = input_cat_dict['ra'][self.j]
        DEC = input_cat_dict['dec'][self.j]
        RA_hour = Angle(RA, unit=u.degree).hour
        RA_hour1 = int(RA_hour)
        RA_hour2 = 60 * (RA_hour - RA_hour1)
        RA_hour3 = np.round(60 * (RA_hour2 - int(RA_hour2)), 5)
        RA_label1 = QtGui.QLabel('RA:', self)
        RA_label2 = QtGui.QLabel(str(RA_hour1) + ':' +
                                 str(int(RA_hour2)) + ':' +
                                 str(RA_hour3), self)
        grid.addWidget(RA_label1, 4, 17, 1, 1)
        grid.addWidget(RA_label2, 4, 18, 1, 1)
        DEC_hour = DEC
        DEC_hour1 = int(DEC)
        DEC_hour2 = -60 * (DEC_hour - DEC_hour1)
        DEC_hour3 = np.round(60 * (DEC_hour2 - int(DEC_hour2)), 5)
        DEC_label1 = QtGui.QLabel('DEC:', self)
        DEC_label2 = QtGui.QLabel(str(DEC_hour1) + ':' +
                                  str(int(DEC_hour2)) + ':' +
                                  str(DEC_hour3), self)
        grid.addWidget(DEC_label1, 5, 17, 1, 2)
        grid.addWidget(DEC_label2, 5, 18, 1, 2)

        ### eazy results
        self.eazy_fig_widget = pg.GraphicsLayoutWidget(self)
        self.eazy_z_widget = pg.GraphicsLayoutWidget(self)
        grid.addWidget(self.eazy_fig_widget, 7, 12, 5, 10)
        grid.addWidget(self.eazy_z_widget, 12, 12, 5, 7)
        self.show_eazy_fig()

        ### Write eazy results

        '''
        z_raw_chi2 = np.round(self.zout['z_raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtGui.QLabel('Chi2: '+str(z_raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,7,31,1,1)

        raw_chi2 = np.round(self.zout['raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtGui.QLabel('Chi2: '+str(raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,8,31,1,1)
        '''

        self.z_phot_chi2 = np.round(self.zout['z_phot_chi2'][self.j], 3)
        eazy_raw_chi2 = QtGui.QLabel('Chi2: ' + str(self.z_phot_chi2), self)
        grid.addWidget(eazy_raw_chi2, 9, 31, 1, 1)

        self.sfr = np.round(self.zout['sfr'][self.j], 3)
        eazy_sfr = QtGui.QLabel('SFR: ' + str(self.sfr), self)
        grid.addWidget(eazy_sfr, 10, 31, 1, 1)

        self.mass = np.round(self.zout['mass'][self.j] / 10 ** 9, 3)
        eazy_mass = QtGui.QLabel('mass: ' + str(self.mass), self)
        grid.addWidget(eazy_mass, 11, 31, 1, 1)

    #############################################################################
    ### functions

    def close_prog(self):
        # TODO: save catalogue!
        print('Well done! :)')
        # self.close()

    def changeValue_cutout_cuts(self, value):
        self.cuts_cutout = value
        cuts_cutout[0] = value
        self.show_cutout()

    def show_spec_2D(self):

        self.spec_2D.clear()

        hdu = fits.open(specs_for_Ivan_dir + 'gds-grizli-v5.0_0' + str(self.ID_here) + '.stack.fits')
        image_header = hdu[0].header
        header = hdu[1].header
        image_sci = hdu[1].data
        hdu.close()

        img_spec_2D = pg.ImageItem(border='k')
        viridis_lookuptable = np.asarray([np.asarray(cmaps.viridis(k)) * 255 for k in range(cuts_spec_2D[0])])
        img_spec_2D.setLookupTable(viridis_lookuptable)
        img_spec_2D.setImage(np.rot90(image_sci)[::-1])
        self.view_spec_2D = self.spec_2D.addViewBox()
        self.view_spec_2D.addItem(img_spec_2D)
        self.view_spec_2D.setAspectLocked(True)

    def changeValue_spec_2D_cuts(self, value):
        self.cuts_spec_2D = value
        cuts_spec_2D[0] = value
        self.show_spec_2D()

    def changeValue_sld_redshift(self, value):
        self.z_slider = float(value / 1000)
        # z_slider[0] = value
        self.le_z.setText(str(self.z_slider))
        self.plot_spec()

        input_cat_dict['z_spec'][self.j] = self.z_slider

    def changeValue_spec_2D_model_cuts(self, value):
        self.cuts_spec_2D_model = value
        cuts_spec_2D_model[0] = value
        self.show_spec_2D_model()

    def plot_spec(self):

        self.full_spec.clear()
        pfs = self.full_spec.addPlot()
        zline = pg.InfiniteLine(angle=0, movable=False, pen=(50, 100, 100))

        spec1 = specs_for_Ivan_dir + "gds-grizli-v5.0_0" + str(self.ID_here) + ".1D.fits"
        infos_dict_spec, header = read_spec_1D(spec1)

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
        for j in lbda:
            vLines_all = pg.InfiniteLine(angle=90, movable=False,
                                         pen=lines_Pen)
            line_pos = lbda[j] * (self.z_slider + 1)
            vLines_all.setPos(line_pos)
            pfs.addItem(vLines_all, ignoreBounds=True)
            line_name_text = j
            annotate2 = pg.TextItem(text=line_name_text, color=c_otherlines,
                                    anchor=(1, 1), angle=-90)
            annotate2.setPos(line_pos, 0.1)
            pfs.addItem(annotate2)

    def np_obj(self, parent):
        # go to next or previous object in catalogue

        # Save comment
        comment = self.le_comment.text()
        if len(comment) != 0:
            comments[self.j] = comment

        self.cut_cutout1 = float(self.le_cut_cutout1.text())
        self.cut_cutout2 = float(self.le_cut_cutout2.text())
        cut_cutout1[0] = self.cut_cutout1
        cut_cutout2[0] = self.cut_cutout2

        self.save_now()
        self.signal_next_previous.emit(self.sender().text())

    def save_now(self):
        input_cat_dict['SFR'][self.j] = self.sfr
        input_cat_dict['mass'][self.j] = self.mass
        input_cat_dict['chi2'][self.j] = self.z_phot_chi2
        write_output(input_cat_dict, comments, 'test.fits')

    def show_cutout(self):

        cutout_file = specs_for_Ivan_dir + 'gds-grizli-v5.0_0' + str(self.ID_here) + '.beams.fits'
        hdu = fits.open(cutout_file)
        header_band = hdu[1].header
        data_band = hdu[1].data
        hdu.close()
        band_ps = pix_scale(header_band)

        p1 = float(self.le_cut_cutout1.text())
        p2 = float(self.le_cut_cutout2.text())

        # make sure that percentiles work, reset to standard values in case of wrong entry
        if p1 < 0:
            p1 = 0
        if p2 > 100:
            p2 = 100
        if p1 > 100:
            p1 = 0
        if p2 < 0:
            p2 = 100
        if p2 < p1:
            p1 = 0
            p2 = 100

        self.perc10 = np.percentile(data_band, p1)
        self.perc90 = np.percentile(data_band, p2)

        xy_band = radec_to_pix(input_cat_dict['ra'][self.j],
                               input_cat_dict['dec'][self.j], header_band)

        x_band = xy_band[0]
        y_band = xy_band[1]
        self.cutout.clear()
        img_band = pg.ImageItem(border='k')
        img_band.setLookupTable(viridis)
        data_band_flipped = np.rot90(np.fliplr(data_band))
        img_band.setImage(data_band_flipped)

        self.cut_cutout1 = self.perc10  # float(self.le_cut_cutout1.text()) * 10**-23
        self.cut_cutout2 = self.perc90  # float(self.le_cut_cutout2.text()) * 10**-23
        cut_cutout1[0] = self.cut_cutout1
        cut_cutout2[0] = self.cut_cutout2

        img_band.setLevels([cut_cutout1[0], cut_cutout2[0]])
        self.view_cutout = self.cutout.addViewBox()
        self.view_cutout.addItem(img_band)

        # width_window_pix = width_window[0] / band_ps
        # self.view_cutout.setRange(QtCore.QRectF(x_band-width_window_pix/2.,
        #                                     y_band-width_window_pix/2.,
        #                                     width_window_pix,
        #                                     width_window_pix))
        self.view_cutout.setAspectLocked(True)

        ### TODO: position of lines seems shifted and doesn't match with catalogue

        # test_line = pg.InfiniteLine(angle=90,movable=False,
        #                            pen=pg.mkPen(color=c_data_crossline, width = 1))
        # test_line.setPos([x_band,0])
        # test_line2 = pg.InfiniteLine(angle=0,movable=False,
        #                             pen=pg.mkPen(color=c_data_crossline, width = 1))
        # test_line2.setPos([0,y_band])
        # self.view_cutout.addItem(test_line)
        # self.view_cutout.addItem(test_line2)


def main():
    muse_fresco_cat = Table(fits.getdata(config['data']['MUSE_LAEs']))
    ids = muse_fresco_cat['id']

    input_cat = load_phot_cat(ids=ids, **config)

    ID = input_cat['id']
    total_num_obj = len(ID)

    print(total_num_obj)

    for key in ('SFR', 'mass', 'chi2'):
        input_cat.add_column(-99., name=key)

    # initialise

    viridis_lookuptable = np.asarray([np.asarray(cmaps.viridis(k)) * 255 for k in range(200)])

    # initialise values for cuts in images
    cuts_cutout = [2000]
    cuts_spec_2D = [400]
    cuts_spec_2D_model = [400]

    cut_cutout1 = [0]
    cut_cutout2 = [100]

    z_slider = [4.6]

    # initiate lists and variables

    comments = np.asarray(['-' for i in range(len(ID))])
    # This makes sure that if the comments were restricted to some length before,
    # this restriction is now lifted
    lines_comment_new = ['-' for a in comments]
    lines_comment_new[:] = comments
    comments = lines_comment_new

    j = 0  # initialise running variable for objects
    width_window = [8.]  # width of the thumbnail cut-out windows in arcsec

    # set colours
    c_data_crossline = 'r'

    # app = QtWidgets.QApplication(sys.argv)
    # window = MainWindow()
    # window.show()
    # sys.exit(app.exec_())


if __name__ == '__main__':
    main()
