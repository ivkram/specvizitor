from qtpy import QtWidgets, QtCore, QtGui

import logging

from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..utils.widgets import AbstractWidget, MyQLineEdit

logger = logging.getLogger(__name__)


class ObjectInfo(AbstractWidget):
    def __init__(self, parent=None):
        self.all_columns: dict[str, str] | None = None

        self._table: QtWidgets.QTableWidget | None = None
        self._table_items: dict[str, list[tuple[QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem]]] | None = None

        self._search_label: QtWidgets.QLabel | None = None
        self._search_lineedit: MyQLineEdit | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Preferred)

        QtGui.QShortcut("/", self, self._set_focus)

    def _create_table_items(self):
        if self.all_columns is None:
            self._table_items = {}
            return

        table_items = {}
        for cname, cname_annotated in self.all_columns.items():
            cname_item = QtWidgets.QTableWidgetItem(cname_annotated)
            value_item = QtWidgets.QTableWidgetItem('')

            table_items[cname] = cname_item, value_item

        self._table_items = table_items

    def _set_table_items(self):
        self._table.setRowCount(len(self._table_items))
        for i, row in enumerate(self._table_items.values()):
            self._table.setItem(i, 0, row[0])
            self._table.setItem(i, 1, row[1])

    @QtCore.Slot(object)
    def update_table_items(self, cat: Catalog | None):
        self.all_columns = cat.annotated_colnames if cat is not None else None

        self._create_table_items()
        self._set_table_items()
        self.update_view()

    @QtCore.Slot()
    def update_view(self):
        for i, cname in enumerate(self._table_items.keys()):
            self._table.setRowHidden(i, self._search_lineedit.text().upper() not in cname.upper())

    def init_ui(self):
        self._table = QtWidgets.QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setHorizontalHeaderLabels(('Key', 'Value'))
        self._table.verticalHeader().hide()
        self._table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Fixed)

        self._search_label = QtWidgets.QLabel("Search:", self)
        self._search_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Maximum)
        self._search_lineedit = MyQLineEdit(self)
        self._search_lineedit.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Maximum)
        self._search_lineedit.setMinimumWidth(50)

        self._search_lineedit.textChanged[str].connect(self.update_view)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._table)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._search_label)
        sub_layout.addWidget(self._search_lineedit)

        self.layout().addLayout(sub_layout)

    @QtCore.Slot()
    def load_inspection_data(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object)
    def load_object(self, j: int, inspection_data: InspectionData, cat_entry: Catalog | None):

        if cat_entry is None:
            for row in self._table_items.values():
                row[1].setText("")
            return

        for cname, row in self._table_items.items():
            try:
                value = cat_entry.get_col(cname)
                value = f"{value:.8f}" if isinstance(value, float) else str(value)
                row[1].setText(value)
            except KeyError as e:
                logger.warning(e)
                row[1].setText("")

    @QtCore.Slot()
    def _set_focus(self):
        self._search_lineedit.clear()
        self._search_lineedit.setFocus()
