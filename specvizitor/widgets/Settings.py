import numpy as np
from qtpy import QtWidgets, QtCore

from abc import abstractmethod
import logging

from ..config import config, CONFIG_DIR
from ..config.spectral_lines import SpectralLineData
from ..io.catalog import Catalog, cat_browser
from ..io.viewer_data import data_browser
from ..utils.logs import qlog
from ..utils.widgets import AbstractWidget, FileBrowser, Section, ParamTable

logger = logging.getLogger(__name__)


class SettingsWidget(AbstractWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout().setAlignment(QtCore.Qt.AlignTop)
        self.setFixedHeight(500)

    @abstractmethod
    def collect(self) -> bool:
        pass

    @abstractmethod
    def accept(self):
        pass


class AppearanceWidget(SettingsWidget):
    appearance_changed = QtCore.Signal(bool)

    THEMES = ('light', 'dark')

    def __init__(self, cfg: config.Appearance, parent=None):
        self.cfg = cfg

        self._theme_label: QtWidgets.QLabel | None = None
        self._theme_combobox: QtWidgets.QComboBox | None = None
        self._antialiasing_checkbox: QtWidgets.QCheckBox | None = None

        self._new_theme: str | None = None
        self._new_antialiasing: bool | None = None

        self._theme_changed: bool = False
        self._appearance_changed: bool = False

        super().__init__(parent=parent)

    def init_ui(self):
        self._theme_label = QtWidgets.QLabel("Theme:", self)
        self._theme_label.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self._theme_combobox = QtWidgets.QComboBox(self)
        self._theme_combobox.addItems(self.THEMES)
        self._theme_combobox.setCurrentIndex(self.THEMES.index(self.cfg.theme))
        self._theme_combobox.setFixedWidth(200)

        self._antialiasing_checkbox = QtWidgets.QCheckBox("Antialiasing", self)
        self._antialiasing_checkbox.setChecked(self.cfg.antialiasing)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(20)

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setAlignment(QtCore.Qt.AlignLeft)
        sub_layout.addWidget(self._theme_label)
        sub_layout.addWidget(self._theme_combobox)

        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._antialiasing_checkbox)

    def collect(self) -> bool:
        self._new_theme = self._theme_combobox.currentText()
        self._new_antialiasing = self._antialiasing_checkbox.isChecked()

        self._theme_changed = self._new_theme != self.cfg.theme
        if self._theme_changed or self._new_antialiasing != self.cfg.antialiasing:
            self._appearance_changed = True
        else:
            self._appearance_changed = False

        return True

    def accept(self):
        self.cfg.theme = self._new_theme
        self.cfg.antialiasing = self._new_antialiasing

        if self._appearance_changed:
            self.appearance_changed.emit(self._theme_changed)


def column_aliases_table_factory(translate: dict[str, list[str]], parent=None) -> ParamTable:
    header = ['Column', 'Aliases']
    data = [[cname, ','.join(cname_aliases)] for cname, cname_aliases in translate.items()]
    regex_pattern = [r'^\s*$', r'^\s*$']
    is_unique = [True, False]

    return ParamTable(header=header, data=data, name='Column Aliases', regex_pattern=regex_pattern,
                      is_unique=is_unique, remember_deleted=False, parent=parent)


class CatalogueWidget(SettingsWidget):
    data_requested = QtCore.Signal()
    catalog_changed = QtCore.Signal(object)

    def __init__(self, cat: Catalog, cfg: config.Catalogue, parent=None):
        self._old_cat = cat
        self.cfg = cfg

        self._new_cat: Catalog | None = None
        self._new_cat_filename: str | None = None
        self._new_translate = None

        self._catalog_changed = False
        self._aliases_changed = False

        self._browser: FileBrowser | None = None
        self._aliases_section: Section | None = None
        self._aliases_table: ParamTable | None = None

        super().__init__(parent=parent)

    def init_ui(self):
        self._browser = cat_browser(self.cfg.filename, title='Filename:', parent=self)

        self._aliases_section = Section("Column aliases", parent=self)
        self._aliases_table = column_aliases_table_factory(self.cfg.translate if self.cfg.translate else {},
                                                           parent=self)

        self.data_requested.connect(self._aliases_table.collect)
        self._aliases_table.data_collected.connect(self.save_aliases)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._browser)

        sub_layout = QtWidgets.QVBoxLayout()
        sub_layout.addWidget(self._aliases_table)
        self._aliases_section.set_layout(sub_layout)
        self.layout().addWidget(self._aliases_section)

    def collect(self) -> bool:
        self.data_requested.emit()

        if self._browser.is_filled():
            self._new_cat_filename = self._browser.path
            self._catalog_changed = self.cfg.filename is None or self._new_cat_filename != self.cfg.filename
        else:
            self._new_cat_filename = None
            self._catalog_changed = self.cfg.filename is not None

        if self._catalog_changed:
            if not self._browser.exists(verbose=True):
                return False

            if self._new_cat_filename is not None:
                self._new_cat = Catalog.read(self._new_cat_filename, translate=self._new_translate)
                if not self._new_cat:
                    return False
            else:
                self._new_cat = None

            return True

        if self._aliases_changed and self._old_cat is not None:
            self._new_cat = self._old_cat.update_translate(self._new_translate)
            if self._new_cat is None:
                return False

        return True

    @QtCore.Slot(list)
    def save_aliases(self, table_data: list[tuple[str, str]]):
        translate = {}
        for alias in table_data:
            translate[alias[0]] = alias[1].split(',')

        if self.cfg.translate.keys() == translate.keys() and list(self.cfg.translate.values()) == list(translate.values()):
            self._aliases_changed = False
        else:
            self._aliases_changed = True

        self._new_translate = translate

    def accept(self):
        self.cfg.translate = self._new_translate

        if self._catalog_changed:
            self.cfg.filename = self._new_cat_filename

        if self._catalog_changed or (self._aliases_changed and self._old_cat is not None):
            self.catalog_changed.emit(self._new_cat)


def image_table_factory(images: dict[str, config.Image], parent=None) -> ParamTable:
    header = ['Label', 'Path', 'WCS Source']
    data = [[label, img.filename, img.wcs_source] for label, img in images.items()]
    regex_pattern = [r'^\s*$', r'^\s*$', None]
    is_unique = [True, False, False]
    is_browser = [False, True, True]

    return ParamTable(header=header, data=data, name='Image', regex_pattern=regex_pattern,
                      is_unique=is_unique, remember_deleted=False, is_browser=is_browser, parent=parent)


class DataSourceWidget(SettingsWidget):
    data_requested = QtCore.Signal()
    images_changed = QtCore.Signal()

    def __init__(self, cfg: config.DataSources, parent=None):
        self.cfg = cfg

        self._browser: FileBrowser | None = None
        self._images_section: Section | None = None
        self._image_table: ParamTable | None = None

        self._new_dir: str | None = None
        self._new_images: dict[config.Image] | None = None

        self._images_changed: bool = False

        super().__init__(parent=parent)

    def init_ui(self):
        self._browser = data_browser(self.cfg.dir, title="Directory:", parent=self)

        self._images_section = Section("Images", parent=self)
        self._image_table = image_table_factory(self.cfg.images, self)

        self.data_requested.connect(self._image_table.collect)
        self._image_table.data_collected.connect(self.save_images)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._browser)

        sub_layout = QtWidgets.QVBoxLayout()
        sub_layout.addWidget(self._image_table)
        self._images_section.set_layout(sub_layout)
        self.layout().addWidget(self._images_section)

    def collect(self) -> bool:
        self.data_requested.emit()

        if not self._browser.is_filled(verbose=True) or not self._browser.exists(verbose=True):
            return False

        self._new_dir = self._browser.path
        return True

    @QtCore.Slot(list)
    def save_images(self, table_data: list[tuple[str, str, str]]):
        images = {}
        for img in table_data:
            images[img[0]] = config.Image(filename=img[1], wcs_source=img[2] if img[2] else None)

        old_data = [[label, img.filename, img.wcs_source] for label, img in self.cfg.images.items()] if self.cfg.images else []
        self._images_changed = True if old_data != table_data else False

        self._new_images = images

    def accept(self):
        self.cfg.dir = self._new_dir
        self.cfg.images = self._new_images

        if self._images_changed:
            self.images_changed.emit()


def spectral_lines_table_factory(wavelengths: dict[str, float], parent=None) -> ParamTable:
    header = ['Line', 'Wavelength']
    data = [[line, str(wave)] for line, wave in wavelengths.items()]
    regex_pattern = [r'^\s*$', r'(?!([0-9]+([.][0-9]*)?|[.][0-9]+)$)']
    is_unique = [True, False]

    return ParamTable(header=header, data=data, name='Spectral Line', regex_pattern=regex_pattern,
                      is_unique=is_unique, remember_deleted=False, parent=parent)


class DataViewerWidget(SettingsWidget):
    data_requested = QtCore.Signal()
    spectral_lines_changed = QtCore.Signal()

    def __init__(self, cfg: SpectralLineData, parent=None):
        self.cfg = cfg

        self._lines_section: Section | None = None
        self._lines_table: ParamTable | None = None

        self._new_wavelengths: dict[str, float] | None = None

        self._wavelengths_changed: bool = False

        super().__init__(parent=parent)

    def init_ui(self):
        self._lines_section = Section("Spectral lines", parent=self)
        self._lines_table = spectral_lines_table_factory(self.cfg.wavelengths, self)

        self.data_requested.connect(self._lines_table.collect)
        self._lines_table.data_collected.connect(self.save_lines)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        sub_layout = QtWidgets.QVBoxLayout()
        sub_layout.addWidget(self._lines_table)
        self._lines_section.set_layout(sub_layout)
        self.layout().addWidget(self._lines_section)

    def collect(self) -> bool:
        self.data_requested.emit()
        return True

    @QtCore.Slot(list)
    def save_lines(self, table_data: list[tuple[str, str]]):
        wavelengths = {}
        for line in table_data:
            wavelengths[line[0]] = float(line[1])

        self._wavelengths_changed = False
        if not self.cfg.wavelengths.keys() == wavelengths.keys():
            self._wavelengths_changed = True
        elif not np.isclose(np.fromiter(wavelengths.values(), dtype=float),
                            np.fromiter(self.cfg.wavelengths.values(), dtype=float)).all():
            self._wavelengths_changed = True

        self._new_wavelengths = wavelengths

    def accept(self):
        self.cfg.wavelengths = self._new_wavelengths

        if self._wavelengths_changed:
            self.spectral_lines_changed.emit()


class Settings(QtWidgets.QDialog):
    appearance_changed = QtCore.Signal()
    catalogue_changed = QtCore.Signal(object)
    data_source_changed = QtCore.Signal()
    spectral_lines_changed = QtCore.Signal()

    restart_requested = QtCore.Signal()

    def __init__(self, cat: Catalog, cfg: config.Config, spectral_lines: SpectralLineData, parent=None):
        self._old_cat = cat
        self._cfg = cfg
        self._spectral_lines = spectral_lines

        self._restart_required: bool = False

        self._tab_widget: QtWidgets.QTabWidget | None = None
        self._tabs: dict[str, SettingsWidget] | None = None

        self._info_label: QtWidgets.QLabel | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.init_ui()
        self.set_layout()
        self.populate()

    def create_tabs(self):
        self._tabs = {'Appearance': AppearanceWidget(self._cfg.appearance, self),
                      'Catalogue': CatalogueWidget(self._old_cat, self._cfg.catalogue, self),
                      'Data Source': DataSourceWidget(self._cfg.data, self),
                      'Data Viewer': DataViewerWidget(self._spectral_lines, self)}
        self._tabs['Appearance'].appearance_changed.connect(self._appearance_changed_action)
        self._tabs['Catalogue'].catalog_changed.connect(self.catalogue_changed.emit)
        self._tabs['Data Source'].images_changed.connect(self.data_source_changed.emit)
        self._tabs['Data Viewer'].spectral_lines_changed.connect(self.spectral_lines_changed.emit)

    def add_tabs(self):
        for name, t in self._tabs.items():
            self._tab_widget.addTab(t, name)

    def init_ui(self):
        self._tab_widget = QtWidgets.QTabWidget(self)

        self.create_tabs()
        self.add_tabs()

        self._info_label = QtWidgets.QLabel(f"Advanced settings: {CONFIG_DIR}", self)
        self._info_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        # add OK/Cancel buttons
        self._button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(20)

    def populate(self):
        self.layout().addWidget(self._tab_widget)
        self.layout().addWidget(self._info_label)
        self.layout().addWidget(self._button_box)

    @QtCore.Slot(bool)
    def _appearance_changed_action(self, theme_changed: bool):
        self._restart_required = self._restart_required or theme_changed
        self.appearance_changed.emit()

    @qlog
    def collect(self) -> bool:
        for t in self._tabs.values():
            if not t.collect():
                return False
        return True

    def accept(self):
        self._restart_required = False

        if not self.collect():
            return

        for t in self._tabs.values():
            t.accept()

        self._cfg.save()
        self._spectral_lines.save()

        restart_requested = False
        if self._restart_required:
            msg_box = QtWidgets.QMessageBox(self)
            ans = msg_box.question(self, '', f"Restart required to apply changes. Restart now?",
                                   msg_box.Yes | msg_box.No)
            if ans == msg_box.Yes:
                restart_requested = True

        super().accept()

        if restart_requested:
            self.restart_requested.emit()
