# import eazy

from qtpy import QtWidgets


class Eazy(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        self._run_eazy_button = QtWidgets.QPushButton("Run Eazy")
        self._run_eazy_button.clicked.connect(self.run_eazy)
        grid.addWidget(self._run_eazy_button, 1, 1)

        '''
        z_raw_chi2 = np.round(self.zout['z_raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtWidgets.QLabel('Chi2: '+str(z_raw_chi2), self)

        raw_chi2 = np.round(self.zout['raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtWidgets.QLabel('Chi2: '+str(raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,8,31,1,1)

        self.z_phot_chi2 = np.round(self.zout['z_phot_chi2'][self.j], 3)
        eazy_raw_chi2 = QtWidgets.QLabel('Chi2: ' + str(self.z_phot_chi2), self)

        self.sfr = np.round(self.zout['sfr'][self.j], 3)
        eazy_sfr = QtWidgets.QLabel('SFR: ' + str(self.sfr), self)

        self.mass = np.round(self.zout['mass'][self.j] / 10 ** 9, 3)
        eazy_mass = QtWidgets.QLabel('mass: ' + str(self.mass), self)
        '''

        self.setLayout(grid)

    def run_eazy(self):
        pass
        # eazy_inst = eazy.photoz.PhotoZ(param_file=self._parent.config['data']['eazy']['param_file'],
        #                                translate_file=self._parent.config['data']['eazy']['translate_file'],
        #                                zeropoint_file=self._parent.config['data']['eazy']['zeropoint_file'],
        #                                load_prior=False, load_products=False, n_proc=-1)
