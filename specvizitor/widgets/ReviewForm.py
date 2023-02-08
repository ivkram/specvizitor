from pyqtgraph.Qt import QtWidgets


class ReviewForm(QtWidgets.QGroupBox):
    def __init__(self, config, parent=None):
        self._config = config

        self._j = None
        self._cat = None
        self._comments = None

        super().__init__(parent)
        self.setTitle('Review Form')
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        # add a multi-line text editor for writing comments
        self._comments_widget = QtWidgets.QTextEdit()
        grid.addWidget(QtWidgets.QLabel('Comments:'), 5, 3, 1, 4)
        grid.addWidget(self._comments_widget, 6, 3, 1, 4)

        self.setLayout(grid)

    def load_object(self, j):
        if self._j is not None:
            self._comments[self._j] = self._comments_widget.toPlainText()

        self._j = j

        self._comments_widget.setText(self._comments[self._j])

    def load_project(self, cat):
        self._cat = cat
        self._comments = ["" for _ in range(len(self._cat))]

        self.setEnabled(True)
