from qtpy import QtCore, QtWidgets

from functools import partial
import re

from .FileBrowser import FileBrowser


class TableRowEditor(QtWidgets.QDialog):
    data_collected = QtCore.Signal(list)

    def __init__(self, header: list[str], data: list[str] | None = None, name: str | None = None,
                 item_choices: list[list[str] | None] | None = None, regex_pattern: list[str | None] | None = None,
                 item_filter_list: list[list[str]] | None = None, is_browser: list[bool] | None = None, parent=None):
        self._header = header
        action = 'Add' if data is None else 'Edit'

        if data is None:
            data = [None] * len(header)
        if item_choices is None:
            item_choices = [None] * len(header)
        if is_browser is None:
            is_browser = [False] * len(header)

        self._old_data = data
        self._item_choices = item_choices
        self._regex_pattern = regex_pattern
        self._filter_list = item_filter_list
        self._is_browser = is_browser

        self._button_box: QtWidgets.QDialogButtonBox | None = None
        self._row_items: list[tuple[QtWidgets.QLabel, QtWidgets.QLineEdit | QtWidgets.QComboBox | FileBrowser]] | None = None

        super().__init__(parent=parent)
        if name is None:
            name = 'Row'
        self.setWindowTitle(f"{action} {name}")

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        self.init_ui()
        self.set_layout()
        self.populate()

    @property
    def _new_data(self) -> list[str]:
        data = []
        for row_item in self._row_items:
            text = self.get_item_editor_text(row_item[1])
            data.append(text)
        return data

    @staticmethod
    def get_item_editor_text(item_editor) -> str:
        if hasattr(item_editor, 'path'):
            return item_editor.path
        if hasattr(item_editor, 'currentText'):
            return item_editor.currentText()
        else:
            return item_editor.text()

    def _create_row_items(self):
        editor_width = 720 if sum(self._is_browser) else 360
        self._row_items = []
        for i, (item_label, item_value, item_choices) in enumerate(zip(self._header, self._old_data, self._item_choices)):
            label = QtWidgets.QLabel(f"{item_label}:", self)
            label.setFixedWidth(120)
            if self._is_browser[i]:
                item_editor = FileBrowser(default_path=item_value if item_value else None, line_edit_width=0, parent=self)
            elif item_choices:
                item_editor = QtWidgets.QComboBox(self)
                item_editor.addItems(item_choices)
                if item_value:
                    item_editor.setCurrentIndex(item_choices.index(item_value))
            else:
                item_editor = QtWidgets.QLineEdit(item_value if item_value else "", self)
            if self._regex_pattern or self._filter_list:
                if hasattr(item_editor, 'textChanged'):
                    item_editor.textChanged.connect(self.validate_text)
            item_editor.setFixedWidth(editor_width)
            self._row_items.append((label, item_editor))

        # in case we match against an empty string
        for i, item_value in enumerate(self._old_data):
            item_editor = self._row_items[i][1]
            if hasattr(item_editor, 'textChanged'):
                item_editor.textChanged.emit(item_value if item_value else "")

    def init_ui(self):
        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        self._create_row_items()

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        for row_item in self._row_items:
            sub_layout = QtWidgets.QHBoxLayout()
            sub_layout.addWidget(row_item[0])
            sub_layout.addWidget(row_item[1])
            self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._button_box)

    @QtCore.Slot()
    def validate_text(self):
        ok_button_enabled = True
        for idx, row_item in enumerate(self._row_items):
            text = self.get_item_editor_text(row_item[1])

            use_regex = self._regex_pattern and self._regex_pattern[idx] is not None
            use_filter_list = self._filter_list and self._filter_list[idx] is not None
            if not (use_regex or use_filter_list):
                continue

            if (use_regex and re.match(self._regex_pattern[idx], text)) or (use_filter_list and text in self._filter_list[idx]):
                ok_button_enabled = False
                break

        ok_button = self._button_box.button(QtWidgets.QDialogButtonBox.Ok)
        ok_button.setEnabled(ok_button_enabled)

    def accept(self):
        self.data_collected.emit(self._new_data)
        super().accept()


class ParamTable(QtWidgets.QWidget):
    data_collected = QtCore.Signal(list, list)

    def __init__(self, header: list[str], data: list[list[str]], is_unique: list[bool] | None = None,
                 remember_deleted=True, parent=None, **kwargs):
        self._header = header
        self._old_data = data
        self._row_editor_kwargs = kwargs

        if is_unique is None:
            is_unique = [False] * len(header)
        self._is_unique = is_unique
        self._remember_deleted = remember_deleted

        self._add_button: QtWidgets.QPushButton | None = None
        self._delete_button: QtWidgets.QPushButton | None = None
        self._edit_button: QtWidgets.QPushButton | None = None
        self._reset_button: QtWidgets.QPushButton | None = None

        self._table: QtWidgets.QTableWidget | None = None
        self._table_items: list[list[QtWidgets.QTableWidgetItem]] | None = None
        self._is_deleted: list[bool] | None = None

        super().__init__(parent=parent)

        self.init_ui()
        self.set_layout()
        self.populate()

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    @property
    def _new_data(self):
        data = []
        for row in self._table_items:
            data_row = []
            for item in row:
                data_row.append(str(item.data(0)))
            data.append(data_row)
        return data

    @property
    def _current_row(self):
        return self._table.currentRow()

    def _get_item_filter_list(self, include_current_row=False):
        filter_list = [[] for _ in range(len(self._header))]
        for i, row in enumerate(self._table_items):
            if i == self._current_row and not include_current_row:
                continue
            for j, item in enumerate(row):
                if self._is_unique[j]:
                    filter_list[j].append(str(item.data(0)))
                else:
                    filter_list[j].append(None)
        return filter_list

    def _create_table_items(self):
        table_items = []
        for data_row in self._old_data:
            row = []
            for data_item in data_row:
                row.append(QtWidgets.QTableWidgetItem(data_item))
            table_items.append(row)

        self._table_items = table_items
        self._is_deleted = [False] * len(table_items)

    def _set_table_items(self):
        self._table.setRowCount(len(self._table_items))
        for i, row in enumerate(self._table_items):
            for j, item in enumerate(row):
                self._table.setItem(i, j, item)

    def init_ui(self):
        self._add_button = QtWidgets.QPushButton('Add...', self)
        self._delete_button = QtWidgets.QPushButton('Delete', self)
        self._edit_button = QtWidgets.QPushButton('Edit...', self)
        self._reset_button = QtWidgets.QPushButton('Reset', self)

        for w in (self._add_button, self._delete_button, self._edit_button, self._reset_button):
            w.setFixedWidth(90)
        self._set_buttons_enabled(False)

        self._table = QtWidgets.QTableWidget(len(self._old_data), len(self._header), self)
        self._table.setTextElideMode(QtCore.Qt.ElideLeft)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setHorizontalHeaderLabels(self._header)

        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setMinimumHeight(250)

        self._create_table_items()
        self._set_table_items()

        self._table.selectionModel().selectionChanged.connect(self.selection_changed_action)

        self._add_button.clicked.connect(self._add_row_dialog)
        self._delete_button.clicked.connect(self._delete_row)
        self._edit_button.clicked.connect(self._edit_row_dialog)
        self._reset_button.clicked.connect(self._reset)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        for w in (self._add_button, self._delete_button, self._edit_button, self._reset_button):
            sub_layout.addWidget(w)
        sub_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._table)

    def _set_buttons_enabled(self, a0: bool):
        for w in (self._delete_button, self._edit_button):
            w.setEnabled(a0)

    @QtCore.Slot()
    def selection_changed_action(self):
        self._set_buttons_enabled(not self._is_deleted[self._current_row])

    def _set_strikeout_font(self, row, a0):
        for item in self._table_items[row]:
            f = item.font()
            f.setStrikeOut(a0)
            item.setFont(f)

    @QtCore.Slot()
    def _add_row_dialog(self):
        item_filter_list = self._get_item_filter_list(include_current_row=True)
        dialog = TableRowEditor(header=self._header, item_filter_list=item_filter_list,
                                **self._row_editor_kwargs, parent=self)
        dialog.data_collected.connect(self._add_row)
        dialog.exec()

    @QtCore.Slot(list)
    def _add_row(self, data_row: list[str]):
        row = []
        for data_item in data_row:
            row.append(QtWidgets.QTableWidgetItem(data_item))
        self._table_items.append(row)

        self._table.setRowCount(len(self._table_items))
        for j, item in enumerate(row):
            self._table.setItem(len(self._table_items) - 1, j, item)

        self._is_deleted += [False]

    @QtCore.Slot()
    def _delete_row(self):
        current_row = self._current_row

        if current_row >= len(self._old_data) or not self._remember_deleted:
            self._table_items.pop(current_row)
            self._table.removeRow(current_row)

            self._is_deleted.pop(current_row)
            current_row -= 1
        else:
            self._is_deleted[current_row] = True
            self._set_strikeout_font(current_row, True)

        self._table.selectionModel().clearSelection()
        self._set_buttons_enabled(False)

        if current_row + 1 < len(self._table_items):
            current_row += 1
            self._table.setCurrentCell(current_row, 0)
            self._table_items[current_row][0].tableWidget().setFocus()

    @QtCore.Slot()
    def _edit_row_dialog(self):
        item_filter_list = self._get_item_filter_list(include_current_row=False)
        dialog = TableRowEditor(header=self._header, data=self._new_data[self._current_row],
                                item_filter_list=item_filter_list, **self._row_editor_kwargs, parent=self)
        dialog.data_collected.connect(partial(self._edit_row, self._current_row))
        dialog.exec()

    @QtCore.Slot(list)
    def _edit_row(self, row_index: int, row_data: list[str]):
        for j, item in enumerate(self._table_items[row_index]):
            item.setText(row_data[j])

    @QtCore.Slot()
    def _reset(self):
        self._create_table_items()
        self._set_table_items()

        self._table.selectionModel().clearSelection()
        self._set_buttons_enabled(False)
        self.setFocus()

    @QtCore.Slot()
    def collect(self):
        self.data_collected.emit(self._new_data, self._is_deleted)
