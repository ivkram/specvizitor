from qtpy import QtWidgets, QtCore

from ..appdata import AppData
from ..config import config
from ..io.output import get_checkboxes

from .AbstractWidget import AbstractWidget


class ReviewForm(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ReviewForm, parent=None):
        super().__init__(layout=QtWidgets.QGridLayout(), parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)

        # create checkboxes
        self._checkboxes = self.create_checkbox_widgets(self.cfg.default_checkboxes)

        # create a multi-line text editor for writing comments
        self._comments_widget = QtWidgets.QTextEdit(parent=self)

        self.init_ui()

    def create_checkbox_widgets(self, checkboxes: dict[str, str] | None) -> dict[str, QtWidgets.QCheckBox]:
        if checkboxes is None:
            return {}

        checkbox_widgets = {}
        for i, (cname, label) in enumerate(checkboxes.items()):
            checkbox_widgets[cname] = QtWidgets.QCheckBox(label, parent=self)

        return checkbox_widgets

    def init_ui(self):
        for i, widget in enumerate(self._checkboxes.values()):
            self.layout().addWidget(widget, i + 1, 1, 1, 1)

        self.layout().addWidget(QtWidgets.QLabel('Comments:', parent=self), len(self._checkboxes) + 1, 1, 1, 1)
        self.layout().addWidget(self._comments_widget, len(self._checkboxes) + 2, 1, 1, 1)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

        for w in self._checkboxes.values():
            w.deleteLater()
        self._checkboxes = self.create_checkbox_widgets(get_checkboxes(self.rd.df, self.cfg.default_checkboxes))
        self.reset_layout()

    @QtCore.Slot(AppData)
    def load_object(self, rd: AppData):
        self._comments_widget.setText(rd.df.at[rd.id, 'comment'])
        for cname, widget in self._checkboxes.items():
            widget.setChecked(rd.df.at[rd.id, cname])

    def dump(self):
        self.rd.df.at[self.rd.id, 'comment'] = self._comments_widget.toPlainText()
        for cname, widget in self._checkboxes.items():
            self.rd.df.at[self.rd.id, cname] = widget.isChecked()
