import pathlib

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from ..utils.widgets import FileBrowser


class NewFile(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("New Project")

        layout = QtWidgets.QVBoxLayout()

        self._location_browser = FileBrowser("Project Location:",
                                             default_path=str(pathlib.Path().resolve() / 'SpecvizitorProject'),
                                             button_text="Browse...",
                                             mode=FileBrowser.OpenDirectory)
        layout.addWidget(self._location_browser)

        self._cat_browser = FileBrowser("Photometric Catalogue:", mode=FileBrowser.OpenFile)
        layout.addWidget(self._cat_browser)

        self._data_browser = FileBrowser("Grizli Data Folder:", mode=FileBrowser.OpenDirectory)
        layout.addWidget(self._data_browser)

        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.setLayout(layout)
        # self.setModal(True)
    
    def accept(self):
        location = self._location_browser.text()
        if pathlib.Path(location):
            pass

        super().accept()
