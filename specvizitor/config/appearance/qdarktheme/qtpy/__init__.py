"""Package applying Qt compat of PyQt6, PySide6, PyQt5 and PySide2."""
from .qt_compat import QtImportError
from .qt_version import QT_VERSION

try:
    from . import QtCore, QtGui, QtSvg, QtWidgets
except ImportError:
    from .._util import get_logger as __get_logger

    __logger = __get_logger(__name__)
    __logger.warning("Failed to import QtCore, QtGui, QtSvg and QtWidgets.")
