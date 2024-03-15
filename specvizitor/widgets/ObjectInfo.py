from qtpy import QtWidgets, QtCore

import logging

from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..utils.widgets import AbstractWidget

from .TableColumns import TableColumns

logger = logging.getLogger(__name__)


class ObjectInfo(AbstractWidget):
    data_collected = QtCore.Signal(list)

    def __init__(self, parent=None):
        self.all_columns: dict[str, str] | None = None
        self.visible_columns: list[str] | None = None

        self._table: QtWidgets.QTableWidget | None = None
        self._table_items: dict[str, list[tuple[QtWidgets.QTableWidgetItem, QtWidgets.QTableWidgetItem]]] | None = None

        self._search_label: QtWidgets.QLabel | None = None
        self._search_lineedit: QtWidgets.QLineEdit | None = None
        self._display_options: QtWidgets.QPushButton | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

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
        if self.all_columns:
            self.update_visible_columns(list(self.all_columns.keys()))

    @QtCore.Slot()
    def update_view(self):
        for i, cname in enumerate(self._table_items.keys()):
            if cname in self.visible_columns and self._search_lineedit.text() in cname:
                self._table.showRow(i)
            else:
                self._table.hideRow(i)

    @QtCore.Slot(list)
    def update_visible_columns(self, visible_columns: list[str] | None):
        self.visible_columns = visible_columns
        self.update_view()

    def init_ui(self):
        self._table = QtWidgets.QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # self._table.horizontalHeader().hide()
        self._table.horizontalHeader().setStretchLastSection(True)
        # self._table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self._table.setHorizontalHeaderLabels(('Key', 'Value'))
        self._table.verticalHeader().hide()
        self._table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        self._search_label = QtWidgets.QLabel("Search:", self)
        self._search_label.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self._search_lineedit = QtWidgets.QLineEdit(self)
        self._search_lineedit.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Maximum)
        self._search_lineedit.setMinimumWidth(50)
        self._display_options = QtWidgets.QPushButton("Columns...", self)
        self._display_options.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self._search_lineedit.textChanged[str].connect(self.update_view)
        self._display_options.clicked.connect(self._display_options_action)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._table)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._search_label)
        sub_layout.addWidget(self._search_lineedit)
        sub_layout.addWidget(self._display_options)

        self.layout().addLayout(sub_layout)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object)
    def load_object(self, _, __, cat_entry: Catalog | None):

        if cat_entry is None:
            for row in self._table_items.values():
                row[1].setText('')
            return

        for cname, row in self._table_items.items():
            try:
                value = cat_entry.get_col(cname)
                value = f'{value:.8f}' if isinstance(value, float) else str(value)
                row[1].setText(value)
            except KeyError as e:
                logger.warning(e)
                row[1].setText('')

    @QtCore.Slot()
    def collect(self):
        self.data_collected.emit(self.visible_columns)

    def _display_options_action(self):
        dialog = TableColumns(list(self.all_columns.keys()), self.visible_columns, parent=self)
        dialog.visible_columns_updated.connect(self.update_visible_columns)
        if dialog.exec():
            pass
