import logging
import pathlib

import pandas as pd

from pyqtgraph.Qt import QtWidgets, QtCore

from ..runtime import RuntimeData
from ..utils import FileBrowser
from ..io.loader import load_cat
from ..utils.logs import qlog


logger = logging.getLogger(__name__)


class NewFile(QtWidgets.QDialog):
    def __init__(self, rd: RuntimeData, parent=None):
        self.rd = rd

        super().__init__(parent)
        self.setWindowTitle("Create a New Inspection File")

        layout = QtWidgets.QVBoxLayout()

        self._browsers = {
            'output': FileBrowser(title='Output File:', filename_extensions='CSV Files (*.csv)',
                                  mode=FileBrowser.SaveFile, default_path=pathlib.Path().resolve() / 'Untitled.csv',
                                  parent=self),
            'cat': FileBrowser(title='Catalogue:', filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                               default_path=self.rd.config.loader.cat.filename, parent=self),
            'data': FileBrowser(title='Data Folder:',  mode=FileBrowser.OpenDirectory,
                                default_path=self.rd.config.loader.data.dir, parent=self)
        }

        for b in self._browsers.values():
            layout.addWidget(b)

        self._filter_check_box = QtWidgets.QCheckBox(
            'Filter the input catalogue based on a list of IDs retrieved from the data folder', checked=True)
        layout.addWidget(self._filter_check_box)

        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self._button_box)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.setLayout(layout)

    @qlog
    def process_input(self):
        # validate the input
        for b in self._browsers.values():
            if not b.filled() or not b.exists():
                return

        # load the catalogue
        translate = self.rd.config.loader.cat.translate
        data_folder = self._browsers['data'].path if self._filter_check_box.isChecked() else None

        return load_cat(self._browsers['cat'].path, translate=translate, data_folder=data_folder)

    def accept(self):
        cat = self.process_input()
        if cat is None:
            return

        self.rd.cat = cat
        self.rd.output_path = pathlib.Path(self._browsers['output'].path)

        # update the user configuration file
        self.rd.config.loader.data.dir = self._browsers['data'].path
        self.rd.config.loader.cat.filename = self._browsers['cat'].path
        self.rd.config.save(self.rd.config_file)

        self.rd.create()

        super().accept()
