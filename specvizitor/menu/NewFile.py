import logging
import pathlib

from qtpy import QtWidgets, QtGui

from ..runtime.appdata import AppData
from ..utils import FileBrowser
from ..io.catalogue import load_cat, create_cat
from ..io.viewer_data import get_id_list
from ..utils.logs import qlog


logger = logging.getLogger(__name__)


class NewFile(QtWidgets.QDialog):
    def __init__(self, rd: AppData, parent=None):
        self.rd = rd

        super().__init__(parent)
        self.setWindowTitle("Create a New Inspection File")

        layout = QtWidgets.QGridLayout()
        layout.setSpacing(20)

        self.setFixedSize(layout.sizeHint())

        self._browsers = {
            'output': FileBrowser(title='Output File:', filename_extensions='CSV Files (*.csv)',
                                  mode=FileBrowser.SaveFile, default_path=pathlib.Path().resolve() / 'Untitled.csv',
                                  parent=self),
            'data': FileBrowser(title='Data Source:', mode=FileBrowser.OpenDirectory,
                                default_path=self.rd.config.loader.data.dir, parent=self),
            'cat': FileBrowser(title='Catalogue:', filename_extensions='FITS Files (*.fits)', mode=FileBrowser.OpenFile,
                               default_path=self.rd.config.loader.cat.filename, parent=self)
        }

        layout.addWidget(self._browsers['output'], 1, 1, 1, 2)
        layout.addWidget(self._browsers['data'], 2, 1, 1, 2)

        self._cat_group = QtWidgets.QButtonGroup()
        self._cat_group.buttonToggled.connect(self.update_cat_creator_state)

        self._create_cat_radio_button = QtWidgets.QRadioButton('Create a catalogue')
        self._cat_group.addButton(self._create_cat_radio_button)
        layout.addWidget(self._create_cat_radio_button, 3, 1, 1, 1)

        self._load_cat_radio_button = QtWidgets.QRadioButton('Load an existing catalogue')
        self._cat_group.addButton(self._load_cat_radio_button)
        layout.addWidget(self._load_cat_radio_button, 3, 2, 1, 1)

        self.separator = QtWidgets.QFrame()
        self.separator.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(self.separator, 4, 1, 1, 2)

        layout.addWidget(self._browsers['cat'], 5, 1, 1, 2)
        self._browsers['cat'].setHidden(True)

        self._filter_check_box = QtWidgets.QCheckBox(
            'Filter the catalogue using a list of IDs retrieved from the data directory')
        self._filter_check_box.setChecked(True)
        self._filter_check_box.setHidden(True)
        layout.addWidget(self._filter_check_box, 6, 1, 1, 2)

        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self._button_box, 7, 1, 1, 2)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        self._create_cat_radio_button.setChecked(True)

        self.setLayout(layout)

    @qlog
    def process_input(self):
        # validate the input
        for b in self._browsers.values():
            if not b.isHidden() and (not b.filled() or not b.exists()):
                return

        if self._browsers['cat'].isHidden():
            obj_ids = get_id_list(self._browsers['data'].path, self.rd.config.loader.data.id_pattern)
            if obj_ids:
                return
            return create_cat(obj_ids)

        # load the catalogue
        translate = self.rd.config.loader.cat.translate
        data_folder = self._browsers['data'].path if self._filter_check_box.isChecked() else None

        return load_cat(self._browsers['cat'].path, translate=translate, data_dir=data_folder,
                        id_pattern=self.rd.config.loader.data.id_pattern)

    def accept(self):
        cat = self.process_input()
        if cat is None:
            return

        self.rd.cat = cat
        self.rd.output_path = pathlib.Path(self._browsers['output'].path)

        # update the user configuration file
        self.rd.config.loader.data.dir = self._browsers['data'].path
        if not self._browsers['cat'].isHidden():
            self.rd.config.loader.cat.filename = self._browsers['cat'].path
        self.rd.config.save(self.rd.config_file)

        self.rd.create()

        super().accept()

    def update_cat_creator_state(self):
        if self._create_cat_radio_button.isChecked():
            self._browsers['cat'].setHidden(True)
            self._filter_check_box.setHidden(True)
        else:
            self._browsers['cat'].setHidden(False)
            self._filter_check_box.setHidden(False)
