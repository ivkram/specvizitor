from qtpy import QtWidgets, QtCore

from functools import partial


class TableColumns(QtWidgets.QDialog):
    visible_columns_updated = QtCore.Signal(list)

    def __init__(self, colnames: list[str], visible_columns: list[str], parent=None):
        self.colnames = colnames
        self.visible_columns = visible_columns

        self._check_all: QtWidgets.QPushButton | None = None
        self._uncheck_all: QtWidgets.QPushButton | None = None

        self._table: QtWidgets.QTableWidget | None = None
        self._checkboxes: list[QtWidgets.QCheckBox] | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setWindowTitle("Table Columns")

        self.init_ui()
        self.set_layout()
        self.populate()

    def _create_checkboxes(self):
        checkboxes = []
        for i, name in enumerate(self.colnames):
            checkbox = QtWidgets.QCheckBox(self)
            checkbox.setChecked(name in self.visible_columns)
            checkboxes.append(checkbox)

        self._checkboxes = checkboxes

    def _add_table_items(self):
        for i, name in enumerate(self.colnames):
            checkbox_container = QtWidgets.QWidget(self)
            sub_layout = QtWidgets.QHBoxLayout()
            sub_layout.setAlignment(QtCore.Qt.AlignCenter)
            sub_layout.addWidget(self._checkboxes[i])
            checkbox_container.setLayout(sub_layout)

            self._table.setCellWidget(i, 0, checkbox_container)
            self._table.setItem(i, 1, QtWidgets.QTableWidgetItem(name))

    def init_ui(self):
        self._check_all = QtWidgets.QPushButton('Check All', self)
        self._uncheck_all = QtWidgets.QPushButton('Uncheck All', self)

        self._table = QtWidgets.QTableWidget(len(self.colnames), 2, self)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setHorizontalHeaderLabels(('Visible', 'Name'))
        self._table.horizontalHeader().resizeSection(0, 100)
        self._table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self._table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

        self._create_checkboxes()
        self._add_table_items()

        # add OK/Cancel buttons
        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)

        self._check_all.pressed.connect(partial(self._all_action, True))
        self._uncheck_all.pressed.connect(partial(self._all_action, False))

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._check_all)
        sub_layout.addWidget(self._uncheck_all)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._table)
        self.layout().addWidget(self._button_box)

    def accept(self):
        self.visible_columns = [cname for i, cname in enumerate(self.colnames) if self._checkboxes[i].isChecked()]
        self.visible_columns_updated.emit(self.visible_columns)

        super().accept()

    @QtCore.Slot()
    def _all_action(self, state: bool):
        for c in self._checkboxes:
            c.setChecked(state)
