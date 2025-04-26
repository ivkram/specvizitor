from astropy.table import Table
from qtpy import QtWidgets, QtCore

import logging
import pathlib

from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
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

        self._subset_cat: Catalog | None = None
        self._subset_name: str | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        self._set_pause_shortcut()

    def init_ui(self):
        self._inspect_subset = QtWidgets.QPushButton('Inspect Subset...', parent=self)
        self._pause_inspecting = QtWidgets.QPushButton('Pause', parent=self)
        self._stop_inspecting = QtWidgets.QPushButton('Stop', parent=self)

        self._inspect_subset.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        for w in (self._pause_inspecting, self._stop_inspecting):
            w.setFixedWidth(90)

        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting.setEnabled(False)

        self._subset_info = QtWidgets.QLabel(self)
        self._subset_info.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self._subset_info.setVisible(False)

        self._inspect_subset.clicked.connect(self.inspect_button_clicked.emit)
        self._pause_inspecting.clicked.connect(self.pause_inspecting_button_clicked.emit)
        self._stop_inspecting.clicked.connect(self.stop_inspecting_button_clicked.emit)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._inspect_subset)
        self.layout().addLayout(sub_layout)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._pause_inspecting)
        sub_layout.addWidget(self._stop_inspecting)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._subset_info)

    def _set_pause_shortcut(self):
        self._pause_inspecting.setShortcut('P')

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
            obj_str = '--'
        self._subset_info.setText(f'Subset: {self._subset_name}\nObject: {obj_str}/{len(self._subset_cat)}')

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        if self._subset_cat:
            subset_entry = self._subset_cat.get_cat_entry(review.get_id(j, full=True), ignore_missing=True)
            if subset_entry is None:
                self.set_subset_info()
            else:
                j_subset = subset_entry.get_col('__index__')
                self.set_subset_info(str(j_subset + 1))

    @QtCore.Slot(bool)
    def pause_subset_inspection(self, is_paused: bool):
        self._pause_inspecting.setText("Resume" if is_paused else "Pause")
        self._set_pause_shortcut()

    @QtCore.Slot()
    def stop_subset_inspection(self):
        self._subset_cat = None
        self._subset_name = None
        self._pause_inspecting.setText('Pause')

        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting.setEnabled(False)
        self._subset_info.setVisible(False)
