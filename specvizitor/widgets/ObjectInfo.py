from astropy.coordinates import SkyCoord
from qtpy import QtWidgets

import logging

from ..appdata import AppData
from ..config import config
from ..utils.table_tools import column_not_found_message
from .AbstractWidget import AbstractWidget


logger = logging.getLogger(__name__)


class ObjectInfo(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ObjectInfo, parent=None):
        super().__init__(layout=QtWidgets.QGridLayout(), parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(2)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # self._table.setHorizontalHeaderLabels(('key', 'value'))
        self._table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        # display information about the object
        self._table_items = self.create_table_items(self.cfg.items)
        self.set_items()

    @staticmethod
    def create_table_items(items) -> list[tuple[QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem]]:
        if items is None:
            return []

        table_items = []
        for cname in items:
            cname_item = QtWidgets.QTableWidgetItem(cname)
            value_item = QtWidgets.QTableWidgetItem('')

            table_items.append((cname_item, value_item))

        return table_items

    def set_items(self):
        self._table.setRowCount(len(self._table_items))
        for i, row in enumerate(self._table_items):
            self._table.setItem(i, 0, row[0])
            self._table.setItem(i, 1, row[1])

    def update_items(self):
        if self.cfg.show_all and self.rd.cat is not None:
            self._table_items = self.create_table_items(self.rd.cat.colnames)
        else:
            self._table_items = self.create_table_items(self.cfg.items)
        self.set_items()

    def init_ui(self):
        self.layout().addWidget(self._table, 1, 1, 1, 1)

    def load_object(self):
        for row in self._table_items:
            cname = row[0].text()
            try:
                row[1].setText(str(self.rd.cat.loc[self.rd.id][cname]))
            except KeyError:
                if cname in self.rd.cat.colnames:
                    logger.warning('Object not found in the catalogue (ID: {})'.format(self.rd.id))
                else:
                    logger.warning(column_not_found_message(cname, self.rd.config.catalogue.translate))
                row[1].setText('')

        # if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
        #     c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
        #     ra, dec = c.to_string('hmsdms').split(' ')
        #     self.ra_label.setText("RA: {}".format(ra))
        #     self.dec_label.setText("Dec: {}".format(dec))
