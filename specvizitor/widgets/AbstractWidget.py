from pyqtgraph.Qt import QtWidgets


class AbstractWidget(QtWidgets.QGroupBox):
    def __init__(self, config, parent=None):
        self._config = config

        self._j = None
        self._df = None
        self._cat = None

        super().__init__(parent)
        self.setEnabled(False)

    def load_project(self, df, cat):
        self._df = df
        self._cat = cat
