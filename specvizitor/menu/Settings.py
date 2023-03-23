from platformdirs import user_config_dir
from qtpy import QtWidgets, QtCore

from abc import abstractmethod
import logging

from ..config import config
from ..io.catalogue import read_cat, cat_browser
from ..io.viewer_data import data_browser
from ..utils.logs import qlog

from ..widgets.AbstractWidget import AbstractWidget
from ..widgets.Section import Section
from ..widgets.FileBrowser import FileBrowser

logger = logging.getLogger(__name__)


class SettingsWidget(AbstractWidget):
    SPACING = 20

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout().setAlignment(QtCore.Qt.AlignTop)
        self.setFixedHeight(200)

    @abstractmethod
    def validate(self) -> bool:
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
        self.layout().setSpacing(self.SPACING)

    def populate(self):
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setAlignment(QtCore.Qt.AlignLeft)
        sub_layout.addWidget(self._theme_label)
        sub_layout.addWidget(self._theme_combobox)

        self.layout().addLayout(sub_layout)

        self.layout().addWidget(self._antialiasing_checkbox)

    def validate(self) -> bool:
        return True

    def accept(self):
        theme = self._theme_combobox.currentText()
        if theme != self.cfg.theme:
            theme_changed = True
        else:
            theme_changed = False

        self.cfg.theme = theme
        self.cfg.antialiasing = self._antialiasing_checkbox.isChecked()

        self.appearance_changed.emit(theme_changed)


class CatalogueWidget(SettingsWidget):
    catalogue_changed = QtCore.Signal(object)

    def __init__(self, cfg: config.Catalogue, parent=None):
        self.cfg = cfg

        self.cat = None

        self._browser: FileBrowser | None = None
        self._aliases_section: Section | None = None
        self._show_all_checkbox: QtWidgets.QCheckBox | None = None

        super().__init__(parent=parent)

    def init_ui(self):
        self._browser = cat_browser(self.cfg.filename, title='Filename:', parent=self)

        self._aliases_section = Section("Column aliases", parent=self)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(self.SPACING)

    def populate(self):
        self.layout().addWidget(self._browser)

        sub_layout = QtWidgets.QVBoxLayout()

        self._aliases_section.set_layout(sub_layout)
        self.layout().addWidget(self._aliases_section)

    def get_catalogue(self):
        return read_cat(self._browser.path, translate=self.cfg.translate)

    def validate(self) -> bool:
        if not self._browser.exists(verbose=True):
            return False

        if self._browser.is_filled():
            self.cat = self.get_catalogue()
            if not self.cat:
                return False

        return True

    def accept(self):
        cat_filename = self._browser.path if self.cat else None

        if self.cfg.filename != cat_filename:
            self.cfg.filename = cat_filename
            self.catalogue_changed.emit(self.cat)


class DataSourceWidget(SettingsWidget):
    def __init__(self, cfg: config.Data, parent=None):
        self.cfg = cfg

        self._browser: FileBrowser | None = None

        super().__init__(parent=parent)

    def init_ui(self):
        self._browser = data_browser(self.cfg.dir, title='Directory:', parent=self)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(self.SPACING)

    def populate(self):
        self.layout().addWidget(self._browser)

    def validate(self) -> bool:
        if not self._browser.is_filled(verbose=True) or not self._browser.exists(verbose=True):
            return False

        return True

    def accept(self):
        self.cfg.dir = self._browser.path


class Settings(QtWidgets.QDialog):
    appearance_changed = QtCore.Signal(bool)
    catalogue_changed = QtCore.Signal(object)

    def __init__(self, cfg: config.Config, parent=None):
        self.cfg = cfg

        self._tab_widget: QtWidgets.QTabWidget | None = None
        self._tabs: dict[str, SettingsWidget] | None = None

        self._info_label: QtWidgets.QLabel | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setWindowTitle("Settings [Beta]")

        self.init_ui()
        self.set_layout()
        self.populate()

    def create_tabs(self):
        self._tabs = {'Appearance': AppearanceWidget(self.cfg.appearance, self),
                      'Catalogue': CatalogueWidget(self.cfg.catalogue, self),
                      'Data Source': DataSourceWidget(self.cfg.data, self)}
        self._tabs['Appearance'].appearance_changed.connect(self.appearance_changed.emit)
        self._tabs['Catalogue'].catalogue_changed.connect(self.catalogue_changed.emit)

    def add_tabs(self):
        for name, t in self._tabs.items():
            self._tab_widget.addTab(t, name)

    def init_ui(self):
        self._tab_widget = QtWidgets.QTabWidget(self)

        self.create_tabs()
        self.add_tabs()

        self._info_label = QtWidgets.QLabel(f"Advanced settings: {user_config_dir('specvizitor')}", self)

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
    def validate(self) -> bool:
        for t in self._tabs.values():
            if not t.validate():
                return False
        return True

    def accept(self):
        if not self.validate():
            return

        for t in self._tabs.values():
            t.accept()

        self.cfg.save()

        super().accept()
