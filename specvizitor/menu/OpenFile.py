import logging
import pathlib

from astropy.table import Table

from pyqtgraph.Qt import QtWidgets, QtCore

from ..runtime import RuntimeData
from ..utils import FileBrowser
from ..io.loader import load_cat
from ..utils.logs import qlog


logger = logging.getLogger(__name__)


class OpenFile(QtWidgets.QDialog):
    def __init__(self, rd: RuntimeData, parent=None):
        self.rd = rd

        super().__init__(parent)
        self.setWindowTitle("Open Inspection File")

        path = QtWidgets.QFileDialog.getOpenFileName(self, caption='Choose File', filter='CSV Files (*.csv)')[0]
