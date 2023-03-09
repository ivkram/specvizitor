import pathlib
import argparse
import sys
import logging
from importlib.metadata import version

from platformdirs import user_config_dir, user_cache_dir

import pyqtgraph as pg
import qtpy.compat
from qtpy import QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot

from .runtime.appdata import AppData, Config, Cache
from .menu import NewFile, Settings
from .widgets import (AbstractWidget, DataViewer, ControlPanel, ObjectInfo, ReviewForm)
from .utils.widget_tools import get_widgets
from .utils.logs import LogMessageBox
from .utils.params import LocalFile


logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    project_loaded = Signal()

    def __init__(self, appdata: AppData, parent=None):
        self.rd = appdata

        super().__init__(parent)

        self.setWindowTitle('Specvizitor')      # set the title of the main window
        # self.setWindowIcon(QtGui.QIcon('logo2_2.png'))

        # add a menu bar
        self._init_menu()

        # add a status bar
        # self.statusBar().showMessage("Message in statusbar.")

        # create the central widget
        self.central_widget = CentralWidget(self.rd, parent=self)
        self.project_loaded.connect(self.central_widget.activate)
        self.setCentralWidget(self.central_widget)
        self.central_widget.init_ui()

        self._reset_view.triggered.connect(self.central_widget.data_viewer.reset_view)
        self._reset_dock_state.triggered.connect(self.central_widget.data_viewer.reset_dock_state)

        # read cache and try to load the last active project
        if self.rd.cache.last_inspection_file:
            self.load_project(self.rd.cache.last_inspection_file)

        self.showMaximized()
        self.was_maximized: bool

    def _init_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_file = QtWidgets.QAction("&New...", parent=self)
        self._new_file.triggered.connect(self._new_file_action)
        self._new_file.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        self._file.addAction(self._new_file)

        self._open_file = QtWidgets.QAction("&Open...", parent=self)
        self._open_file.triggered.connect(self._open_file_action)
        self._open_file.setShortcut(QtGui.QKeySequence('Ctrl+O'))
        self._file.addAction(self._open_file)

        self._file.addSeparator()

        self._save = QtWidgets.QAction("&Save...", parent=self)
        self._save.triggered.connect(self._save_action)
        self._save.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self._save.setEnabled(False)
        self._file.addAction(self._save)

        self._save_as = QtWidgets.QAction("Save As...", parent=self)
        self._save_as.triggered.connect(self._save_as_action)
        self._save_as.setShortcut(QtGui.QKeySequence('Shift+Ctrl+S'))
        self._save_as.setEnabled(False)
        self._file.addAction(self._save_as)

        self._export = QtWidgets.QAction("&Export...", parent=self)
        self._export.triggered.connect(self._export_action)
        self._export.setEnabled(False)
        self._file.addAction(self._export)

        self._file.addSeparator()

        self._quit = QtWidgets.QAction("&Quit...", parent=self)
        self._quit.triggered.connect(self._exit_action)
        self._quit.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        self._file.addAction(self._quit)

        self._view = self._menu.addMenu("&View")

        self._reset_view = QtWidgets.QAction("Reset View", parent=self)
        self._view.addAction(self._reset_view)

        self._reset_dock_state = QtWidgets.QAction("Reset Dock State", parent=self)
        self._view.addAction(self._reset_dock_state)

        self._view.addSeparator()

        self._fullscreen = QtWidgets.QAction("Fullscreen", parent=self)
        self._fullscreen.triggered.connect(lambda: self._exit_fullscreen() if self.isFullScreen() else self._enter_fullscreen())
        self._fullscreen.setShortcut('F11')
        self._view.addAction(self._fullscreen)

        self._shortcut_fullscreen = QtWidgets.QShortcut('Esc', self)
        self._shortcut_fullscreen.activated.connect(lambda: self._exit_fullscreen() if self.isFullScreen() else None)

        self._tools = self._menu.addMenu("&Tools")
        self._settings = QtWidgets.QAction("Se&ttings...", parent=self)
        self._settings.triggered.connect(self._settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...", parent=self)
        self._about.triggered.connect(self._about_action)
        self._help.addAction(self._about)

    def _new_file_action(self):
        """ Create a new inspection file via the NewFile dialog.
        """
        dialog = NewFile(self.rd, parent=self)
        if dialog.exec():
            self.rd.cache.last_object_index = 0
            self.activate()

    def _open_file_action(self):
        """ Open an existing inspection file via QFileDialog.
        """
        path = qtpy.compat.getopenfilename(self, caption='Open Inspection File', filters='CSV Files (*.csv)')[0]
        if path:
            self.rd.cache.last_object_index = 0
            self.load_project(path)

    def load_project(self, path: str):
        """ Load inspection data from an existing inspection file.
        @param path: path to the inspection file
        """
        if pathlib.Path(path).exists():
            self.rd.output_path = pathlib.Path(path)
            self.rd.read()
            self.activate()
        else:
            logger.warning('Inspection file not found (path: {})'.format(path))

    def activate(self):
        """ Update the state of the main window and activate the central widget after loading inspection data.
        """
        for w in (self._save, self._save_as, self._export):
            w.setEnabled(True)
        self.setWindowTitle('{} – Specvizitor'.format(self.rd.output_path.name))
        self.project_loaded.emit()

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
            self.rd.save()  # auto-save
        self.central_widget.data_viewer.save_dock_state()  # save the dock state
        self.close()
        logger.info("Application closed")

    def _enter_fullscreen(self):
        self.was_maximized = True if self.isMaximized() else False
        self.showFullScreen()

    def _exit_fullscreen(self):
        self.showNormal()
        if self.was_maximized:
            self.showMaximized()

    def _settings_action(self):
        dialog = Settings(self.rd, parent=self)
        if dialog.exec() and self.rd.df is not None:
            self.central_widget.data_viewer.load_object()
            self.central_widget.object_info.load_object()

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v{}".format(version('specvizitor')))

    def closeEvent(self, _):
        self._exit_action()


class CentralWidget(QtWidgets.QWidget):
    def __init__(self, rd: AppData, parent=None):
        self.rd = rd
        super().__init__(parent)

        # set up the layout
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setSpacing(10)
        self.setLayout(self.layout)

        # add a widget for the data viewer
        self.data_viewer = DataViewer(self.rd, cfg=self.rd.config.viewer, plugins=self.rd.config.plugins, parent=self)
        self.layout.addWidget(self.data_viewer, 1, 1, 3, 1)

        # add a widget for the control panel
        self.control_panel = ControlPanel(self.rd, cfg=self.rd.config.control_panel, parent=self)
        self.layout.addWidget(self.control_panel, 1, 2, 1, 1)

        # add a widget for displaying information about the object
        self.object_info = ObjectInfo(self.rd, cfg=self.rd.config.object_info, parent=self)
        self.layout.addWidget(self.object_info, 2, 2, 1, 1)

        # add a widget for writing comments
        self.review_form = ReviewForm(self.rd, cfg=self.rd.config.review_form, parent=self)
        self.layout.addWidget(self.review_form, 3, 2, 1, 1)

        # connect signals from the control panel to the slots of the central widget
        self.control_panel.object_selected.connect(self.load_object)
        self.control_panel.reset_view_button_clicked.connect(self.data_viewer.reset_view)
        self.control_panel.reset_dock_state_button_clicked.connect(self.data_viewer.reset_dock_state)
        self.control_panel.screenshot_button_clicked.connect(self.data_viewer.take_screenshot)

    @property
    def widgets(self) -> list[AbstractWidget]:
        """
        @return: a list of widgets added to the central widget.
        """
        return get_widgets(self.layout)

    def init_ui(self):
        for widget in self.widgets:
            widget.init_ui()

    @Slot(int)
    def load_object(self, j: int):
        """ Load a new object to the central widget.
        @param j: the index of the object to display
        """
        if self.rd.j is not None:
            # update the application data from widgets
            self.review_form.dump()

            self.rd.save()  # auto-save

        self.rd.j = j

        for widget in (self.control_panel, self.object_info, self.review_form, self.data_viewer):
            widget.load_object()

        # cache the index of the object
        # TODO: cache the ID instead of the index
        self.rd.cache.last_object_index = j
        self.rd.cache.save()

    @Slot()
    def activate(self):
        """ Activate the central widget.
        """
        for widget in self.widgets:
            widget.activate()

        # cache the inspection file name
        self.rd.cache.last_inspection_file = str(self.rd.output_path)
        self.rd.cache.save()

        # try to display the object with an index stored in cache
        j = self.rd.cache.last_object_index
        if j and j < self.rd.n_objects:
            self.load_object(int(j))
        else:
            self.load_object(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--purge', action='store_true')

    args = parser.parse_args()

    # logging configuration
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    user_files = {
        'config': LocalFile(user_config_dir('specvizitor'), full_name='Configuration file'),
        'cache': LocalFile(user_cache_dir('specvizitor'), full_name='Cache', auto_backup=False)
    }

    if args.purge:
        for f in user_files.values():
            f.delete()

    # initialize the app configuration and cache
    config = Config.read_user_params(user_files['config'], default='default_config.yml')
    cache = Cache.read_user_params(user_files['cache'])

    # initialize the app data
    appdata = AppData(config=config, cache=cache)

    # pyqtgraph configuration
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    pg.setConfigOption('imageAxisOrder', 'row-major')
    pg.setConfigOption('antialias', appdata.config.appearance.antialiasing)

    # start the application
    app = QtWidgets.QApplication(sys.argv)
    logger.info("Application started")

    # initialize the main window
    window = MainWindow(appdata=appdata)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
