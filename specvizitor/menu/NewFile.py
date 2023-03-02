import logging
import pathlib

from qtpy import QtWidgets

from ..runtime.appdata import AppData
from ..utils import FileBrowser
from ..io.catalogue import load_cat, create_cat
from ..io.viewer_data import get_ids_from_dir
from ..utils.logs import qlog


logger = logging.getLogger(__name__)


class NewFile(QtWidgets.QDialog):
    def __init__(self, rd: AppData, parent=None):
        self.rd = rd

        super().__init__(parent)
        self.setWindowTitle("Create a New Inspection File")

        layout = QtWidgets.QVBoxLayout()
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

        # add a file browser for specifying the output file
        layout.addWidget(self._browsers['output'])

        # add a file browser for specifying the data directory
        layout.addWidget(self._browsers['data'])

        # add radio buttons for choosing between creating a new catalogue and loading an existing one
        self._cat_factory_group = QtWidgets.QButtonGroup()
        self._cat_factory_group.buttonToggled.connect(self.update_cat_factory_state)

        self._create_cat_radio_button = QtWidgets.QRadioButton('Create a new catalogue')
        self._cat_factory_group.addButton(self._create_cat_radio_button)

        self._load_cat_radio_button = QtWidgets.QRadioButton('Load an existing catalogue')
        self._cat_factory_group.addButton(self._load_cat_radio_button)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._create_cat_radio_button)
        sub_layout.addWidget(self._load_cat_radio_button)
        layout.addLayout(sub_layout)

        # add a horizontal separator
        self.separator = QtWidgets.QFrame()
        self.separator.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(self.separator)

        # add a file browser for specifying the catalogue
        layout.addWidget(self._browsers['cat'])
        self._browsers['cat'].setHidden(True)

        # add a checkbox for specifying the catalogue loader mode
        self._filter_check_box = QtWidgets.QCheckBox(
            'Filter the catalogue using a list of IDs extracted from the data directory')
        self._filter_check_box.setChecked(False)
        self._filter_check_box.setHidden(True)
        self._filter_check_box.stateChanged.connect(self.update_id_pattern_widget_state)
        layout.addWidget(self._filter_check_box)

        # add a line edit for specifying the ID pattern that will be used to parse the filenames in the data directory
        self._id_pattern_label = QtWidgets.QLabel('ID pattern:')
        self._id_pattern_label.setToolTip('A regular expression used to match the source IDs while scanning '
                                          'the data directory. If more than\none ID is matched to the pattern for a '
                                          'given filename, only the longest match will be returned.')
        self._id_pattern_label.setFixedWidth(120)
        self._id_pattern_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self._id_pattern = QtWidgets.QLineEdit(self.rd.config.loader.data.id_pattern)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._id_pattern_label)
        sub_layout.addWidget(self._id_pattern)
        layout.addLayout(sub_layout)

        # add OK/Cancel buttons
        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self._button_box)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        # set the state of the radio buttons
        self._create_cat_radio_button.setChecked(True)

        self.setLayout(layout)

    @qlog
    def get_catalogue(self):
        # validate the input
        for b in self._browsers.values():
            if not b.isHidden() and (not b.is_filled() or not b.exists()):
                return

        # create a new catalogue if necessary
        if self._browsers['cat'].isHidden():
            ids = get_ids_from_dir(self._browsers['data'].path, self._id_pattern.text())
            if ids is None:
                return
            return create_cat(ids)

        # otherwise, load an existing catalogue
        translate = self.rd.config.loader.cat.translate
        data_dir = self._browsers['data'].path if self._filter_check_box.isChecked() else None

        return load_cat(self._browsers['cat'].path, translate=translate, data_dir=data_dir,
                        id_pattern=self.rd.config.loader.data.id_pattern)

    def accept(self):
        cat = self.get_catalogue()
        if cat is None:
            return

        self.rd.cat = cat
        self.rd.output_path = pathlib.Path(self._browsers['output'].path)

        # update the user configuration file
        self.rd.config.loader.data.dir = self._browsers['data'].path
        if not self._browsers['cat'].isHidden():
            self.rd.config.loader.cat.filename = self._browsers['cat'].path
        if not self._id_pattern.isHidden():
            self.rd.config.loader.data.id_pattern = self._id_pattern.text()
        self.rd.config.save(self.rd.config_file)

        self.rd.create()

        super().accept()

    def update_cat_factory_state(self):
        if self._create_cat_radio_button.isChecked():
            self._browsers['cat'].setHidden(True)
            self._filter_check_box.setHidden(True)

            self._id_pattern.setHidden(False)
            self._id_pattern_label.setHidden(False)
        else:
            self._browsers['cat'].setHidden(False)
            self._filter_check_box.setHidden(False)

            self.update_id_pattern_widget_state()

    def update_id_pattern_widget_state(self):
        if self._filter_check_box.isChecked():
            self._id_pattern.setHidden(False)
            self._id_pattern_label.setHidden(False)
        else:
            self._id_pattern.setHidden(True)
            self._id_pattern_label.setHidden(True)
