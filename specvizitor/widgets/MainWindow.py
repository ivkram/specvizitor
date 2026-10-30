import qtpy.compat
from qtpy import QtWidgets, QtCore, QtGui
import numpy as np

from dataclasses import asdict
from functools import partial
from importlib import metadata
import logging
import pathlib
import time

from .. import APPLICATION
from ..appdata import AppData
from ..config.appearance import setup_appearance
from ..config import Config, DataWidgets, Workspace, WorkspaceRegistry
from ..config.workspace import WORKSPACE_CONFIG_FILENAME
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..io.viewer_data import set_unit_aliases
from ..io.workspace_archive import (ARCHIVE_EXTENSION, export_workspace, import_workspace, inspect_archive,
                                   unset_paths)
from ..plugins.plugin_core import PluginCore
from ..utils.logs import qlog
from ..utils.params import save_yaml
from ..utils.paths import absolute_path

from .DataViewer import DataViewer
from .NavigationAction import Direction, NavigationAction
from .NewFile import NewFile
from .ObjectInfo import ObjectInfo
from .QuickSearch import QuickSearch
from .InspectionResults import InspectionResults
from .InspectionFieldEditor import InspectionFieldEditor
from .Subsets import Subsets
from .Settings import Settings
from .ToolBar import ToolBar
from .WorkspaceDialogs import (CloneWorkspaceDialog, ExportWorkspaceDialog, ForgetWorkspaceDialog,
                               ImportWorkspaceDialog, NewWorkspaceDialog, RenameWorkspaceDialog,
                               ResolvePathsDialog)

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    EXIT_CODE_REBOOT = -42

    # what `File -> Open...` accepts
    OPEN_FILTERS = ';;'.join((
        f'All Supported Files (*.csv {WORKSPACE_CONFIG_FILENAME} *{ARCHIVE_EXTENSION})',
        'Inspection Files (*.csv)',
        f'Workspaces ({WORKSPACE_CONFIG_FILENAME})',
        f'Workspace Archives (*{ARCHIVE_EXTENSION})',
    ))

    project_loaded = QtCore.Signal(InspectionData)
    object_loaded = QtCore.Signal(int, InspectionData, object)
    loading_aborted = QtCore.Signal()
    data_requested = QtCore.Signal()
    project_closed = QtCore.Signal()

    catalogue_updated = QtCore.Signal(object)
    inspection_fields_updated = QtCore.Signal(int, InspectionData)
    data_source_updated = QtCore.Signal()
    spectral_lines_updated = QtCore.Signal()
    visible_columns_updated = QtCore.Signal(list)
    dock_layout_updated = QtCore.Signal(dict)
    viewer_configuration_updated = QtCore.Signal(DataWidgets)

    screenshot_path_selected = QtCore.Signal(str)

    subset_loaded = QtCore.Signal(str, object)
    is_subset_inspection_paused = QtCore.Signal(bool)
    subset_inspection_stopped = QtCore.Signal()

    is_zen_mode_activated = QtCore.Signal(bool)

    def __init__(self,
                 config: Config | None = None,
                 workspace: Workspace | None = None,
                 registry: WorkspaceRegistry | None = None,
                 plugins: list[PluginCore] | None = None,
                 parent=None):

        super().__init__(parent)

        self.rd = AppData()

        self._config = config if config else Config()
        self._registry = registry if registry else WorkspaceRegistry()
        self._plugins: list[PluginCore] = plugins if plugins is not None else []

        self._ws = workspace if workspace is not None else Workspace(pathlib.Path())

        self._object_loaded: bool = False
        self._t_load_object_start = None
        self._restart_requested: bool = False
        self._zen_mode_activated: bool = False
        self._was_maximized: bool = False

        self._subset_cat: Catalog | None = None
        self._subset_inspection_paused: bool = False

        self._navigation_cfg: tuple[NavigationAction, ...]
        self._create_navigation_cfg()

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._update_window_title()

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

        if self._ws.layout.dock_layout:
            self.dock_layout_updated.emit(self._ws.layout.dock_layout)

        if self._ws.config.catalogue.filename:
            self.load_catalogue()

        # an empty list hides every column
        if self.rd.cat and self._ws.layout.visible_columns is not None:
            self.visible_columns_updated.emit(self._ws.layout.visible_columns)

        if self._ws.state.last_inspection_file:
            self.open_file(self._ws.state.last_inspection_file, self._ws.state.last_object_index)

        if self._ws.state.last_subset_file:
            self._load_subset(self._ws.state.last_subset_file, reset_index=False)

    def _create_navigation_cfg(self):
        self._navigation_cfg = (
            NavigationAction(Direction.NEXT, shortcut=QtGui.QKeySequence.MoveToNextChar),
            NavigationAction(Direction.PREVIOUS, shortcut=QtGui.QKeySequence.MoveToPreviousChar),
            NavigationAction(Direction.NEXT, starred_only=True),
            NavigationAction(Direction.PREVIOUS, starred_only=True)
        )

    def init_ui(self):
        self._data_viewer = DataViewer(self._config.data_viewer, self._ws.config.data, self._ws.widgets,
                                       self._config.appearance, spectral_lines=self._ws.spectral_lines,
                                       plugins=self._plugins, parent=self)
        
        self._commands_bar = ToolBar(tuple(self._navigation_cfg[i] for i in [3, 1, 0, 2]),
                                     self._config.appearance, parent=self)
        self._commands_bar.setObjectName('Toolbar')
        self._commands_bar.setEnabled(True)

        self._quick_search = QuickSearch(parent=self)
        self._quick_search_dock = QtWidgets.QDockWidget('Quick Search', self)
        self._quick_search_dock.setObjectName('Quick Search')
        self._quick_search_dock.setWidget(self._quick_search)

        self._object_info = ObjectInfo(parent=self)
        self._object_info_dock = QtWidgets.QDockWidget('Object Information', self)
        self._object_info_dock.setObjectName('Object Information')
        self._object_info_dock.setWidget(self._object_info)

        self._inspection_res = InspectionResults(cfg=self._ws.config.inspection_results, parent=self)
        self._inspection_res_dock = QtWidgets.QDockWidget('Inspection Results', self)
        self._inspection_res_dock.setObjectName('Inspection Results')
        self._inspection_res_dock.setWidget(self._inspection_res)

        self._subsets = Subsets(parent=self)
        self._subsets_dock = QtWidgets.QDockWidget('Subsets', self)
        self._subsets_dock.setObjectName('Subsets')
        self._subsets_dock.setWidget(self._subsets)
        self._subsets_dock.hide()

        self._init_menu()

        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

    def _init_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")
        self._init_file_menu()

        self._edit = self._menu.addMenu("&Edit")

        self._star_object = QtWidgets.QAction("Star Object")
        self._star_object.setEnabled(False)
        self._star_object.triggered.connect(self._inspection_res.star_object)
        self._star_object.setShortcut('S')
        self._edit.addAction(self._star_object)

        self._redshift_menu = QtWidgets.QMenu("&Redshift")
        self._redshift_menu.setEnabled(False)
        self._edit.addMenu(self._redshift_menu)

        self._save_redshift = QtWidgets.QAction("&Save")
        self._save_redshift.triggered.connect(self._data_viewer.request_redshift)
        self._save_redshift.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self._redshift_menu.addAction(self._save_redshift)

        self._clear_redshift = QtWidgets.QAction("Clear")
        self._clear_redshift.setEnabled(False)
        self._clear_redshift.triggered.connect(self._inspection_res.clear_redshift)
        self._clear_redshift.setShortcut(QtGui.QKeySequence('Ctrl+D'))
        self._redshift_menu.addAction(self._clear_redshift)

        self._edit.addSeparator()

        self._edit_inspection_fields = QtWidgets.QAction("Inspection &Fields...")
        self._edit_inspection_fields.setEnabled(False)
        self._edit_inspection_fields.triggered.connect(self._edit_inspection_fields_action)
        self._edit.addAction(self._edit_inspection_fields)

        self._view = self._menu.addMenu("&View")

        self._dock_menu = QtWidgets.QMenu("Docks")
        self._view.addMenu(self._dock_menu)

        self._dock_menu.addActions([
            self._quick_search_dock.toggleViewAction(),
            self._object_info_dock.toggleViewAction(),
            self._inspection_res_dock.toggleViewAction(),
            self._subsets_dock.toggleViewAction()
        ])
        self._dock_menu.addSeparator()
        self._dock_menu.addAction(self._commands_bar.toggleViewAction())

        self._view.addSeparator()

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

        self._zen = QtWidgets.QAction("Zen Mode")
        self._zen.triggered.connect(self._zen_mode_action)
        self._zen.setShortcut('H')
        self._auxiliary_docks = ()  # (self._quick_search_dock, self._object_info_dock, self._subsets_dock)
        self._view.addAction(self._zen)

        self._fullscreen = QtWidgets.QAction("Fullscreen")
        self._fullscreen.triggered.connect(self._fullscreen_action)
        self._fullscreen.setShortcut('F')
        self._view.addAction(self._fullscreen)

        self._navigate = self._menu.addMenu("&Navigate")
        self._navigation_actions: tuple[QtWidgets.QAction, ...] | None = None
        self._add_navigation_actions()

        self._widgets = self._menu.addMenu("&Widgets")

        self._backup_viewer_config = QtWidgets.QAction("Backup...")
        self._backup_viewer_config.triggered.connect(self._backup_viewer_config_action)
        self._widgets.addAction(self._backup_viewer_config)

        self._restore_viewer_config = QtWidgets.QAction("Restore...")
        self._restore_viewer_config.triggered.connect(self._restore_viewer_config_action)
        self._widgets.addAction(self._restore_viewer_config)

        self._tools = self._menu.addMenu("&Tools")

        self._inspect_subset = QtWidgets.QAction("Inspect Subset...")
        self._inspect_subset.setEnabled(False)
        self._inspect_subset.triggered.connect(self.inspect_subset_action)
        self._tools.addAction(self._inspect_subset)

        self._screenshot = QtWidgets.QAction("Take Screenshot...")
        self._screenshot.triggered.connect(self.screenshot_action)
        self._tools.addAction(self._screenshot)

        self._tools.addSeparator()

        self._settings = QtWidgets.QAction("Se&ttings...")
        self._settings.triggered.connect(self.settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...")
        self._about.triggered.connect(self._about_action)
        self._help.addAction(self._about)

    def _init_file_menu(self):
        self._new_file = QtWidgets.QAction("&New...")
        self._new_file.triggered.connect(self._new_file_action)
        self._new_file.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        self._file.addAction(self._new_file)

        self._new_workspace = QtWidgets.QAction("New &Workspace...")
        self._new_workspace.triggered.connect(self._new_workspace_action)
        self._file.addAction(self._new_workspace)

        self._open_file = QtWidgets.QAction("&Open...")
        self._open_file.triggered.connect(self._open_file_action)
        self._open_file.setShortcut(QtGui.QKeySequence('Ctrl+O'))
        self._file.addAction(self._open_file)

        # a child of the File menu, or Wayland refuses it as a popup of that menu
        self._recent_workspaces = self._file.addMenu("Recent Wor&kspaces")

        # created once, since the entries are rebuilt whenever the registry changes
        self._workspace_actions = QtWidgets.QActionGroup(self)
        self._workspace_actions.setExclusive(True)
        self._workspace_list_actions: list[QtWidgets.QAction] = []

        self._file.addSeparator()

        # actions on the current workspace
        self._clone_workspace = QtWidgets.QAction("&Clone Workspace...")
        self._clone_workspace.triggered.connect(self._clone_workspace_action)
        self._file.addAction(self._clone_workspace)

        self._rename_workspace = QtWidgets.QAction("&Rename Workspace...")
        self._rename_workspace.triggered.connect(self._rename_workspace_action)
        self._file.addAction(self._rename_workspace)

        self._export_workspace = QtWidgets.QAction("Ex&port Workspace...")
        self._export_workspace.triggered.connect(self._export_workspace_action)
        self._file.addAction(self._export_workspace)

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

        self._populate_workspace_list()

    def _populate_workspace_list(self):
        # delete the previous entries, otherwise their shortcuts stay active
        for action in self._workspace_list_actions:
            self._recent_workspaces.removeAction(action)
            self._workspace_actions.removeAction(action)
            action.setParent(None)
            action.deleteLater()
        self._workspace_list_actions = []

        known = self._registry.known
        if not known:
            placeholder = QtWidgets.QAction("(none)", self)
            placeholder.setEnabled(False)
            self._recent_workspaces.addAction(placeholder)
            self._workspace_list_actions.append(placeholder)
            return

        active = str(self._ws.path)
        for i, path in enumerate(known):
            name = Workspace.name_at(path)
            action = QtWidgets.QAction(f"{name}", self)
            action.setCheckable(True)
            action.setChecked(path == active)
            action.setToolTip(path)

            if not Workspace.is_workspace(path):
                # kept in the list (a network share may only be offline) and clickable, which offers
                # to remove them; no shortcut, so that it can't be triggered by accident
                action.setText(f"{name}  (unavailable)")
            elif i < 9:
                action.setShortcut(QtGui.QKeySequence(f'Ctrl+{i + 1}'))

            action.triggered.connect(partial(self.switch_workspace, path))
            self._workspace_actions.addAction(action)
            self._recent_workspaces.addAction(action)
            self._workspace_list_actions.append(action)

    @QtCore.Slot(str)
    def switch_workspace(self, path: str):
        if absolute_path(path) == self._ws.path:
            return

        if not Workspace.is_workspace(path):
            self._forget_unavailable_workspace(path)
            return

        self._registry.set_active(path)
        self._registry.save()

        logger.info(f"Switching workspace (path: {path})")
        self.restart()

    def _forget_unavailable_workspace(self, path: str):
        if ForgetWorkspaceDialog(path, parent=self).exec():
            self._registry.forget(path)
            self._registry.save()
            logger.info(f"Workspace removed from the list (path: {path})")

        self._populate_workspace_list()

    @QtCore.Slot()
    @qlog
    def _new_workspace_action(self):
        dialog = NewWorkspaceDialog(self._registry, parent=self)
        if not dialog.exec():
            return

        workspace = Workspace.create(dialog.workspace_path, name=dialog.workspace_name)
        if workspace is None:
            return

        self.switch_workspace(str(workspace.path))

    def _open_workspace(self, path: str):
        if not Workspace.is_workspace(path):
            logger.error(f"Not a workspace: no {WORKSPACE_CONFIG_FILENAME} found (path: {path})")
            return

        if not self._registry.validate_name(Workspace.name_at(path), path=path):
            return

        self.switch_workspace(path)

    def _import_workspace(self, archive: str):
        if inspect_archive(archive) is None:
            return

        dialog = ImportWorkspaceDialog(self._registry, archive, parent=self)
        if not dialog.exec():
            return

        imported = import_workspace(archive, dialog.workspace_path)
        if imported is None:
            return

        imported.rename(dialog.workspace_name)
        if unset_paths(imported.config):
            ResolvePathsDialog(imported, parent=self).exec()
        self.switch_workspace(str(imported.path))

    @QtCore.Slot()
    @qlog
    def _rename_workspace_action(self):
        dialog = RenameWorkspaceDialog(self._registry, self._ws, parent=self)
        if not dialog.exec():
            return

        if dialog.workspace_name == self._ws.name:
            return

        self._ws.rename(dialog.workspace_name)
        self._update_window_title()
        self._populate_workspace_list()

    @QtCore.Slot()
    @qlog
    def _clone_workspace_action(self):
        dialog = CloneWorkspaceDialog(self._registry, self._ws, parent=self)
        if not dialog.exec():
            return

        copied = self._ws.copy(dialog.workspace_path, name=dialog.workspace_name)
        if copied is None:
            return

        self.switch_workspace(str(copied.path))

    @QtCore.Slot()
    @qlog
    def _export_workspace_action(self):
        dialog = ExportWorkspaceDialog(self._ws, parent=self)
        if not dialog.exec():
            return

        # the inspection results may be exported
        if self._object_loaded:
            self.data_requested.emit()

        export_workspace(self._ws, dialog.destination, dialog.options)

    def _add_navigation_actions(self):
        navigation_actions = []

        for i, action_cfg in enumerate(self._navigation_cfg):
            action = QtWidgets.QAction(action_cfg.name)
            action.triggered.connect(partial(self.switch_object, action_cfg))
            if action_cfg.shortcut is not None:
                action.setShortcut(action_cfg.shortcut)

            navigation_actions.append(action)
            self._navigate.addAction(action)

            if i % 2 == 1 and i != len(self._navigation_cfg) - 1:
                self._navigate.addSeparator()

        self._navigation_actions = tuple(navigation_actions)

    def connect(self):
        # connect the main window to the child widgets
        for w in (self._data_viewer, self._commands_bar, self._quick_search, self._object_info, self._inspection_res,
                  self._subsets):
            self.project_loaded.connect(w.load_project)

        self.loading_aborted.connect(self._data_viewer.abort_loading)

        for w in (self._data_viewer, self._object_info, self._inspection_res):
            self.data_requested.connect(w.collect_data)

        self.project_closed.connect(self._data_viewer.free_resources)

        self.catalogue_updated.connect(self._object_info.update_table_items)
        self.catalogue_updated.connect(self._data_viewer.receive_catalog)
        self.inspection_fields_updated.connect(self._inspection_res.update_inspection_fields)
        self.data_source_updated.connect(self._data_viewer.open_images)
        self.spectral_lines_updated.connect(self._data_viewer.spectral_lines_updated.emit)
        self.visible_columns_updated.connect(self._object_info.update_visible_columns)
        self.dock_layout_updated.connect(self._data_viewer.update_dock_layout)
        self.viewer_configuration_updated.connect(self._data_viewer.update_viewer_configuration)

        self.screenshot_path_selected.connect(self._data_viewer.take_screenshot)

        self.subset_loaded.connect(self._subsets.load_subset)
        self.is_subset_inspection_paused.connect(self._subsets.pause_subset_inspection)
        self.subset_inspection_stopped.connect(self._subsets.stop_subset_inspection)

        self.is_zen_mode_activated.connect(self._data_viewer.activate_zen_mode)

        # connect the child widgets to the main window
        self._quick_search.id_selected.connect(self.load_by_id)
        self._quick_search.index_selected.connect(self.load_by_index)

        self._subsets.inspect_button_clicked.connect(self.inspect_subset_action)
        self._subsets.pause_inspecting_button_clicked.connect(self.pause_subset_inspection)
        self._subsets.stop_inspecting_button_clicked.connect(self.stop_subset_inspection)

        self._commands_bar.navigation_action_triggered.connect(self.switch_object)
        self._commands_bar.screenshot_action_triggered.connect(self.screenshot_action)
        self._commands_bar.settings_action_triggered.connect(self.settings_action)

        self._inspection_res.object_starred.connect(self.star_object)
        self._inspection_res.first_object_starred.connect(self.update_navigation_actions)
        self._inspection_res.redshift_set.connect(self._clear_redshift.setEnabled)

        self._data_viewer.object_loaded.connect(self.finalize_loading)
        self._data_viewer.id_selected.connect(self.load_by_id)

        self._data_viewer.data_collected.connect(self.save_viewer_data)
        self._object_info.data_collected.connect(self.save_obj_info_data)
        self._inspection_res.data_collected.connect(self.save_review_data)

        # connect the child widgets between each other
        self._data_viewer.redshift_collected.connect(self._inspection_res.set_redshift)
        self._commands_bar.star_action_triggered.connect(self._inspection_res.star_object)
        self._commands_bar.reset_view_action_triggered.connect(self._data_viewer.reset_view)
        self._commands_bar.reset_layout_action_triggered.connect(self._data_viewer.reset_dock_layout)
        self._inspection_res.object_starred.connect(self._commands_bar.star_object)
        self._inspection_res.first_object_starred.connect(self._commands_bar.update_navigation_actions)

    def populate(self):
        self.setCentralWidget(self._data_viewer)

        self.addToolBar(QtCore.Qt.TopToolBarArea, self._commands_bar)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._quick_search_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._object_info_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._inspection_res_dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._subsets_dock)

    def load_catalogue(self):
        cat = Catalog.read(self._ws.config.catalogue.filename, translate=self._ws.config.catalogue.translate)
        if cat is None:
            self._ws.config.catalogue.filename = None
            self._ws.config.save()

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
        dialog = NewFile(cfg=self._ws.config, parent=self)
        dialog.catalogue_changed.connect(self.update_catalogue)
        dialog.output_path_selected.connect(self.update_output_path)
        if dialog.exec():
            self.rd.create(flags=self._ws.config.inspection_results.default_flags)
            if self.rd.review is not None:
                self.load_project()
            else:
                self.update_catalogue(None)
                self.update_output_path(None)

    @QtCore.Slot()
    @qlog
    def _open_file_action(self):
        """ Open an inspection file, a workspace or a workspace archive via QFileDialog.
        """
        path = qtpy.compat.getopenfilename(self, caption='Open Inspection File or Workspace', filters=self.OPEN_FILTERS)[0]
        if path:
            self.open_path(path)

    @QtCore.Slot(str)
    def open_path(self, path: str):
        """ Open an inspection file, a workspace (its directory or workspace.yml) or a workspace archive.
        """
        path = pathlib.Path(path)

        if path.suffix == ARCHIVE_EXTENSION:
            self._import_workspace(str(path))
        elif path.name == WORKSPACE_CONFIG_FILENAME:
            self._open_workspace(str(path.parent))
        elif Workspace.is_workspace(path):
            self._open_workspace(str(path))
        else:
            self.open_file(str(path))

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
        for w in (self._export, self._redshift_menu, self._star_object, self._edit_inspection_fields, self._reset_view,
                  self._reset_dock_layout, self._inspect_subset):
            w.setEnabled(True)
        self.update_navigation_actions(self.rd.review.has_data("starred"))

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

    def _load_object(self, *widgets):
        for w in widgets:
            self.object_loaded.connect(w.load_object)

        obj_id = self.rd.review.get_id(self.rd.j, full=True)
        cat_entry = self.rd.cat.get_cat_entry(obj_id)

        self.object_loaded.emit(self.rd.j, self.rd.review, cat_entry)
        for w in widgets:
            self.object_loaded.disconnect(w.load_object)

    @QtCore.Slot()
    def finalize_loading(self):
        self._load_object(self._commands_bar, self._inspection_res,self._subsets, self._object_info)
        self._object_loaded = True

        self._ws.state.last_object_index = self.rd.j
        self._ws.state.save()

        logger.info(f"Object loaded (ID: {self.rd.review.get_id(self.rd.j)}, loading time: {time.perf_counter()-self._t_load_object_start:.3f} s)")

    @QtCore.Slot(NavigationAction)
    def switch_object(self, action: NavigationAction):
        if action.starred_only and not self.rd.review.has_data("starred"):
            logger.error("No starred objects found")
            return

        j_upd = self._update_index(self.rd.j, action.direction)
        subset_only = self._subset_cat and not self._subset_inspection_paused

        while True:
            update_index = False

            if action.starred_only and not self.rd.review.get_value(j_upd, 'starred'):
                update_index = True

            if subset_only:
                subset_entry = self._subset_cat.get_cat_entry(self.rd.review.get_id(j_upd, full=True),
                                                              ignore_missing=True)
                if subset_entry is None:
                    update_index = True

            if not update_index:
                break

            j_upd = self._update_index(j_upd, action.direction)
            if j_upd == self.rd.j:  # did the full cycle
                logger.warning(f"No (other) objects with requested properties found (starred: {action.starred_only}, "
                               f"included in the subset: {subset_only})")
                break

        self.load_object(j_upd)

    def _update_index(self, obj_index: int, command: Direction) -> int:
        j_upd = obj_index

        if command is Direction.NEXT:
            j_upd += 1
        elif command is Direction.PREVIOUS:
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
        if self._ws is not None and self._ws.name:
            title += f' [{self._ws.name}]'
        self.setWindowTitle(title)

    def _export_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Export To FITS',
                                           basedir=str(self.rd.output_path.with_suffix('.fits')),
                                           filters='FITS Files (*.fits)')[0]

        if path:
            self.rd.review.write(path, 'fits')

    @QtCore.Slot(bool)
    def star_object(self, starred: bool):
        self._star_object.setText("Unstar object" if starred else "Star object")

    @QtCore.Slot(bool)
    def update_navigation_actions(self, has_starred: bool):
        for action_cfg, action in zip(self._navigation_cfg, self._navigation_actions):
            if action_cfg.starred_only:
                action.setEnabled(has_starred)

    def _restore_viewer_config_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Viewer Configuration',
                                           filters='YAML Files (*.yml)')[0]
        if path:
            new_viewer_cfg = self._ws.widgets.replace_params(pathlib.Path(path))
            if new_viewer_cfg is None:
                logger.error('Failed to restore the viewer configuration')
            else:
                self._ws.widgets = new_viewer_cfg
                self._ws.widgets.save()

                self.viewer_configuration_updated.emit(self._ws.widgets)

                self._reload()

                logger.info('Viewer configuration restored')

    def _backup_viewer_config_action(self):
        path = qtpy.compat.getsavefilename(self, caption='Save Viewer Configuration',
                                           basedir=str(pathlib.Path() / 'data_widgets.yml'),
                                           filters='YAML Files (*.yml)')[0]

        if path:
            save_yaml(path, asdict(self._ws.widgets))
            logger.info('Viewer configuration saved')

    def _zen_mode_action(self):
        self._zen_mode_activated = not self._zen_mode_activated
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

    def _edit_inspection_fields_action(self):
        dialog = InspectionFieldEditor(review=self.rd.review, parent=self)
        dialog.inspection_fields_updated.connect(self.update_inspection_fields)
        if dialog.exec():
            self.inspection_fields_updated.emit(self.rd.j, self.rd.review)

    @QtCore.Slot()
    def inspect_subset_action(self):
        path = qtpy.compat.getopenfilename(self, caption='Open Subset')[0]
        if path:
            self._load_subset(path)

    def _load_subset(self, path: str, reset_index=True):
        if self.rd.review is None:
            self._clear_last_subset_file()
            return

        subset = Catalog.read(path, translate=self._ws.config.catalogue.translate)

        if subset is None:
            self._clear_last_subset_file()
            return

        subset.add_column(np.arange(len(subset)), name='__index__', index=0)

        self._subset_cat = subset
        self._ws.state.last_subset_file = path
        self._ws.state.save()
        self.subset_loaded.emit(path, subset)

        if reset_index:
            self.load_by_id(self._subset_cat.get_col('id')[0])

    @QtCore.Slot()
    def pause_subset_inspection(self):
        self._subset_inspection_paused = not self._subset_inspection_paused
        self.is_subset_inspection_paused.emit(self._subset_inspection_paused)

    @QtCore.Slot()
    def stop_subset_inspection(self):
        self._subset_cat = None
        self._subset_inspection_paused = False

        self._clear_last_subset_file()

        self.subset_inspection_stopped.emit()

    def _clear_last_subset_file(self):
        self._ws.state.last_subset_file = None
        self._ws.state.save()

    @QtCore.Slot()
    def screenshot_action(self):
        default_filename = f'{self.rd.output_path.stem.replace(" ", "_")}_ID{self.rd.review.get_id(self.rd.j)}.png'
        screenshot_location = self._config.data_viewer.default_screenshot_location
        basedir = str(absolute_path(screenshot_location if screenshot_location is not None else "") / default_filename)
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As', basedir=basedir, filters='Images (*.png)')
        if path:
            self.screenshot_path_selected.emit(path)

    @QtCore.Slot()
    def settings_action(self):
        self._restart_requested = False

        dialog = Settings(self.rd.cat, self._config, self._ws.config, self._ws.spectral_lines, parent=self)

        dialog.appearance_changed.connect(self.update_appearance)
        dialog.catalogue_changed.connect(self.update_catalogue)
        dialog.spectral_lines_changed.connect(self.spectral_lines_updated.emit)
        dialog.data_source_changed.connect(self.data_source_updated.emit)
        dialog.unit_aliases_changed.connect(self.update_unit_aliases)

        dialog.restart_requested.connect(self.restart)

        if dialog.exec():
            if not self._restart_requested:
                self._reload()

    @QtCore.Slot()
    def update_unit_aliases(self):
        set_unit_aliases(self._ws.config.data.enabled_unit_aliases)

    @QtCore.Slot()
    def update_appearance(self):
        setup_appearance(self._config.appearance, update_theme=False)
        self._data_viewer.update_appearance()

    @QtCore.Slot(object)
    def update_catalogue(self, cat: Catalog | None):
        if cat is None and self.rd.review is not None:
            self.rd.cat = Catalog.create(self.rd.review.ids_full)
        else:
            self.rd.cat = cat
        self.catalogue_updated.emit(self.rd.cat)

    @QtCore.Slot(pathlib.Path)
    def update_output_path(self, path: pathlib.Path | None):
        if self._object_loaded:
            self.data_requested.emit()

        self.rd.output_path = path
        self._ws.state.last_inspection_file = None if path is None else str(path)
        self._ws.state.save()
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
            self._ws.config.inspection_results.default_flags = default_flags
            self._ws.config.save()

    def _about_action(self):
        package_name: str = __package__.split('.')[0]

        msg = []
        msg.append(f"{package_name.capitalize()} v{metadata.version(package_name)}")
        msg.append("Copyright (c) 2025, Ivan Kramarenko, Josephine Kerutt")
        msg.append(f"\nProject's homepage: {metadata.metadata(package_name).get('Home-page')}")

        QtWidgets.QMessageBox.about(self, f"About {package_name.capitalize()}", '\n'.join(msg))

    def closeEvent(self, a0):
        if self.rd.j is not None:
            self.data_requested.emit()

        self.project_closed.emit()

        # save the state and geometry of the main window
        if self._zen_mode_activated:
            self._zen_mode_action()
        settings = QtCore.QSettings()
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

        super().closeEvent(a0)

    @QtCore.Slot(dict)
    def save_viewer_data(self, layout: dict):
        self._ws.layout.dock_layout = layout
        self._ws.layout.save()

    @QtCore.Slot(list)
    def save_obj_info_data(self, visible_columns: list[str]):
        self._ws.layout.visible_columns = visible_columns
        self._ws.layout.save()

    @QtCore.Slot(bool, float, str, dict)
    def save_review_data(self, starred: bool, redshift: float, comments: str, checkboxes: dict[str, bool]):
        self.rd.review.update_value(self.rd.j, "starred", starred)
        self.rd.review.update_value(self.rd.j, "z_sviz", redshift)
        self.rd.review.update_value(self.rd.j, "comment", comments)
        for cname, is_checked in checkboxes.items():
            self.rd.review.update_value(self.rd.j, cname, is_checked)
        self.rd.save()

    @QtCore.Slot()
    def restart(self):
        self._restart_requested = True
        self.close()
        QtWidgets.QApplication.exit(MainWindow.EXIT_CODE_REBOOT)
