from astropy.table import Table
import qtpy.compat
from qtpy import QtWidgets, QtCore, QtGui

from dataclasses import asdict
from importlib.metadata import version
import logging
import pathlib

from ..appdata import AppData
from ..config import config as cfg
from ..config.appearance import set_up_appearance
from ..config import Config, Cache, Docks, SpectralLines
from ..io.catalogue import read_cat, create_cat
from ..io.inspection_data import InspectionData
from ..utils.logs import LogMessageBox
from ..utils.params import save_yaml

from .DataViewer import DataViewer
from .NewFile import NewFile
from .ObjectInfo import ObjectInfo
from .QuickSearch import QuickSearch
from .ReviewForm import ReviewForm
from .Settings import Settings
from .ToolBar import ToolBar

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    project_loaded = QtCore.Signal(InspectionData)
    data_requested = QtCore.Signal()
    object_selected = QtCore.Signal(int, InspectionData, Table, cfg.Data)

    theme_changed = QtCore.Signal()
    catalogue_changed = QtCore.Signal(object)
    visible_columns_updated = QtCore.Signal(list)
    dock_layout_updated = QtCore.Signal(dict)
    dock_configuration_updated = QtCore.Signal(Docks)

    screenshot_path_selected = QtCore.Signal(str)

    def __init__(self, config: Config, cache: Cache, docks: Docks, spectral_lines: SpectralLines | None = None,
                 plugins=None, parent=None):
        super().__init__(parent)

        self.rd = AppData()
        
        self._config = config
        self._cache = cache

        self._dock_cfg = docks
        self._spectral_lines = spectral_lines

        self._plugins = plugins

        self.was_maximized: bool = False
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._update_window_title()  # set the title of the main window
        # self.setWindowIcon(QtGui.QIcon('logo2_2.png'))

        # add a status bar
        # self.statusBar().showMessage("Message in the statusbar")

        self._data_viewer: DataViewer | None = None
        self._commands_bar: ToolBar | None = None
        self._quick_search: QuickSearch | None = None
        self._object_info: ObjectInfo | None = None
        self._review_form: ReviewForm | None = None

        self._quick_search_dock: QtWidgets.QDockWidget | None = None
        self._object_info_dock: QtWidgets.QDockWidget | None = None
        self._review_form_dock: QtWidgets.QDockWidget | None = None

        self.init_ui()
        self.populate()
        self.connect()

        self.restore_window_state()

        # restore the dock state (= the layout of the data viewer) from cache
        if self._cache.dock_layout:
            self.dock_layout_updated.emit(self._cache.dock_layout)

        # load the catalogue to the memory
        if self._config.catalogue.filename:
            self.load_catalogue()

        # update the list of catalogue columns visible in the object info widget
        # write "is not None" explicitly in case visible_columns == []
        if self.rd.cat and self._cache.visible_columns is not None:
            self.visible_columns_updated.emit(self._cache.visible_columns)

        # read cache and try to load the last active project
        if self._cache.last_inspection_file:
            self.open_file(self._cache.last_inspection_file, self._cache.last_object_index)

    def init_ui(self):
        # create a central widget
        self._data_viewer = DataViewer(self._dock_cfg, self._config.appearance,
                                       spectral_lines=self._spectral_lines, plugins=self._plugins, parent=self)

        # create a toolbar
        self._commands_bar = ToolBar(self.rd, self._config.appearance, parent=self)
        self._commands_bar.setObjectName('Toolbar')
        self._commands_bar.setEnabled(True)

        # create a quick search widget
        self._quick_search = QuickSearch(parent=self)
        self._quick_search_dock = QtWidgets.QDockWidget('Quick Search', self)
        self._quick_search_dock.setObjectName('Quick Search')
        self._quick_search_dock.setWidget(self._quick_search)

        # create a widget displaying information about the object
        self._object_info = ObjectInfo(parent=self)
        self._object_info_dock = QtWidgets.QDockWidget('Object Information', self)
        self._object_info_dock.setObjectName('Object Information')
        self._object_info_dock.setWidget(self._object_info)

        # create a widget for writing comments
        self._review_form = ReviewForm(cfg=self._config.review_form, parent=self)
        self._review_form_dock = QtWidgets.QDockWidget('Review Form', self)
        self._review_form_dock.setObjectName('Review Form')
        self._review_form_dock.setWidget(self._review_form)

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
        self._reset_view.setEnabled(False)
        self._reset_view.triggered.connect(self._data_viewer.view_reset.emit)
        self._view.addAction(self._reset_view)

        self._reset_dock_layout = QtWidgets.QAction("Reset Layout")
        self._reset_dock_layout.setEnabled(False)
        self._reset_dock_layout.triggered.connect(self._data_viewer.reset_dock_layout)
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

        self._add_dock = QtWidgets.QAction("Add...")
        self._add_dock.setEnabled(False)
        self._docks.addAction(self._add_dock)

        self._docks.addSeparator()

        self._backup_dock_configuration = QtWidgets.QAction("Backup...")
        self._backup_dock_configuration.triggered.connect(self._backup_dock_configuration_action)
        self._docks.addAction(self._backup_dock_configuration)

        self._restore_dock_configuration = QtWidgets.QAction("Restore...")
        self._restore_dock_configuration.triggered.connect(self._restore_dock_configuration_action)
        self._docks.addAction(self._restore_dock_configuration)

        self._tools = self._menu.addMenu("&Tools")

        self._screenshot = QtWidgets.QAction("Take Screenshot...")
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
        for w in (self._data_viewer, self._commands_bar, self._quick_search, self._object_info, self._review_form):
            self.project_loaded.connect(w.load_project)

        for w in (self._data_viewer, self._object_info, self._review_form):
            self.data_requested.connect(w.collect)

        for w in (self._data_viewer, self._commands_bar, self._object_info, self._review_form):
            self.object_selected.connect(w.load_object)

        self.theme_changed.connect(self._data_viewer.init_ui)
        self.theme_changed.connect(self._commands_bar.set_icons)
        self.catalogue_changed.connect(self._object_info.update_table_items)
        self.visible_columns_updated.connect(self._object_info.update_visible_columns)

        self.dock_layout_updated.connect(self._data_viewer.restore_dock_layout)
        self.dock_configuration_updated.connect(self._data_viewer.update_dock_configuration)

        self.screenshot_path_selected.connect(self._data_viewer.take_screenshot)

        # connect the child widgets to the main window
        self._quick_search.id_selected.connect(self._select_by_id)
        self._quick_search.index_selected.connect(self._select_by_index)
        self._commands_bar.object_selected.connect(self.load_object)
        self._commands_bar.screenshot_button_clicked.connect(self._screenshot_action)
        self._commands_bar.settings_button_clicked.connect(self._settings_action)

        self._data_viewer.data_collected.connect(self._save_viewer_data)
        self._object_info.data_collected.connect(self._save_obj_info_data)
        self._review_form.data_collected.connect(self._save_review_data)

        # connect the child widgets between each other
        self._commands_bar.reset_view_button_clicked.connect(self._data_viewer.view_reset.emit)
        self._commands_bar.reset_layout_button_clicked.connect(self._data_viewer.reset_dock_layout)

    def populate(self):
        self.setCentralWidget(self._data_viewer)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self._commands_bar)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._quick_search_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._object_info_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._review_form_dock)

    def load_catalogue(self):
        cat = read_cat(self._config.catalogue.filename, translate=self._config.catalogue.translate)
        if cat is None:
            self._config.catalogue.filename = None
            self._config.save()

        self.update_catalogue(cat)

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
        dialog = NewFile(cfg=self._config, parent=self)
        dialog.catalogue_changed.connect(self.update_catalogue)
        dialog.output_path_selected.connect(self.update_output_path)
        if dialog.exec():
            self.rd.create(flags=self._config.review_form.default_checkboxes)
            self.load_project()

    def _open_file_action(self):
        """ Open an existing inspection file via QFileDialog.
        """
        path = qtpy.compat.getopenfilename(self, caption='Open Inspection File', filters='CSV Files (*.csv)')[0]
        if path:
            self.open_file(path)

    def open_file(self, path: str, cached_index: int | None = None):
        """ Load inspection data from an existing inspection file.
        @param path: path to the inspection file
        @param cached_index:
        """
        path = pathlib.Path(path)
        if path.exists():
            self.update_output_path(path)
            self.rd.read()
            self.update_catalogue(self.rd.cat)  # in case the catalogue hasn't been initialized before
            self.load_project(cached_index)
        else:
            logger.warning('Inspection file not found (path: {})'.format(path))

    def load_project(self, j: int | None = None):
        """ Update the state of the main window and activate the central widget after loading inspection data.
        """
        for w in (self._save, self._save_as, self._export, self._reset_view, self._reset_dock_layout):
            w.setEnabled(True)

        self.project_loaded.emit(self.rd.review)

        if j is None or (j < 0 or j >= self.rd.review.n_objects):
            j = 0

        self.load_object(j, request_data=False)

    @QtCore.Slot(int)
    def load_object(self, j: int, request_data=True):
        """ Load a new object to the central widget.
        @param j: the index of the object to display
        @param request_data:
        """
        if request_data:
            self.data_requested.emit()

        self.rd.j = j

        # cache the index of the object
        self._cache.last_object_index = j
        self._cache.save()

        self.object_selected.emit(self.rd.j, self.rd.review, self.rd.cat, self._config.data)

        self._update_window_title()

    def reload(self):
        if self.rd.j is not None:
            self.load_object(self.rd.j)

    def _update_window_title(self):
        title = ''
        if self.rd.output_path is not None:
            title += f'{self.rd.output_path.name} – '
        if self.rd.j is not None:
            title += f'ID {self.rd.review.get_id(self.rd.j)} [#{self.rd.j + 1}/{self.rd.review.n_objects}] – '
        title += 'Specvizitor'
        self.setWindowTitle(title)

    @QtCore.Slot(str)
    def _select_by_id(self, obj_id: str):
        if self.rd.review.validate_id(obj_id):
            self.setFocus()
            self.load_object(self.rd.review.get_id_loc(obj_id))

    @QtCore.Slot(int)
    def _select_by_index(self, index: int):
        if self.rd.review.validate_index(index):
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
            self.update_output_path(pathlib.Path(path).resolve())
            self.rd.save()

    def _export_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Export To FITS',
                                           basedir=str(self.rd.output_path.with_suffix('.fits')),
                                           filters='FITS Files (*.fits)')[0]

        if path:
            self.rd.review.write(self.rd.output_path.with_suffix('.fits'), 'fits')

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
            new_docks = self._dock_cfg.replace_params(pathlib.Path(path))
            if new_docks is None:
                logger.error('Failed to restore the dock configuration')
            else:
                self._dock_cfg = new_docks
                self._dock_cfg.save()

                self.dock_configuration_updated.emit(self._dock_cfg)

                self.reload()

                logger.info('Dock configuration restored')

    def _backup_dock_configuration_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Save Dock Configuration',
                                           basedir=str(pathlib.Path() / 'docks.yml'),
                                           filters='YAML Files (*.yml)')[0]

        if path:
            save_yaml(path, asdict(self._dock_cfg))
            logger.info('Dock configuration saved')

    def _enter_fullscreen(self):
        self.was_maximized = True if self.isMaximized() else False
        self.showFullScreen()

    def _exit_fullscreen(self):
        self.showNormal()
        if self.was_maximized:
            self.showMaximized()

    def _screenshot_action(self):
        default_filename = f'{self.rd.output_path.stem.replace(" ", "_")}_ID{self.rd.review.get_id(self.rd.j)}.png'
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')
        if path:
            self.screenshot_path_selected.emit(path)

    def _settings_action(self):
        dialog = Settings(self._config, parent=self)
        dialog.appearance_changed.connect(self.update_appearance)
        dialog.catalogue_changed.connect(self.update_catalogue)
        if dialog.exec():
            self.reload()

    @QtCore.Slot(bool)
    def update_appearance(self, theme_changed: bool = False):
        set_up_appearance(self._config.appearance)
        if theme_changed:
            self.theme_changed.emit()

    @QtCore.Slot(object)
    def update_catalogue(self, cat: Table | None):
        if cat is None and self.rd.review is not None:
            self.rd.cat = create_cat(self.rd.review.ids)
        else:
            self.rd.cat = cat
        self.catalogue_changed.emit(self.rd.cat)

    @QtCore.Slot(pathlib.Path)
    def update_output_path(self, path: pathlib.Path):
        self.rd.output_path = path
        self._cache.last_inspection_file = str(path)
        self._cache.save()
        self._update_window_title()

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v{}".format(version('specvizitor')))

    def closeEvent(self, _):
        self._exit_action()

    @QtCore.Slot(dict)
    def _save_viewer_data(self, layout: dict):
        self._cache.dock_layout = layout
        self._cache.save()

    @QtCore.Slot(list)
    def _save_obj_info_data(self, visible_columns: list[str]):
        self._cache.visible_columns = visible_columns
        self._cache.save()

    @QtCore.Slot(str, dict)
    def _save_review_data(self, comments: str, checkboxes: dict[str, bool]):
        self.rd.review.update_value(self.rd.j, 'comment', comments)
        for cname, is_checked in checkboxes.items():
            self.rd.review.update_value(self.rd.j, cname, is_checked)
        self.rd.save()
