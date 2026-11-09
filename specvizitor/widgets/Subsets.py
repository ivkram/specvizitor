import logging
import pathlib

from qtpy import QtCore, QtWidgets

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

        self._subset_positions: dict[int, int] | None = None  # object index -> position in the subset
        self._subset_name: str | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)

        self._set_pause_shortcut()

    def init_ui(self):
        self._inspect_subset = QtWidgets.QPushButton("Open...", parent=self)
        self._pause_inspecting = QtWidgets.QPushButton("Pause", parent=self)
        self._stop_inspecting = QtWidgets.QPushButton("Stop", parent=self)

        for w in (self._inspect_subset, self._pause_inspecting, self._stop_inspecting):
            w.setFixedWidth(85)

        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting.setEnabled(False)

        self._subset_info = QtWidgets.QLabel(self)
        self._subset_info.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
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

    def _set_pause_shortcut(self):
        self._pause_inspecting.setShortcut('P')

    @QtCore.Slot()
    def load_inspection_data(self):
        self.setEnabled(True)

    @QtCore.Slot(str, object)
    def load_subset(self, subset_path: str, subset_positions: dict[int, int]):
        self._subset_positions = subset_positions
        self._subset_name = pathlib.Path(subset_path).name

        self._pause_inspecting.setEnabled(True)
        self._stop_inspecting.setEnabled(True)

        self.set_subset_info()
        self._subset_info.setVisible(True)

    def set_subset_info(self, obj_str: str | None = None):
        if obj_str is None:
            obj_str = '--'
        self._subset_info.setText(f"Subset: {self._subset_name}\nObject: {obj_str}/{len(self._subset_positions)}")
        self._subset_info.setToolTip(self._subset_name)

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, inspection_data: InspectionData):
        if self._subset_positions is not None:
            k = self._subset_positions.get(j)
            self.set_subset_info(None if k is None else str(k + 1))

    @QtCore.Slot(bool)
    def pause_subset_inspection(self, is_paused: bool):
        self._pause_inspecting.setText("Resume" if is_paused else "Pause")
        self._set_pause_shortcut()

    @QtCore.Slot()
    def stop_subset_inspection(self):
        self._subset_positions = None
        self._subset_name = None
        self._pause_inspecting.setText('Pause')

        self._pause_inspecting.setEnabled(False)
        self._stop_inspecting.setEnabled(False)
        self._subset_info.setVisible(False)
