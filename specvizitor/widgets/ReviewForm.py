from qtpy import QtWidgets

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.output import get_checkboxes
from .AbstractWidget import AbstractWidget


class ReviewForm(QtWidgets.QGroupBox, AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ReviewForm, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setTitle('Review Form')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        # create checkboxes
        self._checkboxes = self.create_checkbox_widgets(self.cfg.checkboxes)

        # create a multi-line text editor for writing comments
        self._comments_widget = QtWidgets.QTextEdit()

    @staticmethod
    def create_checkbox_widgets(checkboxes: dict[str, str] | None) -> dict[str, QtWidgets.QCheckBox]:
        if checkboxes is None:
            return {}

        checkbox_widgets = {}
        for i, (cname, label) in enumerate(checkboxes.items()):
            checkbox_widgets[cname] = QtWidgets.QCheckBox(label)

        return checkbox_widgets

    def init_ui(self):
        for i, widget in enumerate(self._checkboxes.values()):
            self.layout.addWidget(widget, i + 1, 1, 1, 1)

        self.layout.addWidget(QtWidgets.QLabel('Comments:'), len(self._checkboxes) + 1, 1, 1, 1)
        self.layout.addWidget(self._comments_widget, len(self._checkboxes) + 2, 1, 1, 1)

    def dump(self):
        self.rd.df.at[self.rd.id, 'comment'] = self._comments_widget.toPlainText()
        for cname, widget in self._checkboxes.items():
            self.rd.df.at[self.rd.id, cname] = widget.isChecked()

    def load_object(self):
        self._comments_widget.setText(self.rd.df.at[self.rd.id, 'comment'])
        for cname, widget in self._checkboxes.items():
            widget.setChecked(self.rd.df.at[self.rd.id, cname])

    def activate(self):
        self._checkboxes = self.create_checkbox_widgets(get_checkboxes(self.rd.df, self.cfg.checkboxes))
        self.reset_layout()

        super().activate()
