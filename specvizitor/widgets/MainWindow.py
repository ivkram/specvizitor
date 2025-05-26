import qtpy.compat
from qtpy import QtWidgets, QtCore, QtGui
import numpy as np

from dataclasses import asdict
from importlib import metadata
import logging
import pathlib
import time

from .. import APPLICATION
from ..appdata import AppData
from ..config.appearance import setup_appearance
from ..config import Config, Cache, DataWidgets, SpectralLineData
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..plugins.plugin_core import PluginCore
from ..utils.params import save_yaml

from .DataViewer import DataViewer
from .NewFile import NewFile
from .ObjectInfo import ObjectInfo
from .QuickSearch import QuickSearch
from .InspectionResults import InspectionResults
from .InspectionFieldEditor import InspectionFieldEditor
from .Subsets import Subsets
from .Settings import Settings
from .ToolBar import ToolBar

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    EXIT_CODE_REBOOT = -42
    project_loaded = QtCore.Signal(InspectionData)
    object_selected = QtCore.Signal(int, InspectionData, object)
    loading_aborted = QtCore.Signal()
    data_requested = QtCore.Signal()
    save_action_invoked = QtCore.Signal()
    delete_action_invoked = QtCore.Signal()
    close_action_invoked = QtCore.Signal()

    catalogue_changed = QtCore.Signal(object)
    inspection_fields_changed = QtCore.Signal(int, InspectionData)
    data_source_changed = QtCore.Signal()
    spectral_lines_changed = QtCore.Signal()
    visible_columns_updated = QtCore.Signal(list)
    dock_layout_updated = QtCore.Signal(dict)
    viewer_configuration_updated = QtCore.Signal(DataWidgets)

    starred_state_updated = QtCore.Signal(bool, bool)
    screenshot_path_selected = QtCore.Signal(str)

    subset_loaded = QtCore.Signal(str, object)
    is_subset_inspection_paused = QtCore.Signal(bool)
    subset_inspection_stopped = QtCore.Signal()

    is_zen_mode_activated = QtCore.Signal(bool)

    def __init__(self,
                 config: Config | None = None,
                 cache: Cache | None = None,
                 widget_cfg: DataWidgets | None = None,
                 spectral_lines: SpectralLineData | None = None,
                 plugins: list[PluginCore] | None = None,
                 parent=None):

        super().__init__(parent)

        self.rd = AppData()

        self._config = config if config else Config()
        self._cache = cache if cache else Cache()
        self._widget_cfg = widget_cfg if widget_cfg else DataWidgets()
        self._spectral_lines = spectral_lines if spectral_lines else SpectralLineData()
        self._plugins: list[PluginCore] = plugins if plugins is not None else []

        self._object_loaded: bool = False
        self._t_load_object_start = None
        self._restart_requested: bool = False
        self._zen_mode_activated: bool = False
        self._was_maximized: bool = False

        self._subset_cat: Catalog | None = None
        self._subset_inspection_paused: bool = False

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._update_window_title()  # set the title of the main window
        # self.setWindowIcon(QtGui.QIcon('logo2_2.png'))

        # add a status bar
        # self.statusBar().showMessage("Message in the statusbar")

        QtWidgets.QShortcut('Ctrl+S', self, self.save_action_invoked.emit)
        QtWidgets.QShortcut('Ctrl+D', self, self.delete_action_invoked.emit)
        QtWidgets.QShortcut('Esc', self, lambda: self._exit_fullscreen() if self.isFullScreen() else None)

        self._data_viewer: DataViewer | None = None
        self._commands_bar: ToolBar | None = None
        self._quick_search: QuickSearch | None = None
        self._object_info: ObjectInfo | None = None
        self._inspection_res: InspectionResults | None = None
        self._subsets: Subsets | None = None

        self._quick_search_dock: QtWidgets.QDockWidget | None = None
        self._object_info_dock: QtWidgets.QDockWidget | None = None
        self._inspection_res_dock: QtWidgets.QDockWidget | None = None
        self._subsets_dock: QtWidgets.QDockWidget | None = None

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

        # load the subset to the memory
        if self._cache.last_subset_file:
            self.load_subset(reset_index=False)

        # read cache and try to load the last opened project
        if self._cache.last_inspection_file:
            self.open_file(self._cache.last_inspection_file, self._cache.last_object_index)

    def init_ui(self):
        # create a central widget
        self._data_viewer = DataViewer(self._config.data_viewer, self._config.data, self._widget_cfg,
                                       self._config.appearance, spectral_lines=self._spectral_lines,
                                       plugins=self._plugins, parent=self)

        # create a toolbar
        self._commands_bar = ToolBar(self._config.appearance, parent=self)
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
        self._inspection_res = InspectionResults(cfg=self._config.inspection_results, parent=self)
        self._inspection_res_dock = QtWidgets.QDockWidget('Inspection Results', self)
        self._inspection_res_dock.setObjectName('Inspection Results')
        self._inspection_res_dock.setWidget(self._inspection_res)

        # create a widget for inspecting a subset of objects
        self._subsets = Subsets(parent=self)
        self._subsets_dock = QtWidgets.QDockWidget('Subsets', self)
        self._subsets_dock.setObjectName('Subsets')
        self._subsets_dock.setWidget(self._subsets)

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

        self._export = QtWidgets.QAction("&Export FITS Table...")
        self._export.triggered.connect(self._export_action)
        self._export.setEnabled(False)
        self._file.addAction(self._export)

        self._file.addSeparator()

        self._quit = QtWidgets.QAction("&Quit")
        self._quit.triggered.connect(self.close)
        self._quit.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        self._file.addAction(self._quit)

        self._view = self._menu.addMenu("&View")

        self._reset_view = QtWidgets.QAction("Reset View")
        self._reset_view.setEnabled(False)
        self._reset_view.triggered.connect(self._data_viewer.reset_view)
        self._reset_view.setShortcut('R')
        self._view.addAction(self._reset_view)

        self._reset_dock_layout = QtWidgets.QAction("Reset Layout")
        self._reset_dock_layout.setEnabled(False)
        self._reset_dock_layout.triggered.connect(self._data_viewer.reset_dock_layout)
        self._view.addAction(self._reset_dock_layout)

        self._view.addSeparator()

        self._zen = QtWidgets.QAction("Enter Zen Mode")
        self._zen.triggered.connect(self._zen_mode_action)
        self._zen.setShortcut('H')
        self._auxiliary_docks = ()  # (self._quick_search_dock, self._object_info_dock, self._subsets_dock)
        self._view.addAction(self._zen)

        self._view.addSeparator()

        self._fullscreen = QtWidgets.QAction("Fullscreen")
        self._fullscreen.triggered.connect(self._fullscreen_action)
        self._fullscreen.setShortcut('F')
        self._view.addAction(self._fullscreen)

        self._widgets = self._menu.addMenu("&Widgets")

        self._backup_viewer_config = QtWidgets.QAction("Backup...")
        self._backup_viewer_config.triggered.connect(self._backup_viewer_config_action)
        self._widgets.addAction(self._backup_viewer_config)

        self._restore_viewer_config = QtWidgets.QAction("Restore...")
        self._restore_viewer_config.triggered.connect(self._restore_viewer_config_action)
        self._widgets.addAction(self._restore_viewer_config)

        self._tools = self._menu.addMenu("&Tools")

        self._inspect_subset = QtWidgets.QAction("Inspect Subset...")
        self._inspect_subset.triggered.connect(self._inspect_subset_action)
        self._tools.addAction(self._inspect_subset)

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
        for w in (self._data_viewer, self._commands_bar, self._quick_search, self._object_info, self._inspection_res,
                  self._subsets):
            self.project_loaded.connect(w.load_project)

        for w in (self._data_viewer, self._object_info, self._inspection_res):
            self.data_requested.connect(w.collect)

        self.loading_aborted.connect(self._data_viewer.abort_loading)

        self.catalogue_changed.connect(self._object_info.update_table_items)
        self.inspection_fields_changed.connect(self._inspection_res.update_inspection_fields)
        self.data_source_changed.connect(self._data_viewer.open_images)
        self.spectral_lines_changed.connect(self._data_viewer.spectral_lines_changed.emit)
        self.visible_columns_updated.connect(self._object_info.update_visible_columns)
        self.dock_layout_updated.connect(self._data_viewer.restore_dock_layout)
        self.viewer_configuration_updated.connect(self._data_viewer.update_viewer_configuration)

        self.starred_state_updated.connect(self._commands_bar.update_star_button_icon)
        self.screenshot_path_selected.connect(self._data_viewer.take_screenshot)

        self.subset_loaded.connect(self._subsets.load_subset)
        self.is_subset_inspection_paused.connect(self._subsets.pause_subset_inspection)
        self.subset_inspection_stopped.connect(self._subsets.stop_subset_inspection)

        self.save_action_invoked.connect(self._data_viewer.request_redshift)
        self.delete_action_invoked.connect(self._inspection_res.clear_redshift_value)
        self.close_action_invoked.connect(self._data_viewer.free_resources)

        self.is_zen_mode_activated.connect(self._data_viewer.enter_zen_mode)

        # connect the child widgets to the main window
        self._quick_search.id_selected.connect(self.load_by_id)
        self._quick_search.index_selected.connect(self.load_by_index)

        self._subsets.inspect_button_clicked.connect(self._inspect_subset_action)
        self._subsets.pause_inspecting_button_clicked.connect(self._pause_subset_inspection_action)
        self._subsets.stop_inspecting_button_clicked.connect(self._stop_subset_inspection_action)

        self._commands_bar.navigation_button_clicked.connect(self.switch_object)
        self._commands_bar.star_button_clicked.connect(self.update_starred_state)
        self._commands_bar.screenshot_button_clicked.connect(self._screenshot_action)
        self._commands_bar.settings_button_clicked.connect(self._settings_action)

        self._inspection_res.edit_button_clicked.connect(self._edit_inspection_file_action)

        self._data_viewer.object_loaded.connect(self.finalize_loading)

        self._data_viewer.data_collected.connect(self.save_viewer_data)
        self._object_info.data_collected.connect(self.save_obj_info_data)
        self._inspection_res.data_collected.connect(self.save_review_data)

        # connect the child widgets between each other
        self._data_viewer.redshift_obtained.connect(self._inspection_res.set_redshift_value)
        self._commands_bar.reset_view_button_clicked.connect(self._data_viewer.reset_view)
        self._commands_bar.reset_layout_button_clicked.connect(self._data_viewer.reset_dock_layout)

    def populate(self):
        self.setCentralWidget(self._data_viewer)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self._commands_bar)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._quick_search_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._object_info_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._inspection_res_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._subsets_dock)

    def load_catalogue(self):
        cat = Catalog.read(self._config.catalogue.filename, translate=self._config.catalogue.translate)
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
            self.rd.create(flags=self._config.inspection_results.default_flags)
            if self.rd.review is not None:
                self.load_project()
            else:
                self.update_catalogue(None)
                self.update_output_path(None)

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
            if self.rd.cat is None:
                self.update_catalogue(None)  # in case the catalogue hasn't been initialized before
            self.load_project(cached_index)
        else:
            logger.warning('Inspection file not found (path: {})'.format(path))

    def load_project(self, j: int | None = None):
        """ Update the state of the main window and activate the central widget after loading inspection data.
        """
        for w in (self._export, self._reset_view, self._reset_dock_layout):
            w.setEnabled(True)

        self.project_loaded.emit(self.rd.review)

        if j is None or (j < 0 or j >= self.rd.review.n_objects):
            j = 0

        self._object_loaded = False
        self.load_object(j)

    @QtCore.Slot(int)
    def load_object(self, j: int):
        """ Load a new object to the central widget.
        @param j: the index of the object to display
        """
        if self._object_loaded:
            self.data_requested.emit()
        else:
            self.loading_aborted.emit()

        self._object_loaded = False
        self._t_load_object_start = time.perf_counter()

        self.rd.j = j

        self._load_object(self._data_viewer)
        self._update_window_title()

    def _get_cat_entry(self) -> Catalog | None:
        if self.rd.j is None:
            return None

        obj_id = self.rd.review.get_id(self.rd.j, full=True)
        return self.rd.cat.get_cat_entry(obj_id)

    def _load_object(self, *widgets):
        for w in widgets:
            self.object_selected.connect(w.load_object)
        self.object_selected.emit(self.rd.j, self.rd.review, self._get_cat_entry())
        for w in widgets:
            self.object_selected.disconnect(w.load_object)

    @QtCore.Slot()
    def finalize_loading(self):
        self._load_object(self._commands_bar, self._inspection_res,self._subsets, self._object_info)
        self._object_loaded = True

        self._cache.last_object_index = self.rd.j
        self._cache.save()

        logger.info(f"Object loaded (ID: {self.rd.review.get_id(self.rd.j)}, loading time: {time.perf_counter()-self._t_load_object_start:.3f} s)")

    @QtCore.Slot(str, bool)
    def switch_object(self, command: str, switch_to_starred: bool):
        if command not in ('next', 'previous'):
            logger.error(f'Unknown command: {command}')
            return

        if switch_to_starred and not self.rd.review.has_data('starred'):
            logger.error('No starred objects found')
            return

        j_upd = self._update_index(self.rd.j, command)
        if self._subset_cat and not self._subset_inspection_paused:
            while True:
                subset_entry = self._subset_cat.get_cat_entry(self.rd.review.get_id(j_upd, full=True),
                                                              ignore_missing=True)
                if subset_entry is not None:
                    break

                j_upd = self._update_index(j_upd, command)
                if j_upd == self.rd.j:  # in case no other ID from the subset is found
                    logger.warning('No other IDs found in the subset')
                    break

        elif switch_to_starred:
            while not self.rd.review.get_value(j_upd, 'starred'):
                j_upd = self._update_index(j_upd, command)

        self.load_object(j_upd)

    def _update_index(self, obj_index: int, command: str) -> int:
        j_upd = obj_index

        if command == 'next':
            j_upd += 1
        elif command == 'previous':
            j_upd -= 1

        j_upd = j_upd % self.rd.review.n_objects
        return j_upd

    @QtCore.Slot(str)
    def load_by_id(self, obj_id: str):
        if self.rd.review.validate_id(obj_id):
            self.setFocus()
            self.load_object(self.rd.review.get_id_loc(obj_id))

    @QtCore.Slot(int)
    def load_by_index(self, index: int):
        if self.rd.review.validate_index(index):
            self.setFocus()
            self.load_object(index - 1)

    def _reload(self):
        if self.rd.j is not None:
            self.load_object(self.rd.j)

    def _update_window_title(self):
        title = ''
        if self.rd.output_path is not None:
            title += f'{self.rd.output_path.name} – '
        if self.rd.j is not None:
            obj_id = self.rd.review.get_id(self.rd.j, full=True)
            obj_id = obj_id if isinstance(obj_id, tuple) else (obj_id,)
            id_str = ', '.join(map(str, obj_id))
            title += f"ID {id_str} [#{self.rd.j + 1}/{self.rd.review.n_objects}] – "
        title += APPLICATION
        self.setWindowTitle(title)

    def _export_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Export To FITS',
                                           basedir=str(self.rd.output_path.with_suffix('.fits')),
                                           filters='FITS Files (*.fits)')[0]

        if path:
            self.rd.review.write(path, 'fits')

    def _restore_viewer_config_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Viewer Configuration',
                                           filters='YAML Files (*.yml)')[0]
        if path:
            new_viewer_cfg = self._widget_cfg.replace_params(pathlib.Path(path))
            if new_viewer_cfg is None:
                logger.error('Failed to restore the viewer configuration')
            else:
                self._widget_cfg = new_viewer_cfg
                self._widget_cfg.save()

                self.viewer_configuration_updated.emit(self._widget_cfg)

                self._reload()

                logger.info('Viewer configuration restored')

    def _backup_viewer_config_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Save Viewer Configuration',
                                           basedir=str(pathlib.Path() / 'data_widgets.yml'),
                                           filters='YAML Files (*.yml)')[0]

        if path:
            save_yaml(path, asdict(self._widget_cfg))
            logger.info('Viewer configuration saved')

    def _zen_mode_action(self):
        self._zen_mode_activated = not self._zen_mode_activated
        self._zen.setText("Exit Zen Mode" if self._zen_mode_activated else "Enter Zen Mode")
        for w in self._auxiliary_docks:
            w.setVisible(not self._zen_mode_activated)
        self.is_zen_mode_activated.emit(self._zen_mode_activated)

    @QtCore.Slot()
    def _fullscreen_action(self):
        if self.isFullScreen():
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        self._was_maximized = True if self.isMaximized() else False
        self.showFullScreen()

    def _exit_fullscreen(self):
        self.showNormal()
        if self._was_maximized:
            self.showMaximized()

    def _edit_inspection_file_action(self):
        dialog = InspectionFieldEditor(review=self.rd.review, parent=self)
        dialog.inspection_fields_updated.connect(self.update_inspection_fields)
        if dialog.exec():
            self.inspection_fields_changed.emit(self.rd.j, self.rd.review)

    def _inspect_subset_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Subset')[0]
        if path:
            self._cache.last_subset_file = path
            self._cache.save()
            self.load_subset()

    def load_subset(self, reset_index=True):
        subset_path = self._cache.last_subset_file
        subset = Catalog.read(subset_path, translate=self._config.catalogue.translate)
        if subset:
            subset.add_column(np.arange(len(subset)), name='__index__', index=0)

            self._subset_cat = subset
            self.subset_loaded.emit(subset_path, subset)

            if reset_index:
                self.load_by_id(self._subset_cat.get_col('id')[0])
        else:
            self._cache.last_subset_file = None
            self._cache.save()

    def _pause_subset_inspection_action(self):
        self._subset_inspection_paused = not self._subset_inspection_paused
        self.is_subset_inspection_paused.emit(self._subset_inspection_paused)

    def _stop_subset_inspection_action(self):
        self._subset_cat = None
        self._subset_inspection_paused = False

        self._cache.last_subset_file = None
        self._cache.save()

        self.subset_inspection_stopped.emit()

    def _screenshot_action(self):
        default_filename = f'{self.rd.output_path.stem.replace(" ", "_")}_ID{self.rd.review.get_id(self.rd.j)}.png'
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')
        if path:
            self.screenshot_path_selected.emit(path)

    def _settings_action(self):
        self._restart_requested = False

        dialog = Settings(self.rd.cat, self._config, self._spectral_lines, parent=self)

        dialog.appearance_changed.connect(self.update_appearance)
        dialog.catalogue_changed.connect(self.update_catalogue)
        dialog.spectral_lines_changed.connect(self.spectral_lines_changed.emit)
        dialog.data_source_changed.connect(self.data_source_changed.emit)

        dialog.restart_requested.connect(self.restart)

        if dialog.exec():
            if not self._restart_requested:
                self._reload()

    @QtCore.Slot()
    def update_appearance(self):
        setup_appearance(self._config.appearance, update_theme=False)

    @QtCore.Slot(object)
    def update_catalogue(self, cat: Catalog | None):
        if cat is None and self.rd.review is not None:
            self.rd.cat = Catalog.create(self.rd.review.ids_full)
        else:
            self.rd.cat = cat
        self.catalogue_changed.emit(self.rd.cat)

    @QtCore.Slot(pathlib.Path)
    def update_output_path(self, path: pathlib.Path | None):
        if self._object_loaded:
            self.data_requested.emit()

        self.rd.output_path = path
        self._cache.last_inspection_file = None if path is None else str(path)
        self._cache.save()
        self._update_window_title()

    @QtCore.Slot(list, list, bool)
    def update_inspection_fields(self, fields: list[tuple[str, str]], is_deleted: list[bool], set_as_default: bool):
        old_columns = self.rd.review.user_defined_columns
        for i, old_name in enumerate(old_columns):
            new_name = fields[i][0]
            if is_deleted[i]:
                self.rd.review.delete_column(column_name=old_name)
            elif old_name != new_name:
                self.rd.review.rename_column(old_name=old_name, new_name=new_name)

        for field in fields[len(old_columns):]:
            new_name, new_type = field[0], field[1]
            if new_type == 'boolean':
                self.rd.review.add_flag_column(column_name=new_name)

        if set_as_default:
            default_flags = self.rd.review.flag_columns
            self._config.inspection_results.default_flags = default_flags
            self._config.save()

    def _about_action(self):
        package_name: str = __package__.split('.')[0]

        msg = []
        msg.append(f"{package_name.capitalize()} v{metadata.version(package_name)}")
        msg.append(f"Copyright (c) 2025, Ivan Kramarenko, Josephine Kerutt")
        msg.append(f"\nProject's homepage: {metadata.metadata(package_name).get('Home-page')}")

        QtWidgets.QMessageBox.about(self, f"About {package_name.capitalize()}", '\n'.join(msg))

    def closeEvent(self, a0):
        if self.rd.j is not None:
            self.data_requested.emit()

        self.close_action_invoked.emit()

        # save the state and geometry of the main window
        if self._zen_mode_activated:
            self._zen_mode_action()
        settings = QtCore.QSettings()
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

        super().closeEvent(a0)

    @QtCore.Slot()
    def update_starred_state(self):
        starred = not self.rd.review.get_value(self.rd.j, 'starred')
        self.rd.review.update_value(self.rd.j, 'starred', starred)

        self.starred_state_updated.emit(starred, self.rd.review.has_data('starred'))

    @QtCore.Slot(dict)
    def save_viewer_data(self, layout: dict):
        self._cache.dock_layout = layout
        self._cache.save()

    @QtCore.Slot(list)
    def save_obj_info_data(self, visible_columns: list[str]):
        self._cache.visible_columns = visible_columns
        self._cache.save()

    @QtCore.Slot(float, str, dict)
    def save_review_data(self, redshift: float, comments: str, checkboxes: dict[str, bool]):
        self.rd.review.update_value(self.rd.j, 'z_sviz', redshift)
        self.rd.review.update_value(self.rd.j, 'comment', comments)
        for cname, is_checked in checkboxes.items():
            self.rd.review.update_value(self.rd.j, cname, is_checked)
        self.rd.save()

    @QtCore.Slot()
    def restart(self):
        self._restart_requested = True
        self.close()
        QtWidgets.QApplication.exit(MainWindow.EXIT_CODE_REBOOT)
