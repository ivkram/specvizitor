from qtpy import QtCore, QtGui, QtWidgets

from ..config import config
from ..io.inspection_data import FieldType, InspectionData, REDSHIFT_FILL_VALUE
from ..utils.widgets import AbstractWidget, MyQTextEdit


class InspectionResults(AbstractWidget):
    object_starred = QtCore.Signal(bool)
    first_object_starred = QtCore.Signal(bool)
    redshift_set = QtCore.Signal(bool)
    data_collected = QtCore.Signal(bool, float, str, dict)

    # the field types that can be displayed and edited here
    FIELD_TYPES: tuple[FieldType, ...] = (FieldType.BOOLEAN,)

    def __init__(self, cfg: config.InspectionResults, parent=None):

        self.cfg = cfg
        self._is_starred: bool | None = None
        self._n_starred: int | None = None
        self._redshift: float | None = None

        self._redshift_widget: QtWidgets.QLabel | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._clear_redshift: QtWidgets.QPushButton | None = None
        self._separator: QtWidgets.QFrame | None = None

        self._checkbox_widgets: dict[str, QtWidgets.QCheckBox] | None = None
        self._comments_widget: MyQTextEdit | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)

        QtGui.QShortcut("E", self, self._comments_widget.setFocus)

    def _create_checkbox_widgets(self, inspection_data: InspectionData | None = None):
        if self._checkbox_widgets is not None:
            for w in self._checkbox_widgets.values():
                w.deleteLater()

        flags = self.cfg.default_flags if inspection_data is None else inspection_data.flag_columns

        checkbox_widgets = {}
        for i, flag_name in enumerate(flags):
            # TODO: overwrite the keyPressEvent method of QtWidgets.QCheckBox to add shortcuts
            checkbox_widget = QtWidgets.QCheckBox(flag_name, self)
            checkbox_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
            checkbox_widgets[flag_name] = checkbox_widget

            if i < 9:
                checkbox_widget.setShortcut(str(i + 1))

        self._checkbox_widgets = checkbox_widgets

    def init_ui(self):
        self._redshift_widget = QtWidgets.QLabel("Redshift: --", self)
        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self._clear_redshift = QtWidgets.QPushButton("Clear", self)

        self._separator = QtWidgets.QFrame(self)
        self._separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)

        self._create_checkbox_widgets()
        self._comments_widget = MyQTextEdit(self)
        self._comments_widget.setPlaceholderText('Comment')
        self._comments_widget.setMinimumWidth(90)

        self._clear_redshift.clicked.connect(self.clear_redshift)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._redshift_widget)
        sub_layout.addWidget(self._spacer)
        sub_layout.addWidget(self._clear_redshift)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._separator)
        self._separator.setVisible(False)

        for i, widget in enumerate(self._checkbox_widgets.values()):
            self.layout().addWidget(widget)

        self.layout().addWidget(self._comments_widget)

    @QtCore.Slot(InspectionData)
    def load_inspection_data(self, inspection_data: InspectionData):
        self.setEnabled(True)

        self._create_checkbox_widgets(inspection_data=inspection_data)
        self.repopulate()

        self._n_starred = inspection_data.n_starred

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, inspection_data: InspectionData):
        self._set_starred_state(bool(inspection_data.get_value(j, "starred")))
        self.set_redshift(inspection_data.get_value(j, "z_sviz"))
        self._comments_widget.setText(inspection_data.get_value(j, "comment"))
        for cname, widget in self._checkbox_widgets.items():
            widget.setChecked(bool(inspection_data.get_value(j, cname)))

    @QtCore.Slot()
    def star_object(self):
        starred = not self._is_starred
        self._set_starred_state(starred)

        if self._n_starred == 0 and starred:
            self.first_object_starred.emit(True)
        elif self._n_starred == 1 and not starred:
            self.first_object_starred.emit(False)
        self._n_starred += 1 if starred else -1

    def _set_starred_state(self, starred: bool):
        self._is_starred = starred
        self.object_starred.emit(self._is_starred)

    @QtCore.Slot(float)
    def set_redshift(self, redshift: float):
        self._redshift = redshift

        if self._redshift != REDSHIFT_FILL_VALUE:
            self._redshift_widget.setText(f"Redshift: {self._redshift:.4f}")
            self._clear_redshift.setEnabled(True)
            self.redshift_set.emit(True)
        else:
            self._redshift_widget.setText("Redshift: --")
            self._clear_redshift.setEnabled(False)
            self.setFocus()
            self.redshift_set.emit(False)

    @QtCore.Slot()
    def clear_redshift(self):
        self.set_redshift(REDSHIFT_FILL_VALUE)

    @QtCore.Slot(int, InspectionData)
    def update_inspection_fields(self, j: int, inspection_data: InspectionData):
        self._create_checkbox_widgets(inspection_data=inspection_data)
        self.repopulate()

        self.load_object(j, inspection_data)  # not the "cleanest" solution

    @QtCore.Slot()
    def collect_data(self):
        starred, redshift = self._is_starred, self._redshift
        comment = self._comments_widget.toPlainText()
        checkboxes = {cname: widget.isChecked() for cname, widget in self._checkbox_widgets.items()}

        self.data_collected.emit(starred, redshift, comment, checkboxes)
