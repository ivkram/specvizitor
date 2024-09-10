from qtpy import QtCore, QtWidgets

from ..config import config
from ..io.inspection_data import InspectionData, REDSHIFT_FILL_VALUE
from ..utils.widgets import AbstractWidget, MyQTextEdit


class InspectionResults(AbstractWidget):
    data_collected = QtCore.Signal(float, str, dict)
    edit_button_clicked = QtCore.Signal()

    def __init__(self, cfg: config.InspectionResults, parent=None):

        self.cfg = cfg
        self._saved_redshift: float | None = None

        self._redshift_widget: QtWidgets.QLabel | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._clear_redshift: QtWidgets.QPushButton | None = None
        self._separator: QtWidgets.QFrame | None = None

        self._checkbox_widgets: dict[str, QtWidgets.QCheckBox] | None = None
        self._comments_widget: MyQTextEdit | None = None

        self._edit_fields: QtWidgets.QPushButton | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        # add shortcuts
        QtWidgets.QShortcut("E", self, self._comments_widget.setFocus)

    def _create_checkbox_widgets(self, review: InspectionData | None = None):
        if self._checkbox_widgets is not None:
            for w in self._checkbox_widgets.values():
                w.deleteLater()

        flags = self.cfg.default_flags if review is None else review.flag_columns

        checkbox_widgets = {}
        for i, flag_name in enumerate(flags):
            # TODO: overwrite the keyPressEvent method of QtWidgets.QCheckBox to add shortcuts
            checkbox_widget = QtWidgets.QCheckBox(flag_name, self)
            checkbox_widget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            checkbox_widgets[flag_name] = checkbox_widget

            if i < 9:
                checkbox_widget.setShortcut(str(i + 1))

        self._checkbox_widgets = checkbox_widgets

    def init_ui(self):
        self._redshift_widget = QtWidgets.QLabel("Redshift: --", self)
        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self._clear_redshift = QtWidgets.QPushButton("Clear", self)

        self._separator = QtWidgets.QFrame(self)
        self._separator.setFrameShape(QtWidgets.QFrame.HLine)

        self._create_checkbox_widgets()
        self._comments_widget = MyQTextEdit(self)
        self._comments_widget.setPlaceholderText('Comment')
        self._comments_widget.setMinimumWidth(90)

        self._edit_fields = QtWidgets.QPushButton("Edit...", self)
        self._edit_fields.clicked.connect(self.edit_button_clicked.emit)

        self._clear_redshift.clicked.connect(self.clear_redshift_value)

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

        self.layout().addWidget(self._edit_fields)

    @QtCore.Slot(InspectionData)
    def load_project(self, review: InspectionData):
        self.setEnabled(True)

        self._create_checkbox_widgets(review=review)
        self.repopulate()

    @QtCore.Slot(float)
    def set_redshift_value(self, redshift: float):
        if redshift != REDSHIFT_FILL_VALUE:
            self._redshift_widget.setText(f"Redshift: {redshift:.4f}")
        else:
            self._redshift_widget.setText(f"Redshift: --")
        self._saved_redshift = redshift

    @QtCore.Slot()
    def clear_redshift_value(self):
        self.set_redshift_value(REDSHIFT_FILL_VALUE)

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        self.set_redshift_value(review.get_value(j, 'z_sviz'))
        self._comments_widget.setText(review.get_value(j, 'comment'))
        for cname, widget in self._checkbox_widgets.items():
            widget.setChecked(review.get_value(j, cname))

    @QtCore.Slot(int, InspectionData)
    def update_inspection_fields(self, j: int, review: InspectionData):
        self._create_checkbox_widgets(review=review)
        self.repopulate()

        self.load_object(j, review)  # not the "cleanest" solution

    @QtCore.Slot()
    def collect(self):
        redshift = self._saved_redshift
        comment = self._comments_widget.toPlainText()
        checkboxes = {cname: widget.isChecked() for cname, widget in self._checkbox_widgets.items()}

        self.data_collected.emit(redshift, comment, checkboxes)
