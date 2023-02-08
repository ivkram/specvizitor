# import eazy

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets


class Eazy(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        self._run_eazy_button = QtWidgets.QPushButton("Run Eazy")
        self._run_eazy_button.clicked.connect(self.run_eazy)
        grid.addWidget(self._run_eazy_button, 1, 1)

        self.setLayout(grid)

    def run_eazy(self):
        pass
        # eazy_inst = eazy.photoz.PhotoZ(param_file=self._parent.config['data']['eazy']['param_file'],
        #                                translate_file=self._parent.config['data']['eazy']['translate_file'],
        #                                zeropoint_file=self._parent.config['data']['eazy']['zeropoint_file'],
        #                                load_prior=False, load_products=False, n_proc=-1)
