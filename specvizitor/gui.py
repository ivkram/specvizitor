import pathlib
import argparse
import sys
import logging
from importlib.metadata import version

import pyqtgraph as pg
import qtpy.compat
from qtpy import QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot

from .runtime.appdata import AppData
from .menu import NewFile
from .widgets import (AbstractWidget, DataViewer, ControlPanel, ObjectInfo, ReviewForm)
from .utils.widgets import get_widgets
from .utils.logs import LogMessageBox


logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    project_loaded = Signal()

    def __init__(self, runtime: AppData, parent=None):
        self.rd = runtime

        super().__init__(parent)

        self.setGeometry(600, 500, 2550, 1450)  # set the position and the size of the main window
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

        # read cache and try to load the last active project
        if self.rd.cache.last_inspection_file:
            self.load_project(self.rd.cache.last_inspection_file)

    def _init_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_file = QtWidgets.QAction("&New...")
        self._new_file.triggered.connect(self._new_file_action)
        self._file.addAction(self._new_file)

        self._open_file = QtWidgets.QAction("&Open...")
        self._open_file.triggered.connect(self._open_file_action)
        self._file.addAction(self._open_file)

        self._file.addSeparator()

        self._save = QtWidgets.QAction("&Save...")
        self._save.triggered.connect(self._save_action)
        self._save.setEnabled(False)
        self._file.addAction(self._save)

        self.shortcut_close = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+S'), self)
        self.shortcut_close.activated.connect(self._save_action)

        self._save_as = QtWidgets.QAction("Save As...")
        self._save_as.triggered.connect(self._save_as_action)
        self._save_as.setEnabled(False)
        self._file.addAction(self._save_as)

        self._export = QtWidgets.QAction("&Export...")
        self._export.triggered.connect(self._export_action)
        self._export.setEnabled(False)
        self._file.addAction(self._export)

        self._file.addSeparator()

        self._exit = QtWidgets.QAction("E&xit...")
        self._exit.triggered.connect(self._exit_action)
        self._file.addAction(self._exit)

        self._tools = self._menu.addMenu("&Tools")
        self._settings = QtWidgets.QAction("Se&ttings...")
        self._settings.triggered.connect(self._settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...")
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
        msg = 'The data is saved automatically'
        if self.rd.output_path is not None:
            msg += ' to {}'.format(self.rd.output_path)
        LogMessageBox(logging.INFO, msg, parent=self)

    def _save_as_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _export_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _exit_action(self):
        self.rd.save()  # auto-save
        self.central_widget.data_viewer.save_dock_state()  # save the dock state
        self.close()
        logger.info("Application closed")

    def _settings_action(self):
        QtWidgets.QMessageBox.information(self, "Settings",
                                          "Configuration file: {}\n\nCache: {}".
                                          format(self.rd.config_file.path, self.rd.cache_file.path))

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v{}".format(version('specvizitor')))

    def closeEvent(self, _):
        self._exit_action()


class CentralWidget(QtWidgets.QWidget):
    def __init__(self, rd: AppData, parent=None):
        self.rd = rd
        super().__init__(parent)

        # set up the layout
        self.layout = QtWidgets.QGridLayout()
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
        self.control_panel.reset_button_clicked.connect(self.data_viewer.reset_view)
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

        for widget in self.widgets:
            widget.load_object()

        # cache the index of the object
        # TODO: cache the ID instead of the index
        self.rd.cache.last_object_index = j
        self.rd.cache.save(self.rd.cache_file)

    @Slot()
    def activate(self):
        """ Activate the central widget.
        """
        for widget in self.widgets:
            widget.activate()

        # cache the inspection file name
        self.rd.cache.last_inspection_file = str(self.rd.output_path)
        self.rd.cache.save(self.rd.cache_file)

        # try to display the object with an index stored in cache
        j = self.rd.cache.last_object_index
        if j and j < self.rd.n_objects:
            self.load_object(int(j))
        else:
            self.load_object(0)


def main():
    parser = argparse.ArgumentParser()

    # logging configuration
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    # initialize the application data
    runtime = AppData()

    # pyqtgraph configuration
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    pg.setConfigOption('antialias', runtime.config.gui.antialiasing)

    # start the application
    app = QtWidgets.QApplication(sys.argv)
    logger.info("Application started")

    # initialize the main window
    window = MainWindow(runtime=runtime)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
