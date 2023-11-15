from qtpy import QtCore, QtWidgets

from ..config import config
from ..io.inspection_data import InspectionData

from .AbstractWidget import AbstractWidget


class ReviewForm(AbstractWidget):
    data_collected = QtCore.Signal(str, dict)

    def __init__(self, cfg: config.ReviewForm, parent=None):

        self.cfg = cfg

        self._checkbox_widgets: dict[str, QtWidgets.QCheckBox] | None = None
        self._comments_widget: QtWidgets.QTextEdit | None = None

        self._edit_flags: QtWidgets.QPushButton | None = None

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

    def _create_checkbox_widgets(self, review: InspectionData | None = None):
        if self._checkbox_widgets is not None:
            for w in self._checkbox_widgets.values():
                w.deleteLater()

        flags = self.cfg.default_flags if review is None else review.flag_columns

        checkbox_widgets = {}
        if flags is not None:
            for i, flag_name in enumerate(flags):
                # TODO: overwrite the keyPressEvent method of QtWidgets.QCheckBox to add shortcuts
                checkbox_widget = QtWidgets.QCheckBox(flag_name, self)
                checkbox_widgets[flag_name] = checkbox_widget
                
                if i < 9:
                    checkbox_widget.setShortcut(str(i + 1))

        self._checkbox_widgets = checkbox_widgets

    def init_ui(self):
        self._create_checkbox_widgets()
        self._comments_widget = QtWidgets.QTextEdit(self)

        self._edit_flags = QtWidgets.QPushButton("Edit...", self)
        self._edit_flags.pressed.connect(self._edit_flags_action)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())

    def populate(self):
        for i, widget in enumerate(self._checkbox_widgets.values()):
            self.layout().addWidget(widget, i + 1, 1, 1, 1)

        self.layout().addWidget(QtWidgets.QLabel('Comments:', self), len(self._checkbox_widgets) + 1, 1, 1, 1)
        self.layout().addWidget(self._comments_widget, len(self._checkbox_widgets) + 2, 1, 1, 1)

        self.layout().addWidget(self._edit_flags, len(self._checkbox_widgets) + 3, 1, 1, 1)

    @QtCore.Slot(InspectionData)
    def load_project(self, review: InspectionData):
        self.setEnabled(True)

        self._create_checkbox_widgets(review=review)
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

    def _edit_flags_action(self):
        pass
