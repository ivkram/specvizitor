from pyqtgraph.Qt import QtWidgets


class ReviewForm(QtWidgets.QGroupBox):
    def __init__(self, config, parent=None):
        self._config = config

        self._j = None
        self._df = None
        self._cat = None


        super().__init__(parent)
        self.setTitle('Review Form')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        self.setEnabled(False)

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

    def load_project(self, df, cat):
        self._df = df
        self._cat = cat

        self.setEnabled(True)
