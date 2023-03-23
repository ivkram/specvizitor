from qtpy import QtWidgets, QtCore

import logging
import pathlib

from ..config import config
from ..io.catalogue import read_cat, create_cat, cat_browser
from ..io.viewer_data import get_ids_from_dir, data_browser
from ..utils.logs import qlog
from ..widgets.FileBrowser import FileBrowser

logger = logging.getLogger(__name__)


class NewFile(QtWidgets.QDialog):
    output_path_selected = QtCore.Signal(pathlib.Path)
    catalogue_changed = QtCore.Signal(object)

    def __init__(self, cfg: config.Config, parent=None):
        self.cfg = cfg

        self._browsers: dict[str, FileBrowser] | None = None
        self._cat_factory_group: QtWidgets.QButtonGroup | None = None
        self._create_cat_radio_button: QtWidgets.QRadioButton | None = None
        self._load_cat_radio_button: QtWidgets.QRadioButton | None = None
        self._separator: QtWidgets.QFrame | None = None
        self._filter_check_box: QtWidgets.QCheckBox | None = None
        self._id_pattern_label: QtWidgets.QLabel | None = None
        self._id_pattern: QtWidgets.QLineEdit | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setWindowTitle("Create a New Inspection File")

        self.init_ui()
        self.set_layout()
        self.populate()

        self.setFixedWidth(self.layout().sizeHint().width())

    def init_ui(self):
        width = 135
        self._browsers = {
            'output': FileBrowser(filename_extensions='CSV Files (*.csv)',
                                  mode=FileBrowser.SaveFile, default_path=pathlib.Path().resolve() / 'Untitled.csv',
                                  title='Output File:', title_width=width, parent=self),
            'data': data_browser(self.cfg.data.dir, title='Data Source:', title_width=width, parent=self),
            'cat': cat_browser(self.cfg.catalogue.filename, title='Catalogue:', title_width=width, parent=self)
        }

        # add radio buttons for choosing between creating a new catalogue and loading an existing one
        self._cat_factory_group = QtWidgets.QButtonGroup(parent=self)
        self._cat_factory_group.buttonToggled.connect(self.update_cat_factory_state)

        self._create_cat_radio_button = QtWidgets.QRadioButton('Create a new catalogue', self)
        self._cat_factory_group.addButton(self._create_cat_radio_button)

        self._load_cat_radio_button = QtWidgets.QRadioButton('Load an existing catalogue', self)
        self._cat_factory_group.addButton(self._load_cat_radio_button)

        # create a horizontal separator
        self._separator = QtWidgets.QFrame(parent=self)
        self._separator.setFrameShape(QtWidgets.QFrame.HLine)

        # add a checkbox for specifying the catalogue loader mode
        self._filter_check_box = QtWidgets.QCheckBox(
            'Filter the catalogue using a list of IDs extracted from the data directory', self)

        self._filter_check_box.stateChanged.connect(self.update_id_pattern_widget_state)

        # add a line edit for specifying the ID pattern that will be used to parse the filenames in the data directory
        self._id_pattern_label = QtWidgets.QLabel('ID pattern:', self)
        self._id_pattern_label.setToolTip('A regular expression used to match the object IDs during the scan of '
                                          'the data directory. If more than\none ID is matched to the pattern for a '
                                          'given filename, only the longest match will be returned.')
        self._id_pattern_label.setFixedWidth(120)
        self._id_pattern_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self._id_pattern = QtWidgets.QLineEdit(self.cfg.data.id_pattern, self)

        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # add OK/Cancel buttons
        self._button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
                                                      self)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        # set the state of radio buttons and checkboxes
        self._filter_check_box.setChecked(False)
        self._load_cat_radio_button.setChecked(True)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(20)
        self.setFixedHeight(450)

    def populate(self):
        # add a file browser for specifying the output file
        self.layout().addWidget(self._browsers['output'])

        # add a file browser for specifying the data directory
        self.layout().addWidget(self._browsers['data'])

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._load_cat_radio_button)
        sub_layout.addWidget(self._create_cat_radio_button)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._separator)

        # add a file browser for specifying the catalogue
        self.layout().addWidget(self._browsers['cat'])

        self.layout().addWidget(self._filter_check_box)

        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addWidget(self._id_pattern_label)
        sub_layout.addWidget(self._id_pattern)
        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._spacer)
        self.layout().addWidget(self._button_box)

    @qlog
    def validate(self) -> bool:
        for b in self._browsers.values():
            if not b.isHidden() and (not b.is_filled(verbose=True) or not b.exists(verbose=True)):
                return False
        return True

    @qlog
    def get_catalogue(self):
        # create a new catalogue if necessary
        if self._browsers['cat'].isHidden():
            ids = get_ids_from_dir(self._browsers['data'].path, self._id_pattern.text())
            if ids is None:
                return
            return create_cat(ids)

        # otherwise, load an existing catalogue
        data_dir = self._browsers['data'].path if self._filter_check_box.isChecked() else None

        return read_cat(self._browsers['cat'].path, translate=self.cfg.catalogue.translate, data_dir=data_dir,
                        id_pattern=self.cfg.data.id_pattern)

    def accept(self):
        if not self.validate():
            return

        cat = self.get_catalogue()
        if cat is None:
            return

        self.catalogue_changed.emit(cat)
        self.output_path_selected.emit(pathlib.Path(self._browsers['output'].path))

        # update the user configuration file
        self.cfg.data.dir = self._browsers['data'].path
        if not self._browsers['cat'].isHidden():
            self.cfg.catalogue.filename = self._browsers['cat'].path
        else:
            self.cfg.catalogue.filename = None
        if not self._id_pattern.isHidden():
            self.cfg.data.id_pattern = self._id_pattern.text()
        self.cfg.save()

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
