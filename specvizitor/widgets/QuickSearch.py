from qtpy import QtWidgets, QtCore

import logging

from ..appdata import AppData
from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class QuickSearch(AbstractWidget):
    object_selected = QtCore.Signal(int)

    def __init__(self, rd: AppData, parent=None):
        super().__init__(layout=QtWidgets.QGridLayout(), parent=parent)

        self.rd = rd

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        # create the `Go to ID` button
        self._go_to_id_button = QtWidgets.QPushButton(self)
        self._go_to_id_button.setText('Go to ID')
        self._go_to_id_button.setFixedWidth(110)
        self._go_to_id_button.clicked.connect(self.go_to_id)

        self._id_field = QtWidgets.QLineEdit(self)
        self._id_field.returnPressed.connect(self.go_to_id)

        # create the `Go to index` button
        self._go_to_index_button = QtWidgets.QPushButton(self)
        self._go_to_index_button.setText('Go to #')
        self._go_to_index_button.setFixedWidth(110)
        self._go_to_index_button.clicked.connect(self.go_to_index)

        self._index_field = QtWidgets.QLineEdit(self)
        self._index_field.returnPressed.connect(self.go_to_index)

        self.init_ui()

    def init_ui(self):
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

        if id_upd in self.rd.df.index:
            self.parent().setFocus()
            self.object_selected.emit(self.rd.df.index.get_loc(id_upd))
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

        if 0 < index_upd <= self.rd.n_objects:
            self.parent().setFocus()
            self.object_selected.emit(index_upd - 1)
        else:
            logger.error(f'Index `{text}` out of range')
            return
