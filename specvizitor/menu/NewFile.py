import logging
import pathlib

from astropy.table import Table

from pyqtgraph.Qt import QtWidgets, QtCore

from ..utils import FileBrowser
from ..utils.config import save_config
from ..io.loader import load_cat


from ..utils.logs import qlog


logger = logging.getLogger('specvizitor')


class NewFile(QtWidgets.QDialog):
    project_created = QtCore.pyqtSignal(str, Table)

    def __init__(self, config: dict, parent=None):
        self._config = config

        super().__init__(parent)
        self.setWindowTitle("New Project")

        layout = QtWidgets.QVBoxLayout()

        self._browsers = {
            'output': FileBrowser(title='Output File:', filename_extensions='CSV Files (*.csv)',
                                  mode=FileBrowser.SaveFile, default_path=pathlib.Path().resolve() / 'Untitled.csv',
                                  parent=self),
            'cat': FileBrowser(title='Catalogue:', filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                               default_path=self._config['loader']['cat']['filename'], parent=self),
            'data': FileBrowser(title='Data Folder:',  mode=FileBrowser.OpenDirectory,
                                default_path=self._config['loader']['data']['dir'], parent=self)
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
    def accept(self):
        # validate the input
        for b in self._browsers.values():
            if not b.filled() or not b.exists():
                return

        # load the catalogue
        translate = self._config['loader']['cat'].get('translate')
        data_folder = self._browsers['data'].path if self._filter_check_box.isChecked() else None

        cat = load_cat(self._browsers['cat'].path, translate=translate, data_folder=data_folder)
        if cat is None:
            return

        logger.handlers.clear()

        # update the user configuration file
        self._config['loader']['data']['dir'] = self._browsers['data'].path
        self._config['loader']['cat']['filename'] = self._browsers['cat'].path
        save_config(self._config)

        logger.info('New project created')
        super().accept()

        self.project_created.emit(self._browsers['output'].path, cat)
