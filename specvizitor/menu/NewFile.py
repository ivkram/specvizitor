import logging
import pathlib

from astropy.table import Table

from pyqtgraph.Qt import QtWidgets, QtCore

from ..utils.widgets import FileBrowser
from ..io.loader import load_cat


class NewFile(QtWidgets.QDialog):
    project_created = QtCore.pyqtSignal(str, Table)

    def __init__(self, config: dict, parent=None):
        self._config = config

        super().__init__(parent)
        self.setWindowTitle("New Project")

        layout = QtWidgets.QVBoxLayout()

        self._project_browser = FileBrowser(self, title='Project:',
                                            filename_extensions='SpecVizitor Files (*.svz)',
                                            mode=FileBrowser.SaveFile,
                                            default_path=str(pathlib.Path().resolve() / 'Untitled.svz'))
        layout.addWidget(self._project_browser)

        self._cat_browser = FileBrowser(self, title='Catalogue:', mode=FileBrowser.OpenFile,
                                        filename_extensions='FITS Files (*.fits)')
        layout.addWidget(self._cat_browser)

        self._data_browser = FileBrowser(self, title='Data Folder:', mode=FileBrowser.OpenDirectory)
        layout.addWidget(self._data_browser)

        self._filter_check_box = QtWidgets.QCheckBox(
            'Filter the input catalogue based on a list of IDs retrieved from the data folder', checked=True)
        layout.addWidget(self._filter_check_box)

        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self._button_box)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self.setLayout(layout)

        self._cat_browser._line_edit.setText('/home/rainnfog/Documents/research/master/data/cats/FRESCO/gds-grizli-v5.1-fix_phot_apcorr.fits')
        self._data_browser._line_edit.setText('/home/rainnfog/Documents/research/master/data/test/')
    
    def accept(self):
        project_filename = self._project_browser.get_path()
        cat_filename = self._cat_browser.get_path()
        data_dirname = self._data_browser.get_path()

        for i, path in enumerate((project_filename, cat_filename, data_dirname)):
            if not path:
                logging.error('Field #{} is empty'.format(i + 1))
                QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                      'Some fields are empty', parent=self).show()
                return

        project_filename = pathlib.Path(project_filename).resolve()
        cat_filename = pathlib.Path(cat_filename).resolve()
        data_dirname = pathlib.Path(data_dirname).resolve()

        if not project_filename.parent.exists():
            logging.error('Project root directory `{}` not found'.format(project_filename.parent))
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'The project root directory does not exist', parent=self).show()
            return
        if not project_filename.suffix == '.svz':
            logging.error('Project filename extension `{}` is invalid'.format(project_filename.suffix))
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'The project filename extension must be `.svz`', parent=self).show()
            return

        if not cat_filename.exists():
            logging.error('Catalogue `{}` not found'.format(cat_filename))
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'The catalogue does not exist', parent=self).show()
            return
        if cat_filename.suffix not in ('.fits',):
            logging.error('The catalogue format `{}` is invalid'.format(cat_filename.suffix))
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'The catalogue format is invalid. Currently supported formats: .fits',
                                  parent=self).show()
            return

        if not data_dirname.exists():
            logging.error('Data folder `{}` not found'.format(data_dirname))
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'The data folder does not exist', parent=self).show()
            return

        # loading the catalogue
        if self._filter_check_box.isChecked():
            cat = load_cat(cat_filename, **self._config['cat'], data_folder=data_dirname)
        else:
            cat = load_cat(cat_filename, **self._config['cat'])

        if cat is None:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, 'Specvizitor Message',
                                  'An error occurred when loading the catalogue', parent=self).show()
            return

        self._config['data']['dir'] = str(data_dirname)
        self.project_created.emit(str(project_filename), cat)

        # TODO: cache cat_filename

        super().accept()
