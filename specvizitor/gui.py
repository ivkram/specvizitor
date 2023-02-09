import sys
import logging
import pathlib

from astropy.table import Table

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from .utils.params import read_config, read_cache, get_user_config_filename, get_cache_filename
from .menu import NewFile
from .widgets import (ControlPanel, ObjectInfo, ReviewForm,
                      ImageCutout, Spec2D, Spec1D,
                      Eazy)

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        # load the configuration file
        self._config = read_config()

        # read cache
        self._cache = read_cache()

        super().__init__(parent)

        # size, title and logo
        self.setGeometry(600, 500, 2550, 1450)  # position and size of the window
        self.setWindowTitle('FRESCO')  # title of the window
        self.setWindowIcon(QtGui.QIcon('logo2_2.png'))  # logo in upper left corner

        # add a menu
        self._add_menu()

        # add a status bar
        self.statusBar().showMessage("Message in statusbar.")

        # add a central widget
        self.main_GUI = FRESCO(self._config, self._cache, parent=self)
        # self.main_GUI.signal1.connect(self.show_status)
        self.setCentralWidget(self.main_GUI)

    def _add_menu(self):
        self._menu = self.menuBar()

        self._file = self._menu.addMenu("&File")

        self._new_project = QtWidgets.QAction("&New...")
        self._new_project.triggered.connect(self._new_project_action)
        self._file.addAction(self._new_project)

        self._file.addAction("&Open...")
        self._file.addAction("&Export...")
        self._file.addSeparator()

        self._exit = QtWidgets.QAction("E&xit...")
        self._exit.triggered.connect(self._exit_action)
        self._file.addAction(self._exit)

        self._tools = self._menu.addMenu("&Tools")
        self._settings = QtWidgets.QAction("&Settings...")
        self._settings.triggered.connect(self._settings_action)
        self._tools.addAction(self._settings)

        self._help = self._menu.addMenu("&Help")
        self._about = QtWidgets.QAction("&About...")
        self._about.triggered.connect(self._about_action)
        self._help.addAction(self._about)

    def _new_project_action(self):
        new_project_dialog = NewFile(self._config, self._cache, parent=self)
        new_project_dialog.project_created.connect(self.main_GUI.load_project)
        new_project_dialog.exec()

    def _exit_action(self):
        # TODO: save everything before exiting the program
        logger.info("Exiting the program...")
        self.close()

    def _settings_action(self):
        QtWidgets.QMessageBox.information(self, "Settings",
                                          "Location of the configuration file: {}\n\nLocation of cache: {}".
                                          format(get_user_config_filename(), get_cache_filename()))

    def _about_action(self):
        QtWidgets.QMessageBox.about(self, "About Specvizitor", "Specvizitor v0.1.0")


class FRESCO(QtWidgets.QWidget):
    def __init__(self, config: dict, cache: dict, parent=None):
        self._config = config
        self._cache = cache

        self._output_file = None
        self._cat = None

        # initialise the widget
        super().__init__(parent)

        # set up the widget layout
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        self.setLayout(grid)

        # TODO: create a DataViewer class
        # add a widget for the image cutout
        self.image_cutout = ImageCutout(config['loader'], config['gui']['viewer']['image_cutout'], parent=self)
        grid.addWidget(self.image_cutout, 1, 1, 3, 1)

        # add a widget for the 2D spectrum
        self.spec_2D = Spec2D(config['loader'], config['gui']['viewer']['spec_2D'], parent=self)
        grid.addWidget(self.spec_2D, 4, 1, 1, 2)

        # add a widget for the 1D spectrum
        self.spec_1D = Spec1D(config['loader'], config['gui']['viewer']['spec_1D'], parent=self)
        grid.addWidget(self.spec_1D, 5, 1, 1, 2)

        # add a widget for the control panel
        self.control_panel = ControlPanel(config['gui']['control_panel'], cache, parent=self)
        grid.addWidget(self.control_panel, 1, 3, 1, 1)

        # add a widget for displaying information about the object
        self.object_info = ObjectInfo(config['gui']['object_info'], parent=self)
        grid.addWidget(self.object_info, 2, 3, 1, 1)

        # add a widget for writing comments
        self.review_form = ReviewForm(config, parent=self)
        grid.addWidget(self.review_form, 3, 3, 3, 1)

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

        self.control_panel.reset_button_clicked.connect(self.image_cutout.reset_view)
        self.control_panel.reset_button_clicked.connect(self.spec_2D.reset_view)
        self.control_panel.reset_button_clicked.connect(self.spec_1D.reset_view)

        self.control_panel.object_selected.connect(self.control_panel.load_object)
        self.control_panel.object_selected.connect(self.object_info.load_object)
        self.control_panel.object_selected.connect(self.review_form.load_object)

        self.control_panel.object_selected.connect(self.image_cutout.load_object)
        self.control_panel.object_selected.connect(self.spec_2D.load_object)
        self.control_panel.object_selected.connect(self.spec_1D.load_object)

    #############################################################################
    # functions

    def load_project(self, output_file: str, cat: Table):
        self._output_file = output_file
        self._cat = cat

        self.control_panel.load_project(self._cat)
        self.object_info.load_project(self._cat)
        self.review_form.load_project(self._cat)

        self.image_cutout.load_project(self._cat)
        self.spec_2D.load_project(self._cat)
        self.spec_1D.load_project(self._cat)

        # TODO: read index from cache when opening an existing project, not when creating a new one
        j = self._cache.get('last_object_index', 0)

        if j < len(self._cat):
            self.control_panel.object_selected.emit(int(j))
        else:
            self.control_panel.object_selected.emit(0)

    def save_now(self):
        self._cat['SFR'][self._j] = 0  # self.sfr
        self._cat['mass'][self._j] = 0  # self.mass
        self._cat['chi2'][self._j] = 0  # self.z_phot_chi2
        # write_output(input_cat, comments, 'test.fits')


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
