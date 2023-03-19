from qtpy import QtWidgets, QtCore

import logging

from ..appdata import AppData
from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class QuickSearch(AbstractWidget):
    object_selected = QtCore.Signal(int)

    def __init__(self, rd: AppData, parent=None):
        self.rd = rd

        self._go_to_id_button: QtWidgets.QPushButton | None = None
        self._id_field: QtWidgets.QLineEdit | None = None
        self._go_to_index_button: QtWidgets.QPushButton | None = None
        self._index_field: QtWidgets.QLineEdit | None = None

        super().__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

    def init_ui(self):
        # create a `Go to ID` button
        self._go_to_id_button = QtWidgets.QPushButton(self)
        self._go_to_id_button.setText('Go to ID')
        self._go_to_id_button.setFixedWidth(110)

        self._id_field = QtWidgets.QLineEdit(self)

        # create a `Go to index` button
        self._go_to_index_button = QtWidgets.QPushButton(self)
        self._go_to_index_button.setText('Go to #')
        self._go_to_index_button.setFixedWidth(110)

        self._index_field = QtWidgets.QLineEdit(self)

    def connect(self):
        self._go_to_id_button.clicked.connect(self.go_to_id)
        self._id_field.returnPressed.connect(self.go_to_id)
        self._go_to_index_button.clicked.connect(self.go_to_index)
        self._index_field.returnPressed.connect(self.go_to_index)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())

    def populate(self):
        self.layout().addWidget(self._go_to_id_button, 1, 1, 1, 1)
        self.layout().addWidget(self._id_field, 1, 2, 1, 1)
        self.layout().addWidget(self._go_to_index_button, 2, 1, 1, 1)
        self.layout().addWidget(self._index_field, 2, 2, 1, 1)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    def go_to_id(self):
        text = self._id_field.text()
        self._id_field.clear()

        try:
            id_upd = int(text)
        except ValueError:
            logger.error(f'Invalid ID: {text}')
            return

        if id_upd in self.rd.notes.ids:
            self.parent().setFocus()
            self.object_selected.emit(self.rd.notes.get_id_loc(id_upd))
        else:
            logger.error(f'ID `{text}` not found')
            return

    def go_to_index(self):
        text = self._index_field.text()
        self._index_field.clear()

        try:
            index_upd = int(text)
        except ValueError:
            logger.error(f'Invalid index: {text}')
            return

        if 0 < index_upd <= self.rd.notes.n_objects:
            self.parent().setFocus()
            self.object_selected.emit(index_upd - 1)
        else:
            logger.error(f'Index `{text}` out of range')
            return
