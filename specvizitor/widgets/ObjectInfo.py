from astropy.coordinates import SkyCoord


from pyqtgraph.Qt import QtWidgets


class ObjectInfo(QtWidgets.QGroupBox):
    def __init__(self, config, parent=None):
        self._config = config

        self._j = None
        self._cat = None

        super().__init__(parent)
        self.setTitle('Object Information')
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        # display RA
        self.ra_label = QtWidgets.QLabel()
        grid.addWidget(self.ra_label, 1, 1, 1, 1)

        # display Dec
        self.dec_label = QtWidgets.QLabel()
        grid.addWidget(self.dec_label, 2, 1, 1, 1)

        self.setLayout(grid)

    def load_object(self, j):
        self._j = j

        if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
            c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
            ra, dec = c.to_string('hmsdms').split(' ')
            self.ra_label.setText("RA: {}".format(ra))
            self.dec_label.setText("Dec: {}".format(dec))

    def load_project(self, cat):
        self._cat = cat
        self.setEnabled(True)
