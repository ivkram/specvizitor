from astropy.coordinates import SkyCoord
from astropy.table import Table
from qtpy import QtWidgets, QtCore

import logging

from ..appdata import AppData
from ..config import config
from ..utils.table_tools import column_not_found_message
from .AbstractWidget import AbstractWidget


logger = logging.getLogger(__name__)


class ObjectInfo(AbstractWidget):
    def __init__(self, cfg: config.ObjectInfo, parent=None):
        self.cfg = cfg

        self._search_lineedit: QtWidgets.QLineEdit | None = None
        self._table: QtWidgets.QTableWidget | None = None
        self._table_items: list[tuple[QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem]] | None = None

        super().__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

    def create_table_items(self, cat: Table | None = None):
        if self.cfg.show_all and cat is not None:
            items = cat.colnames
        else:
            items = self.cfg.items

        if items is None:
            return []

        table_items = []
        for cname in items:
            cname_item = QtWidgets.QTableWidgetItem(cname)
            value_item = QtWidgets.QTableWidgetItem('')

            table_items.append((cname_item, value_item))

        self._table_items = table_items

    def set_table_items(self):
        self._table.setRowCount(len(self._table_items))
        for i, row in enumerate(self._table_items):
            self._table.setItem(i, 0, row[0])
            self._table.setItem(i, 1, row[1])

    @QtCore.Slot(Table)
    def update_table_items(self, cat: Table | None = None):
        self.create_table_items(cat=cat)
        self.set_table_items()

    def init_ui(self):
        self._search_lineedit = QtWidgets.QLineEdit(self)

        self._table = QtWidgets.QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # self._table.setHorizontalHeaderLabels(('key', 'value'))
        self._table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        self.update_table_items()

    def connect(self):
        self._search_lineedit.textChanged[str].connect(self.search)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._table)
        self.layout().addWidget(self._search_lineedit)

    def search(self, keyword):
        for i, row in enumerate(self._table_items):
            if keyword in row[0].text():
                self._table.showRow(i)
            else:
                self._table.hideRow(i)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(AppData)
    def load_object(self, rd: AppData):
        try:
            rd.cat.loc[rd.id]
        except KeyError:
            logger.warning('Object not found in the catalogue (ID: {})'.format(rd.id))
            return

        for row in self._table_items:
            cname = row[0].text()
            try:
                row[1].setText(str(rd.cat.loc[rd.id][cname]))
            except KeyError:
                logger.warning(column_not_found_message(cname, rd.cat.meta.get('aliases')))
                row[1].setText('')

        # if 'ra' in self._cat.colnames and 'dec' in self._cat.colnames:
        #     c = SkyCoord(ra=self._cat['ra'][self._j], dec=self._cat['dec'][self._j], frame='icrs', unit='deg')
        #     ra, dec = c.to_string('hmsdms').split(' ')
        #     self.ra_label.setText("RA: {}".format(ra))
        #     self.dec_label.setText("Dec: {}".format(dec))
