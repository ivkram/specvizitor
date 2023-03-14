import pandas as pd
from qtpy import QtWidgets, QtCore

from ..appdata import AppData
from ..config import config
from ..io.output import get_checkboxes

from .AbstractWidget import AbstractWidget


class ReviewForm(AbstractWidget):
    data_captured = QtCore.Signal(str, dict)

    def __init__(self, cfg: config.ReviewForm, parent=None):

        self.cfg = cfg

        self._checkbox_widgets: dict[str, QtWidgets.QCheckBox] | None = None
        self._comments_widget: QtWidgets.QTextEdit | None = None

        super().__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

    def create_checkbox_widgets(self, df: pd.DataFrame | None = None):
        if self._checkbox_widgets is not None:
            for w in self._checkbox_widgets.values():
                w.deleteLater()

        if df is None:
            checkboxes = self.cfg.default_checkboxes
        else:
            checkboxes = get_checkboxes(df, self.cfg.default_checkboxes)

        if checkboxes is None:
            return {}

        checkbox_widgets = {}
        for i, (cname, label) in enumerate(checkboxes.items()):
            checkbox_widgets[cname] = QtWidgets.QCheckBox(label, self)

        self._checkbox_widgets = checkbox_widgets

    def init_ui(self):
        self.create_checkbox_widgets()
        self._comments_widget = QtWidgets.QTextEdit(self)

    def connect(self):
        pass

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())

    def populate(self):
        for i, widget in enumerate(self._checkbox_widgets.values()):
            self.layout().addWidget(widget, i + 1, 1, 1, 1)

        self.layout().addWidget(QtWidgets.QLabel('Comments:', self), len(self._checkbox_widgets) + 1, 1, 1, 1)
        self.layout().addWidget(self._comments_widget, len(self._checkbox_widgets) + 2, 1, 1, 1)

    @QtCore.Slot(pd.DataFrame)
    def load_project(self, df: pd.DataFrame):
        self.setEnabled(True)

        self.create_checkbox_widgets(df=df)
        self.repopulate()

    @QtCore.Slot(AppData)
    def load_object(self, rd: AppData):
        self._comments_widget.setText(rd.df.at[rd.id, 'comment'])
        for cname, widget in self._checkbox_widgets.items():
            widget.setChecked(rd.df.at[rd.id, cname])

    @QtCore.Slot()
    def capture(self):
        comment = self._comments_widget.toPlainText()
        checkboxes = {cname: widget.isChecked() for cname, widget in self._checkbox_widgets.items()}

        self.data_captured.emit(comment, checkboxes)
