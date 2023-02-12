import logging

from astropy.coordinates import SkyCoord

from ..runtime import RuntimeData
from .AbstractWidget import AbstractWidget


from pyqtgraph.Qt import QtWidgets, QtCore


logger = logging.getLogger(__name__)


class ObjectInfo(QtWidgets.QGroupBox, AbstractWidget):
    def __init__(self, rd: RuntimeData, parent=None):
        self.cfg = rd.config.object_info
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        self.setTitle('Object Information')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        grid = QtWidgets.QGridLayout()

        # display information about the object
        self._labels = []
        for i in range(len(self.cfg.items)):
            label_widget = QtWidgets.QLabel()
            label_widget.setHidden(True)
            label_widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self._labels.append(label_widget)
            grid.addWidget(label_widget, i + 1, 1, 1, 1)

        self.setLayout(grid)

    def load_object(self):
        for i, (cname, label) in enumerate(self.cfg.items.items()):
            if cname in self.rd.cat.colnames:
                self._labels[i].setText(label.format(self.rd.cat[cname][self.rd.j]))
                self._labels[i].setHidden(False)
            else:
                logger.warning('`{}` column not found in the catalogue'.format(cname))
                self._labels[i].setHidden(True)

        # if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
        #     c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
        #     ra, dec = c.to_string('hmsdms').split(' ')
        #     self.ra_label.setText("RA: {}".format(ra))
        #     self.dec_label.setText("Dec: {}".format(dec))
