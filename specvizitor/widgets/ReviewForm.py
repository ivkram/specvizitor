from pyqtgraph.Qt import QtWidgets

from .AbstractWidget import AbstractWidget


class ReviewForm(AbstractWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setTitle('Review Form')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)

        grid = QtWidgets.QGridLayout()

        # add checkboxes
        self._checkboxes = {}
        for i, (cname, label) in enumerate(self._config['checkboxes'].items()):
            checkbox_widget = QtWidgets.QCheckBox(label)
            self._checkboxes[cname] = checkbox_widget
            grid.addWidget(checkbox_widget, i + 1, 1, 1, 1)

        # add a multi-line text editor for writing comments
        self._comments_widget = QtWidgets.QTextEdit()
        grid.addWidget(QtWidgets.QLabel('Comments:'), len(self._checkboxes) + 1, 1, 1, 1)
        grid.addWidget(self._comments_widget, len(self._checkboxes) + 2, 1, 1, 1)

        self.setLayout(grid)

    def load_object(self, j):
        if self._j is not None:
            self._df['comment'][self._cat['id'][self._j]] = self._comments_widget.toPlainText()

        self._j = j

        self._comments_widget.setText(self._df['comment'][self._cat['id'][self._j]])
        # for i, (cname, widget) in enumerate(self._checkboxes):
        #     widget.setCheckState()

    def load_project(self, *args, **kwargs):
        super().load_project(*args, **kwargs)
        self.setEnabled(True)
