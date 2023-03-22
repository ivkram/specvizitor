from astropy.table import Table
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
from .config import Docks, config
from .config.config import Appearance
from .utils.logs import LogMessageBox
from .utils.params import save_yaml
from .io.catalogue import create_cat
from .io.inspection_data import InspectionData
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
    project_loaded = QtCore.Signal(InspectionData)
    data_requested = QtCore.Signal()
    object_selected = QtCore.Signal(int, InspectionData, Table, config.Data)
    catalogue_changed = QtCore.Signal(object)
    screenshot_path_selected = QtCore.Signal(str)
    dock_layout_updated = QtCore.Signal(dict)
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

        self.data_viewer: DataViewer | None = None
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

        # restore the dock state (= the layout of the data viewer) from cache
        if self.rd.cache.dock_layout:
            self.dock_layout_updated.emit(self.rd.cache.dock_layout)

        # read cache and try to load the last active project
        if self.rd.cache.last_inspection_file:
            self.open_file(self.rd.cache.last_inspection_file)

    def init_ui(self):
        # create a central widget
        self.data_viewer = DataViewer(self.rd.config.data_viewer, self.rd.docks,
                                      spectral_lines=self.rd.lines, plugins=self._plugins, parent=self)

        # create a toolbar
        self.toolbar = ToolBar(self.rd, parent=self)
        self.toolbar.setObjectName('Toolbar')
        self.toolbar.setEnabled(True)

        # create a quick search widget
        self.quick_search = QuickSearch(parent=self)
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

        self._file.addSeparator()

        self._export = QtWidgets.QAction("&Export FITS Table...")
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
        self._reset_view.triggered.connect(self.data_viewer.view_reset.emit)
        self._view.addAction(self._reset_view)

        self._reset_dock_layout = QtWidgets.QAction("Reset Layout")
        self._reset_dock_layout.triggered.connect(self.data_viewer.reset_dock_layout)
        self._view.addAction(self._reset_dock_layout)

        self._view.addSeparator()

        self._fullscreen = QtWidgets.QAction("Fullscreen")
        self._fullscreen.triggered.connect(lambda:
                                           self._exit_fullscreen() if self.isFullScreen() else self._enter_fullscreen())
        self._fullscreen.setShortcut('F11')
        self._view.addAction(self._fullscreen)

        self._shortcut_fullscreen = QtWidgets.QShortcut('Esc', self)
        self._shortcut_fullscreen.activated.connect(lambda: self._exit_fullscreen() if self.isFullScreen() else None)

        self._docks = self._menu.addMenu("&Docks")

        self._backup_dock_configuration = QtWidgets.QAction("Backup...")
        self._backup_dock_configuration.triggered.connect(self._backup_dock_configuration_action)
        self._docks.addAction(self._backup_dock_configuration)

        self._restore_dock_configuration = QtWidgets.QAction("Restore...")
        self._restore_dock_configuration.triggered.connect(self._restore_dock_configuration_action)
        self._docks.addAction(self._restore_dock_configuration)

        self._docks.addSeparator()

        self._screenshot = QtWidgets.QAction("Capture...")
        self._screenshot.triggered.connect(self._screenshot_action)
        self._docks.addAction(self._screenshot)

        self._tools = self._menu.addMenu("&Tools")

        self._settings = QtWidgets.QAction("Se&ttings...")
        self._settings.triggered.connect(self._settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...")
        self._about.triggered.connect(self._about_action)
        self._help.addAction(self._about)

    def connect(self):
        # connect the main window to the child widgets
        for w in (self.data_viewer, self.toolbar, self.quick_search, self.object_info, self.review_form):
            self.project_loaded.connect(w.load_project)

        for w in (self.data_viewer, self.review_form):
            self.data_requested.connect(w.collect)

        for w in (self.data_viewer, self.toolbar, self.object_info, self.review_form):
            self.object_selected.connect(w.load_object)

        self.catalogue_changed.connect(self.object_info.update_table_items)

        self.dock_layout_updated.connect(self.data_viewer.restore_dock_layout)
        self.dock_configuration_updated.connect(self.data_viewer.update_dock_configuration)
        self.screenshot_path_selected.connect(self.data_viewer.take_screenshot)

        # connect the child widgets to the main window
        self.quick_search.id_selected.connect(self._select_by_id)
        self.quick_search.index_selected.connect(self._select_by_index)
        self.toolbar.object_selected.connect(self.load_object)
        self.toolbar.screenshot_button_clicked.connect(self._screenshot_action)
        self.toolbar.settings_button_clicked.connect(self._settings_action)

        self.data_viewer.data_collected.connect(self._save_viewer_data)
        self.review_form.data_collected.connect(self._save_review_data)

        # connect the child widgets between each other
        self.toolbar.reset_view_button_clicked.connect(self.data_viewer.view_reset.emit)
        self.toolbar.reset_layout_button_clicked.connect(self.data_viewer.reset_dock_layout)

    def populate(self):
        self.setCentralWidget(self.data_viewer)

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

        self.project_loaded.emit(self.rd.notes)

        # cache the inspection file name
        self.rd.cache.last_inspection_file = str(self.rd.output_path)
        self.rd.cache.save()

        # try to display the object with an index stored in cache
        j = self.rd.cache.last_object_index
        if j and 0 <= j < self.rd.notes.n_objects:
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
        self.rd.cache.last_object_index = j
        self.rd.cache.save()

        self.object_selected.emit(self.rd.j, self.rd.notes, self.rd.cat, self.rd.config.data)

        self._update_window_title()

    def refresh(self):
        if self.rd.j is not None:
            self.load_object(self.rd.j)

    def _update_window_title(self):
        self.setWindowTitle(
            f'{self.rd.output_path.name} – ID {self.rd.notes.get_id(self.rd.j)}'
            f'[#{self.rd.j + 1}/{self.rd.notes.n_objects}] – Specvizitor')

    @Slot(str)
    def _select_by_id(self, obj_id: str):
        if self.rd.notes.validate_id(obj_id):
            self.setFocus()
            self.load_object(self.rd.notes.get_id_loc(obj_id))

    @Slot(int)
    def _select_by_index(self, index: int):
        if self.rd.notes.validate_index(index):
            self.setFocus()
            self.load_object(index - 1)

    def _save_action(self):
        """ Instead of saving inspection results, display a message saying that the auto-save mode is enabled.
        """
        msg = 'The project data is saved automatically'
        if self.rd.output_path is not None:
            msg += ' to {}'.format(self.rd.output_path)
        LogMessageBox(logging.INFO, msg, parent=self)

    def _save_as_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                           basedir=str(self.rd.output_path),
                                           filters='CSV Files (*.csv)')[0]
        if path:
            self.rd.output_path = pathlib.Path(path).resolve()
            self.rd.notes.write(self.rd.output_path)
            self.rd.cache.last_inspection_file = str(self.rd.output_path)
            self.rd.cache.save()
            self._update_window_title()

    def _export_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Export To FITS',
                                           basedir=str(self.rd.output_path.with_suffix('.fits')),
                                           filters='FITS Files (*.fits)')[0]

        if path:
            self.rd.notes.write(self.rd.output_path.with_suffix('.fits'), 'fits')

    def _exit_action(self):
        if self.rd.j is not None:
            self.data_requested.emit()

        # save the state and geometry of the main window
        settings = QtCore.QSettings()
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

        self.close()
        logger.info("Application closed")

    def _restore_dock_configuration_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Dock Configuration',
                                           filters='YAML Files (*.yml)')[0]
        if path:
            new_docks = self.rd.docks.replace_params(pathlib.Path(path))
            if new_docks is None:
                logger.error('Failed to restore the dock configuration')
            else:
                self.rd.docks = new_docks
                self.rd.docks.save()

                self.dock_configuration_updated.emit(self.rd.docks)

                self.refresh()

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
        default_filename = f'{self.rd.output_path.stem.replace(" ", "_")}_ID{self.rd.notes.get_id(self.rd.j)}.png'
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')
        if path:
            self.screenshot_path_selected.emit(path)

    def _settings_action(self):
        dialog = Settings(self.rd.config, parent=self)
        dialog.catalogue_selected.connect(self.update_catalogue)
        if dialog.exec():
            self.refresh()

    @Slot(object)
    def update_catalogue(self, cat: Table | None):
        if cat is None and self.rd.notes is not None:
            self.rd.cat = create_cat(self.rd.notes.ids)
        else:
            self.rd.cat = cat

        self.catalogue_changed.emit(self.rd.cat)

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v{}".format(version('specvizitor')))

    def closeEvent(self, _):
        self._exit_action()

    @QtCore.Slot(dict)
    def _save_viewer_data(self, layout: dict):
        self.rd.cache.dock_layout = layout
        self.rd.cache.save()

    @QtCore.Slot(str, dict)
    def _save_review_data(self, comments: str, checkboxes: dict[str, bool]):
        self.rd.notes.update_value(self.rd.j, 'comment', comments)
        for cname, is_checked in checkboxes.items():
            self.rd.notes.update_value(self.rd.j, cname, is_checked)
        self.rd.save()


def change_appearance(cfg: Appearance):
    pg.setConfigOption('antialias', cfg.antialiasing)

    # set up the theme
    qdarktheme.setup_theme(cfg.theme)
    if cfg.theme == 'dark':
        pg.setConfigOption('background', "#1d2023")
        pg.setConfigOption('foreground', '#eff0f1')
    else:
        pg.setConfigOption('background', "w")
        pg.setConfigOption('foreground', 'k')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--purge', action='store_true')

    args = parser.parse_args()

    # logging configuration
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    # initialize the application data
    appdata = AppData.init_from_disk(purge=args.purge)

    # start the application
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('FRESCO')
    app.setApplicationName('Specvizitor')
    logger.info("Application started")

    # pyqtgraph configuration
    pg.setConfigOption('imageAxisOrder', 'row-major')

    # GUI appearance
    change_appearance(cfg=appdata.config.appearance)

    # initialize the main window
    window = MainWindow(appdata=appdata)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
