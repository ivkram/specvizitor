from astropy.table import Table
from qtpy import QtWidgets, QtCore

import logging
import numpy as np
import pathlib

from ..io.inspection_data import InspectionData
from ..utils.table_tools import get_table_indices, loc_full
from ..utils.widgets import AbstractWidget


logger = logging.getLogger(__name__)


class Subsets(AbstractWidget):
    inspect_button_clicked = QtCore.Signal()
    pause_inspecting_button_clicked = QtCore.Signal()
    stop_inspecting_button_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        self._inspect_subset: QtWidgets.QPushButton | None = None
        self._pause_inspecting: QtWidgets.QPushButton | None = None
        self._stop_inspecting: QtWidgets.QPushButton | None = None
        self._subset_info: QtWidgets.QLabel | None = None

        self._subset_cat: Table | None = None
        self._subset_name: str | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

    def init_ui(self):
        self._inspect_subset = QtWidgets.QPushButton('Inspect...', parent=self)
        self._pause_inspecting = QtWidgets.QPushButton('Pause', parent=self)
        self._pause_inspecting.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting = QtWidgets.QPushButton('Stop', parent=self)
        self._stop_inspecting.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self._stop_inspecting.setEnabled(False)

        self._subset_info = QtWidgets.QLabel(self)
        self._subset_info.setVisible(False)

        self._inspect_subset.clicked.connect(self.inspect_button_clicked.emit)
        self._pause_inspecting.clicked.connect(self.pause_inspecting_button_clicked.emit)
        self._stop_inspecting.clicked.connect(self.stop_inspecting_button_clicked.emit)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._inspect_subset)
        sub_layout.addWidget(self._pause_inspecting)
        sub_layout.addWidget(self._stop_inspecting)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._subset_info)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(str, object)
    def load_subset(self, subset_path: str, subset: Table):
        self._subset_cat = subset
        self._subset_name = pathlib.Path(subset_path).name

        self._pause_inspecting.setEnabled(True)
        self._stop_inspecting.setEnabled(True)

        self.set_subset_info()
        self._subset_info.setVisible(True)

    def set_subset_info(self, obj_str: str | None = None):
        if obj_str is None:
            obj_str = '-'
        self._subset_info.setText(f'Subset: {self._subset_name}\nObject: {obj_str}/{len(self._subset_cat)}')

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        if self._subset_cat:
            try:
                j_subset = loc_full(self._subset_cat, review.get_id(j, full=True))['__index__']
                # j_subset, = np.where(self._subset_cat['id'] == review.get_id(j))[0]
                self.set_subset_info(str(j_subset + 1))

            except ValueError:
                self.set_subset_info()

    @QtCore.Slot(bool)
    def pause_inspecting_subset(self, is_paused: bool):
        if is_paused:
            self._pause_inspecting.setText('Resume')
        else:
            self._pause_inspecting.setText('Pause')

    @QtCore.Slot()
    def stop_inspecting_subset(self):
        self._subset_cat = None
        self._subset_name = None
        self._pause_inspecting.setText('Pause')

        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting.setEnabled(False)
        self._subset_info.setVisible(False)
