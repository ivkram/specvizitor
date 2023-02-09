import logging

from astropy.coordinates import SkyCoord


from pyqtgraph.Qt import QtWidgets, QtCore


logger = logging.getLogger(__name__)


class ObjectInfo(QtWidgets.QGroupBox):
    def __init__(self, config, parent=None):
        self._config = config

        self._j = None
        self._cat = None

        super().__init__(parent)
        self.setTitle('Object Information')
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        # display information about the object
        self._labels = []
        for i in range(len(self._config['items'])):
            label_widget = QtWidgets.QLabel()
            label_widget.setHidden(True)
            label_widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self._labels.append(label_widget)
            grid.addWidget(label_widget, i, 1, 1, 1)

        self.setLayout(grid)

    def load_object(self, j):
        self._j = j

        for i, (cname, label) in enumerate(self._config['items'].items()):
            if cname in self._cat.colnames:
                self._labels[i].setText(label.format(self._cat[cname][self._j]))
                self._labels[i].setHidden(False)
            else:
                logger.warning('`{}` column not found in the catalogue'.format(cname))
                self._labels[i].setHidden(True)

        # if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
        #     c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
        #     ra, dec = c.to_string('hmsdms').split(' ')
        #     self.ra_label.setText("RA: {}".format(ra))
        #     self.dec_label.setText("Dec: {}".format(dec))

    def load_project(self, cat):
        self._cat = cat
        self.setEnabled(True)
