from astropy.table import Table
import pandas as pd
from platformdirs import user_config_dir, user_cache_dir
import pyqtgraph as pg
import qdarktheme
import qtpy.compat
from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Slot


import argparse
from dataclasses import asdict
import importlib
from importlib.metadata import version
import logging
import pathlib
import sys

from .appdata import AppData
from .config import Config, Docks, SpectralLines, Cache
from .utils.logs import LogMessageBox
from .utils.params import LocalFile, save_yaml
from .io.viewer_data import add_enabled_aliases

from .menu.NewFile import NewFile
from .menu.Settings import Settings

from .widgets.DataViewer import DataViewer
from .widgets.ToolBar import ToolBar
from .widgets.QuickSearch import QuickSearch
from .widgets.ObjectInfo import ObjectInfo
from .widgets.ReviewForm import ReviewForm

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    project_loaded = QtCore.Signal(pd.DataFrame)
    data_requested = QtCore.Signal()
    object_selected = QtCore.Signal(AppData)
    catalogue_changed = QtCore.Signal(Table)
    screenshot_path_selected = QtCore.Signal(str)
    dock_state_updated = QtCore.Signal(dict)
    dock_configuration_updated = QtCore.Signal(Docks)

    def __init__(self, appdata: AppData, parent=None):
        super().__init__(parent)

        self.rd = appdata

        self.was_maximized: bool = False
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.setWindowTitle('Specvizitor')  # set the title of the main window
        # self.setWindowIcon(QtGui.QIcon('logo2_2.png'))

        # register units
        if appdata.config.data.defined_units is not None:
            add_enabled_aliases(appdata.config.data.defined_units)

        # register plugins
        self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin()
                         for plugin_name in self.rd.config.plugins]

        # add a status bar
        # self.statusBar().showMessage("Message in the statusbar")

        self.inspector_widget: DataViewer | None = None
        self.toolbar: ToolBar | None = None
        self.quick_search: QuickSearch | None = None
        self.object_info: ObjectInfo | None = None
        self.review_form: ReviewForm | None = None

        self.quick_search_dock: QtWidgets.QDockWidget | None = None
        self.object_info_dock: QtWidgets.QDockWidget | None = None
        self.review_form_dock: QtWidgets.QDockWidget | None = None

        self.init_ui()
        self.populate()
        self.connect()

        self.restore_window_state()

        # restore the dock state from cache
        if self.rd.cache.dock_state:
            self.dock_state_updated.emit(self.rd.cache.dock_state)

        # read cache and try to load the last active project
        if self.rd.cache.last_inspection_file:
            self.open_file(self.rd.cache.last_inspection_file)

    def init_ui(self):
        # create a central widget
        self.inspector_widget = DataViewer(self.rd.config.data_viewer, self.rd.docks,
                                           spectral_lines=self.rd.lines, plugins=self._plugins, parent=self)

        # create a toolbar
        self.toolbar = ToolBar(self.rd, parent=self)
        self.toolbar.setObjectName('Toolbar')
        self.toolbar.setEnabled(True)

        # create a quick search widget
        self.quick_search = QuickSearch(rd=self.rd, parent=self)
        self.quick_search_dock = QtWidgets.QDockWidget('Quick Search', self)
        self.quick_search_dock.setObjectName('Quick Search')
        self.quick_search_dock.setWidget(self.quick_search)

        # create a widget displaying information about the object
        self.object_info = ObjectInfo(cfg=self.rd.config.object_info, parent=self)
        self.object_info_dock = QtWidgets.QDockWidget('Object Information', self)
        self.object_info_dock.setObjectName('Object Information')
        self.object_info_dock.setWidget(self.object_info)

        # create a widget for writing comments
        self.review_form = ReviewForm(cfg=self.rd.config.review_form, parent=self)
        self.review_form_dock = QtWidgets.QDockWidget('Review Form', self)
        self.review_form_dock.setObjectName('Review Form')
        self.review_form_dock.setWidget(self.review_form)

        self._init_menu()

    def _init_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_file = QtWidgets.QAction("&New...")
        self._new_file.triggered.connect(self._new_file_action)
        self._new_file.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        self._file.addAction(self._new_file)

        self._open_file = QtWidgets.QAction("&Open...")
        self._open_file.triggered.connect(self._open_file_action)
        self._open_file.setShortcut(QtGui.QKeySequence('Ctrl+O'))
        self._file.addAction(self._open_file)

        self._file.addSeparator()

        self._save = QtWidgets.QAction("&Save...")
        self._save.triggered.connect(self._save_action)
        self._save.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self._save.setEnabled(False)
        self._file.addAction(self._save)

        self._save_as = QtWidgets.QAction("Save As...")
        self._save_as.triggered.connect(self._save_as_action)
        self._save_as.setShortcut(QtGui.QKeySequence('Shift+Ctrl+S'))
        self._save_as.setEnabled(False)
        self._file.addAction(self._save_as)

        self._export = QtWidgets.QAction("&Export...")
        self._export.triggered.connect(self._export_action)
        self._export.setEnabled(False)
        self._file.addAction(self._export)

        self._file.addSeparator()

        self._quit = QtWidgets.QAction("&Quit...")
        self._quit.triggered.connect(self._exit_action)
        self._quit.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        self._file.addAction(self._quit)

        self._view = self._menu.addMenu("&View")

        self._reset_view = QtWidgets.QAction("Reset View")
        self._reset_view.setShortcut('F5')
        self._reset_view.triggered.connect(self.inspector_widget.view_reset.emit)
        self._view.addAction(self._reset_view)

        self._reset_dock_state = QtWidgets.QAction("Reset Dock State")
        self._reset_dock_state.triggered.connect(self.inspector_widget.reset_dock_state)
        self._view.addAction(self._reset_dock_state)

        self._view.addSeparator()

        self._backup_dock_configuration = QtWidgets.QAction("Backup...")
        self._backup_dock_configuration.triggered.connect(self._backup_dock_configuration_action)
        self._view.addAction(self._backup_dock_configuration)

        self._restore_dock_configuration = QtWidgets.QAction("Restore...")
        self._restore_dock_configuration.triggered.connect(self._restore_dock_configuration_action)
        self._view.addAction(self._restore_dock_configuration)

        self._view.addSeparator()

        self._fullscreen = QtWidgets.QAction("Fullscreen")
        self._fullscreen.triggered.connect(lambda:
                                           self._exit_fullscreen() if self.isFullScreen() else self._enter_fullscreen())
        self._fullscreen.setShortcut('F11')
        self._view.addAction(self._fullscreen)

        self._shortcut_fullscreen = QtWidgets.QShortcut('Esc', self)
        self._shortcut_fullscreen.activated.connect(lambda: self._exit_fullscreen() if self.isFullScreen() else None)

        self._tools = self._menu.addMenu("&Tools")

        self._screenshot = QtWidgets.QAction("Capture Dock Area...")
        self._screenshot.triggered.connect(self._screenshot_action)
        self._tools.addAction(self._screenshot)

        self._tools.addSeparator()

        self._settings = QtWidgets.QAction("Se&ttings...")
        self._settings.triggered.connect(self._settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...")
        self._about.triggered.connect(self._about_action)
        self._help.addAction(self._about)

    def connect(self):
        # connect the main window to the child widgets
        for w in (self.inspector_widget, self.toolbar, self.quick_search, self.object_info, self.review_form):
            self.project_loaded.connect(w.load_project)

        for w in (self.inspector_widget, self.review_form):
            self.data_requested.connect(w.capture)

        for w in (self.inspector_widget, self.toolbar, self.object_info, self.review_form):
            self.object_selected.connect(w.load_object)

        self.catalogue_changed.connect(self.object_info.update_table_items)

        self.dock_state_updated.connect(self.inspector_widget.restore_dock_state)
        self.dock_configuration_updated.connect(self.inspector_widget.update_dock_configuration)
        self.screenshot_path_selected.connect(self.inspector_widget.take_screenshot)

        # connect the child widgets to the main window
        self.quick_search.object_selected.connect(self.load_object)
        self.toolbar.object_selected.connect(self.load_object)
        self.toolbar.screenshot_button_clicked.connect(self._screenshot_action)
        self.toolbar.settings_button_clicked.connect(self._settings_action)

        self.inspector_widget.data_captured.connect(self._save_inspector_data)
        self.review_form.data_captured.connect(self._save_review_data)

        # connect the child widgets between each other
        self.toolbar.reset_view_button_clicked.connect(self.inspector_widget.view_reset.emit)
        self.toolbar.reset_dock_state_button_clicked.connect(self.inspector_widget.reset_dock_state)

    def populate(self):
        self.setCentralWidget(self.inspector_widget)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.quick_search_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.object_info_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.review_form_dock)

    def restore_window_state(self):
        settings = QtCore.QSettings()
        if settings.value("geometry") is None or settings.value("windowState") is None:
            self.showMaximized()
            self.setFocus()
        else:
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))

    def _new_file_action(self):
        """ Create a new inspection file via the NewFile dialog.
        """
        dialog = NewFile(self.rd, parent=self)
        if dialog.exec():
            self.rd.cache.last_object_index = 0
            self.catalogue_changed.emit(self.rd.cat)
            self.load_project()

    def _open_file_action(self):
        """ Open an existing inspection file via QFileDialog.
        """
        path = qtpy.compat.getopenfilename(self, caption='Open Inspection File', filters='CSV Files (*.csv)')[0]
        if path:
            self.rd.cache.last_object_index = 0
            self.open_file(path)

    def open_file(self, path: str):
        """ Load inspection data from an existing inspection file.
        @param path: path to the inspection file
        """
        if pathlib.Path(path).exists():
            self.rd.output_path = pathlib.Path(path)
            self.rd.read()
            self.catalogue_changed.emit(self.rd.cat)
            self.load_project()
        else:
            logger.warning('Inspection file not found (path: {})'.format(path))

    def load_project(self):
        """ Update the state of the main window and activate the central widget after loading inspection data.
        """
        for w in (self._save, self._save_as, self._export):
            w.setEnabled(True)

        self.project_loaded.emit(self.rd.df)

        # cache the inspection file name
        self.rd.cache.last_inspection_file = str(self.rd.output_path)
        self.rd.cache.save()

        # try to display the object with an index stored in cache
        j = self.rd.cache.last_object_index
        if j and 0 <= j < self.rd.n_objects:
            self.load_object(int(j))
        else:
            self.load_object(0)

    @Slot(int)
    def load_object(self, j: int):
        """ Load a new object to the central widget.
        @param j: the index of the object to display
        """
        if self.rd.j is not None:
            self.data_requested.emit()

        self.rd.j = j

        # cache the index of the object
        # TODO: cache the ID instead of the index
        self.rd.cache.last_object_index = j
        self.rd.cache.save()

        self.object_selected.emit(self.rd)

        self.setWindowTitle(
            f'{self.rd.output_path.name} – ID {self.rd.id} [#{self.rd.j + 1}/{self.rd.n_objects}] – Specvizitor')

    def _save_action(self):
        """ Instead of saving inspection results, display a message saying that the auto-save mode is enabled.
        """
        msg = 'The project data is saved automatically'
        if self.rd.output_path is not None:
            msg += ' to {}'.format(self.rd.output_path)
        LogMessageBox(logging.INFO, msg, parent=self)

    def _save_as_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _export_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _exit_action(self):
        if self.rd.df is not None:
            self.data_requested.emit()

        # save the state and geometry of the main window
        settings = QtCore.QSettings()
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

        self.close()
        logger.info("Application closed")

    def _restore_dock_configuration_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Dock Configuration',
                                           basedir=str(pathlib.Path()),
                                           filters='YAML Files (*.yml)')[0]
        if path:
            new_docks = self.rd.docks.replace_params(pathlib.Path(path))
            if new_docks is None:
                logger.error('Failed to restore the dock configuration')
            else:
                self.rd.docks = new_docks
                self.rd.docks.save()

                self.dock_configuration_updated.emit(self.rd.docks)
                self.object_selected.emit(self.rd)

                logger.info('Dock configuration restored')

    def _backup_dock_configuration_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Save Dock Configuration',
                                           basedir=str(pathlib.Path() / 'docks.yml'),
                                           filters='YAML Files (*.yml)')[0]

        if path:
            save_yaml(path, asdict(self.rd.docks))
            logger.info('Dock configuration saved')

    def _enter_fullscreen(self):
        self.was_maximized = True if self.isMaximized() else False
        self.showFullScreen()

    def _exit_fullscreen(self):
        self.showNormal()
        if self.was_maximized:
            self.showMaximized()

    def _screenshot_action(self):
        default_filename = '{}_ID{}.png'.format(self.rd.output_path.stem.replace(' ', '_'), self.rd.id)
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')
        if path:
            self.screenshot_path_selected.emit(path)

    def _settings_action(self):
        dialog = Settings(self.rd, parent=self)
        if dialog.exec():
            self.catalogue_changed.emit(self.rd.cat)
            if self.rd.df is not None:
                for widget in (self.inspector_widget, self.object_info):
                    widget.load_object(self.rd)

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v{}".format(version('specvizitor')))

    def closeEvent(self, _):
        self._exit_action()

    @QtCore.Slot(dict)
    def _save_inspector_data(self, dock_state: dict):
        self.rd.cache.dock_state = dock_state
        self.rd.cache.save()

    @QtCore.Slot(str, dict)
    def _save_review_data(self, comments: str, checkboxes: dict[str, bool]):
        self.rd.df.at[self.rd.id, 'comment'] = comments
        for cname, is_checked in checkboxes.items():
            self.rd.df.at[self.rd.id, cname] = is_checked
        self.rd.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--purge', action='store_true')

    args = parser.parse_args()

    # logging configuration
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    user_files: dict[str, LocalFile] = {
        'config': LocalFile(user_config_dir('specvizitor'), full_name='Settings file'),
        'docks': LocalFile(user_config_dir('specvizitor'), filename='docks.yml', full_name='Dock configuration file'),
        'lines': LocalFile(user_config_dir('specvizitor'), filename='lines.yml', full_name='List of spectral lines'),
        'cache': LocalFile(user_cache_dir('specvizitor'), full_name='Cache file', auto_backup=False)
    }

    if args.purge:
        for f in user_files.values():
            f.delete()

    # initialize the app data
    appdata = AppData(config=Config.read_user_params(user_files['config'], default='default_config.yml'),
                      docks=Docks.read_user_params(user_files['docks'], default='default_docks.yml'),
                      lines=SpectralLines.read_user_params(user_files['lines'], default='default_lines.yml'),
                      cache=Cache.read_user_params(user_files['cache']))

    # pyqtgraph configuration
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    pg.setConfigOption('imageAxisOrder', 'row-major')
    pg.setConfigOption('antialias', appdata.config.appearance.antialiasing)

    # start the application
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('FRESCO')
    app.setApplicationName('Specvizitor')
    logger.info("Application started")

    # set up the theme
    qdarktheme.setup_theme(appdata.config.appearance.theme)
    if appdata.config.appearance.theme == 'dark':
        pg.setConfigOption('background', "#1d2023")
        pg.setConfigOption('foreground', '#eff0f1')
    else:
        pg.setConfigOption('background', "w")
        pg.setConfigOption('foreground', 'k')

    # initialize the main window
    window = MainWindow(appdata=appdata)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
