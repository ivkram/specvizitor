import logging

# from astropy.coordinates import SkyCoord

from ..runtime.appdata import AppData
from ..runtime import config
from .AbstractWidget import AbstractWidget


from qtpy import QtWidgets, QtCore


logger = logging.getLogger(__name__)


class ObjectInfo(QtWidgets.QGroupBox, AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ObjectInfo, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setTitle('Object Information')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # display information about the object
        self._labels = self.create_info_widgets(self.cfg.items.items())

    @staticmethod
    def create_info_widgets(items) -> dict[str, QtWidgets.QLabel]:
        if items is None:
            return {}

        info_widgets = {}
        for i, (cname, label) in enumerate(items):
            widget = QtWidgets.QLabel()
            widget.setText(label)
            widget.setHidden(True)
            widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

            info_widgets[cname] = widget

        return info_widgets

    def init_ui(self):
        for i, widget in enumerate(self._labels.values()):
            self.layout.addWidget(widget, i + 1, 1, 1, 1)

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
