from platformdirs import user_config_dir
from qtpy import QtWidgets, QtCore

from abc import abstractmethod
import logging

from ..config import config
from ..io.catalog import Catalog, cat_browser
from ..io.viewer_data import data_browser
from ..utils.logs import qlog
from ..utils.widgets import AbstractWidget, FileBrowser, Section, ParamTable

logger = logging.getLogger(__name__)


class SettingsWidget(AbstractWidget):
    SPACING = 20

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout().setAlignment(QtCore.Qt.AlignTop)
        self.layout().setSpacing(self.SPACING)
        self.setFixedHeight(400)

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


def column_aliases_table_factory(translate: dict[str, list[str]] | None = None, parent=None) -> ParamTable:
    header = ['Column', 'Aliases']
    if translate is None:
        data = []
    else:
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
        self._aliases_table = column_aliases_table_factory(self.cfg.translate, parent=self)

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

        self._new_cat = self._old_cat
        if self._aliases_changed and self._old_cat is not None:
            if not self._new_cat.update_translate(self._new_translate):
                return False

        return True

    @QtCore.Slot(list)
    def save_aliases(self, aliases: list[tuple[str, str]]):
        translate = {}
        for alias in aliases:
            translate[alias[0]] = alias[1].split(',')

        self._aliases_changed = False
        for cname, cname_aliases in translate.items():
            if cname not in self.cfg.translate.keys() or cname_aliases != self.cfg.translate[cname]:
                self._aliases_changed = True
                break

        self._new_translate = translate if translate else None

    def accept(self):
        self.cfg.translate = self._new_translate

        if self._catalog_changed:
            self.cfg.filename = self._new_cat_filename

        if self._catalog_changed or (self._aliases_changed and self._old_cat is not None):
            self.catalog_changed.emit(self._new_cat)


class DataSourceWidget(SettingsWidget):
    def __init__(self, cfg: config.Data, parent=None):
        self.cfg = cfg

        self._browser: FileBrowser | None = None

        self._new_dir: str | None = None

        super().__init__(parent=parent)

    def init_ui(self):
        self._browser = data_browser(self.cfg.dir, title='Directory:', parent=self)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._browser)

    def collect(self) -> bool:
        if not self._browser.is_filled(verbose=True) or not self._browser.exists(verbose=True):
            return False

        self._new_dir = self._browser.path
        return True

    def accept(self):
        self.cfg.dir = self._new_dir


class Settings(QtWidgets.QDialog):
    appearance_changed = QtCore.Signal(bool)
    catalogue_changed = QtCore.Signal(object)

    def __init__(self, cat: Catalog, cfg: config.Config, parent=None):
        self._old_cat = cat
        self.cfg = cfg

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
        self._tabs = {'Appearance': AppearanceWidget(self.cfg.appearance, self),
                      'Catalogue': CatalogueWidget(self._old_cat, self.cfg.catalogue, self),
                      'Data Source': DataSourceWidget(self.cfg.data, self)}
        self._tabs['Appearance'].appearance_changed.connect(self.appearance_changed.emit)
        self._tabs['Catalogue'].catalog_changed.connect(self.catalogue_changed.emit)

    def add_tabs(self):
        for name, t in self._tabs.items():
            self._tab_widget.addTab(t, name)

    def init_ui(self):
        self._tab_widget = QtWidgets.QTabWidget(self)

        self.create_tabs()
        self.add_tabs()

        self._info_label = QtWidgets.QLabel(f"Advanced settings: {user_config_dir('specvizitor')}", self)
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

    @qlog
    def collect(self) -> bool:
        for t in self._tabs.values():
            if not t.collect():
                return False
        return True

    def accept(self):
        if not self.collect():
            return

        for t in self._tabs.values():
            t.accept()

        self.cfg.save()

        super().accept()
