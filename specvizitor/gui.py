import sys
import logging
from importlib.metadata import version

from astropy.table import Table
import pandas as pd

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtWidgets

from .runtime import RuntimeData
from .menu import NewFile
from .widgets import (AbstractWidget, DataViewer, ControlPanel, ObjectInfo, ReviewForm)
from .utils.widgets import get_widgets


pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        self.rd = RuntimeData()

        super().__init__(parent)
        logger.info("Application started")

        # size, title and logo
        self.setGeometry(600, 500, 2550, 1450)  # position and size of the window
        self.setWindowTitle('FRESCO')  # title of the window
        self.setWindowIcon(QtGui.QIcon('logo2_2.png'))  # logo in upper left corner

        # add a menu
        self._add_menu()

        # add a status bar
        # self.statusBar().showMessage("Message in statusbar.")

        # add a central widget
        self.main_GUI = FRESCO(self.rd, parent=self)
        # self.main_GUI.signal1.connect(self.show_status)
        self.setCentralWidget(self.main_GUI)

    def _add_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_project = QtWidgets.QAction("&New...")
        self._new_project.triggered.connect(self._new_project_action)
        self._file.addAction(self._new_project)

        self._file.addAction("&Open...")
        self._file.addAction("Save As...")
        self._file.addAction("&Export...")
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

    def _new_project_action(self):
        new_project_dialog = NewFile(self.rd, parent=self)
        new_project_dialog.project_created.connect(self.main_GUI.load_project)
        new_project_dialog.exec()

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
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        # add a widget for the data viewer
        self.data_viewer = DataViewer(self.rd, parent=self)
        grid.addWidget(self.data_viewer, 1, 1, 3, 1)

        # add a widget for the control panel
        self.control_panel = ControlPanel(self.rd, parent=self)
        grid.addWidget(self.control_panel, 1, 2, 1, 1)

        # add a widget for displaying information about the object
        self.object_info = ObjectInfo(self.rd, parent=self)
        grid.addWidget(self.object_info, 2, 2, 1, 1)

        # add a widget for writing comments
        self.review_form = ReviewForm(self.rd, parent=self)
        grid.addWidget(self.review_form, 3, 2, 1, 1)

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

        self.widgets: list[AbstractWidget] = []
        for w in get_widgets(grid):
            self.widgets.append(w)

    def load_object(self, j: int):
        if self.rd.j:
            for widget in self.widgets:
                widget.dump()
        self.rd.save()

        self.rd.j = j
        self.rd.cache.last_object_index = j
        self.rd.cache.save(self.rd.cache_file)

        for widget in self.widgets:
            widget.load_object()

    def load_project(self, output_file: str, cat: Table):
        self.rd.project = output_file
        self.rd.cat = cat
        self.rd.cat.add_index('id')

        self.rd.df = pd.DataFrame(index=self.rd.cat['id']).sort_index()
        self.rd.df['comment'] = ''
        for i, cname in enumerate(self.rd.config.review_form.checkboxes.keys()):
            self.rd.df[cname] = False

        for w in self.widgets:
            w.load_project()

        # TODO: read index from cache when opening an existing project, not when creating a new one
        j = self.rd.cache.last_object_index

        if j and j < len(self.rd.cat):
            self.load_object(int(j))
        else:
            self.load_object(0)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
