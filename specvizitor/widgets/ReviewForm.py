from qtpy import QtWidgets, QtCore

from ..config import config
from ..io.inspection_data import InspectionData

from .AbstractWidget import AbstractWidget


class ReviewForm(AbstractWidget):
    data_collected = QtCore.Signal(str, dict)

    def __init__(self, cfg: config.ReviewForm, parent=None):

        self.cfg = cfg

        self._checkbox_widgets: dict[str, QtWidgets.QCheckBox] | None = None
        self._comments_widget: QtWidgets.QTextEdit | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

    def create_checkbox_widgets(self, review: InspectionData | None = None):
        if self._checkbox_widgets is not None:
            for w in self._checkbox_widgets.values():
                w.deleteLater()

        if review is None:
            flags = self.cfg.default_flags
        else:
            flags = review.flag_columns

        checkbox_widgets = {}
        if flags is not None:
            for flag_name in flags:
                checkbox_widgets[flag_name] = QtWidgets.QCheckBox(flag_name, self)

        self._checkbox_widgets = checkbox_widgets

    def init_ui(self):
        self.create_checkbox_widgets()
        self._comments_widget = QtWidgets.QTextEdit(self)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())

    def populate(self):
        for i, widget in enumerate(self._checkbox_widgets.values()):
            self.layout().addWidget(widget, i + 1, 1, 1, 1)

        self.layout().addWidget(QtWidgets.QLabel('Comments:', self), len(self._checkbox_widgets) + 1, 1, 1, 1)
        self.layout().addWidget(self._comments_widget, len(self._checkbox_widgets) + 2, 1, 1, 1)

    @QtCore.Slot(InspectionData)
    def load_project(self, review: InspectionData):
        self.setEnabled(True)

        self.create_checkbox_widgets(review=review)
        self.repopulate()

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        self._comments_widget.setText(review.get_value(j, 'comment'))
        for cname, widget in self._checkbox_widgets.items():
            widget.setChecked(review.get_value(j, cname))

    @QtCore.Slot()
    def collect(self):
        comment = self._comments_widget.toPlainText()
        checkboxes = {cname: widget.isChecked() for cname, widget in self._checkbox_widgets.items()}

        self.data_collected.emit(comment, checkboxes)
