from pyqtgraph.Qt import QtWidgets

from ..runtime import RuntimeData
from .AbstractWidget import AbstractWidget


class ReviewForm(QtWidgets.QGroupBox, AbstractWidget):
    def __init__(self, rd: RuntimeData, parent=None):
        self.cfg = rd.config.review_form
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        self.setTitle('Review Form')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        grid = QtWidgets.QGridLayout()

        # add checkboxes
        self._checkboxes = {}

        if self.cfg.checkboxes:
            for i, (cname, label) in enumerate(self.cfg.checkboxes.items()):
                widget = QtWidgets.QCheckBox(label)
                self._checkboxes[cname] = widget
                grid.addWidget(widget, i + 1, 1, 1, 1)

        # add a multi-line text editor for writing comments
        self._comments_widget = QtWidgets.QTextEdit()
        grid.addWidget(QtWidgets.QLabel('Comments:'), len(self._checkboxes) + 1, 1, 1, 1)
        grid.addWidget(self._comments_widget, len(self._checkboxes) + 2, 1, 1, 1)

        self.setLayout(grid)

    def dump(self):
        self.rd.df['comment'][self.rd.id] = self._comments_widget.toPlainText()

    def load_object(self):
        self._comments_widget.setText(self.rd.df['comment'][self.rd.id])
        # for i, (cname, widget) in enumerate(self._checkboxes):
        #     widget.setCheckState()
