import pathlib
import argparse
import sys
import logging
from importlib.metadata import version

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtWidgets

from .runtime import RuntimeData
from .menu import NewFile
from .widgets import (AbstractWidget, DataViewer, ControlPanel, ObjectInfo, ReviewForm)
from .utils.widgets import get_widgets
from .utils.logs import LogMessageBox

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)


logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Application started")

        self.rd = RuntimeData()

        # size, title and logo
        self.setGeometry(600, 500, 2550, 1450)  # position and size of the window
        self.setWindowTitle('Specvizitor')  # title of the window
        self.setWindowIcon(QtGui.QIcon('logo2_2.png'))  # logo in upper left corner

        # add a menu
        self._add_menu()

        # add a status bar
        # self.statusBar().showMessage("Message in statusbar.")

        # add a central widget
        self.main_GUI = FRESCO(self.rd, parent=self)
        # self.main_GUI.signal1.connect(self.show_status)
        self.setCentralWidget(self.main_GUI)

        if self.rd.cache.last_inspection_file:
            self.open(self.rd.cache.last_inspection_file)

    def _add_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_file = QtWidgets.QAction("&New...")
        self._new_file.triggered.connect(self._new_file_action)
        self._file.addAction(self._new_file)

        self._open_file = QtWidgets.QAction("&Open...")
        self._open_file.triggered.connect(self._open_file_action)
        self._file.addAction(self._open_file)

        self._file.addSeparator()

        self._save = QtWidgets.QAction("Save...")
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
        dialog = NewFile(self.rd, parent=self)
        if dialog.exec():
            self.rd.cache.last_object_index = 0
            self.load_project()

    def _open_file_action(self):
        path = QtWidgets.QFileDialog.getOpenFileName(self, caption='Open Inspection File', filter='CSV Files (*.csv)')[
            0]
        if path:
            self.rd.cache.last_object_index = 0
            self.open(path)

    def open(self, path: str):
        if pathlib.Path(path).exists():
            self.rd.output_path = pathlib.Path(path)
            self.rd.read()
            self.load_project()
        else:
            logger.warning('Inspection file not found (path: {})'.format(path))

    def load_project(self):
        for w in (self._save, self._save_as, self._export):
            w.setEnabled(True)
        self.setWindowTitle('{} – Specvizitor'.format(self.rd.output_path.name))
        self.main_GUI.load_project()

    def _save_action(self):
        msg = 'The data is saved automatically'
        if self.rd.output_path is not None:
            msg += ' to {}'.format(self.rd.output_path)
        LogMessageBox(logging.INFO, msg, parent=self)

    def _save_as_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _export_action(self):
        LogMessageBox(logging.INFO, 'Not implemented', parent=self)

    def _exit_action(self):
        self.rd.save()
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


class FRESCO(QtWidgets.QWidget):
    def __init__(self, rd: RuntimeData, parent=None):
        self.rd = rd
        super().__init__(parent)

        # set up the widget layout
        self.layout = QtWidgets.QGridLayout()
        self.layout.setSpacing(10)
        self.setLayout(self.layout)

        # add a widget for the data viewer
        self.data_viewer = DataViewer(self.rd, parent=self)
        self.layout.addWidget(self.data_viewer, 1, 1, 3, 1)

        # add a widget for the control panel
        self.control_panel = ControlPanel(self.rd, parent=self)
        self.layout.addWidget(self.control_panel, 1, 2, 1, 1)

        # add a widget for displaying information about the object
        self.object_info = ObjectInfo(self.rd, parent=self)
        self.layout.addWidget(self.object_info, 2, 2, 1, 1)

        # add a widget for writing comments
        self.review_form = ReviewForm(self.rd, parent=self)
        self.layout.addWidget(self.review_form, 3, 2, 1, 1)

        # add the Eazy widget
        # self.eazy = Eazy(self)
        # grid.addWidget(self.eazy, 6, 3, 1, 1)

        # Write eazy results

        '''
        z_raw_chi2 = np.round(self.zout['z_raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtWidgets.QLabel('Chi2: '+str(z_raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,7,31,1,1)

        raw_chi2 = np.round(self.zout['raw_chi2'][self.j],3)
        eazy_raw_chi2 = QtWidgets.QLabel('Chi2: '+str(raw_chi2), self)
        grid.addWidget(eazy_raw_chi2,8,31,1,1)
        '''

        # self.z_phot_chi2 = np.round(self.zout['z_phot_chi2'][self.j], 3)
        # eazy_raw_chi2 = QtWidgets.QLabel('Chi2: ' + str(self.z_phot_chi2), self)
        # grid.addWidget(eazy_raw_chi2, 9, 31, 1, 1)
        #
        # self.sfr = np.round(self.zout['sfr'][self.j], 3)
        # eazy_sfr = QtWidgets.QLabel('SFR: ' + str(self.sfr), self)
        # grid.addWidget(eazy_sfr, 10, 31, 1, 1)
        #
        # self.mass = np.round(self.zout['mass'][self.j] / 10 ** 9, 3)
        # eazy_mass = QtWidgets.QLabel('mass: ' + str(self.mass), self)
        # grid.addWidget(eazy_mass, 11, 31, 1, 1)

        # self.control_panel.reset_button_clicked.connect(self.image_cutout.reset_view)

        self.control_panel.object_selected.connect(self.load_object)
        self.control_panel.reset_button_clicked.connect(self.data_viewer.reset_view)

    @property
    def widgets(self) -> list[AbstractWidget]:
        return get_widgets(self.layout)

    def load_object(self, j: int):
        if self.rd.j is not None:
            for widget in self.widgets:
                widget.dump()
            self.rd.save()

        self.rd.j = j
        self.rd.cache.last_object_index = j
        self.rd.cache.save(self.rd.cache_file)

        for widget in self.widgets:
            widget.load_object()

    def load_project(self):
        self.rd.cache.last_inspection_file = str(self.rd.output_path)
        self.rd.cache.save(self.rd.cache_file)

        # reload the review form
        self.layout.removeWidget(self.review_form)
        self.review_form.setParent(None)
        self.review_form = ReviewForm(self.rd, parent=self)
        self.layout.addWidget(self.review_form, 3, 2, 1, 1)

        for w in self.widgets:
            w.load_project()

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

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
