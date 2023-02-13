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
        self._labels = {}

        if self.cfg.items:
            for i, (cname, label) in enumerate(self.cfg.items.items()):
                widget = QtWidgets.QLabel()
                widget.setText(label)
                widget.setHidden(True)
                widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                self._labels[cname] = widget
                grid.addWidget(widget, i + 1, 1, 1, 1)

        self.setLayout(grid)

    def load_object(self):
        for cname, widget in self._labels.items():
            try:
                widget.setText(self.cfg.items[cname].format(self.rd.cat.loc[self.rd.id][cname]))
            except KeyError:
                if cname in self.rd.cat.colnames:
                    logger.warning('Object not found in the catalogue (ID: {})'.format(self.rd.id))
                else:
                    logger.warning('`{}` column not found in the catalogue'.format(cname))
                widget.setHidden(True)
            else:
                widget.setHidden(False)

        # if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
        #     c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
        #     ra, dec = c.to_string('hmsdms').split(' ')
        #     self.ra_label.setText("RA: {}".format(ra))
        #     self.dec_label.setText("Dec: {}".format(dec))
