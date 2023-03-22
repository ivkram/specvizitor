from qtpy import QtWidgets, QtCore

import logging

from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class QuickSearch(AbstractWidget):
    id_selected = QtCore.Signal(str)
    index_selected = QtCore.Signal(int)

    def __init__(self, parent=None):
        self._go_to_id_button: QtWidgets.QPushButton | None = None
        self._id_field: QtWidgets.QLineEdit | None = None
        self._go_to_index_button: QtWidgets.QPushButton | None = None
        self._index_field: QtWidgets.QLineEdit | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
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
        # don't validate the ID here because it could be either int OR str
        self.id_selected.emit(self._id_field.text())
        self._id_field.clear()

    def go_to_index(self):
        text = self._index_field.text()
        self._index_field.clear()

        # validate the index (must be int)
        try:
            index = int(text)
        except ValueError:
            logger.error(f'Invalid index: {text}')
            return False

        self.index_selected.emit(index)
