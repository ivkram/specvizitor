import logging
from functools import wraps

from pyqtgraph.Qt import QtWidgets


logger = logging.getLogger('specvizitor')


class QLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        LogMessageBox(record.levelno, record.msg)


class LogMessageBox(QtWidgets.QMessageBox):
    LOGGING_LEVELS = {
        logging.INFO: QtWidgets.QMessageBox.Information,
        logging.WARNING: QtWidgets.QMessageBox.Warning,
        logging.ERROR: QtWidgets.QMessageBox.Warning,
        logging.CRITICAL: QtWidgets.QMessageBox.Critical
    }

    def __init__(self, level: int, message: str):
        super().__init__(LogMessageBox.LOGGING_LEVELS[level], 'Specvizitor Message', message,
                         parent=QtWidgets.QApplication.focusWidget())
        self.show()


def qlog(action):
    @wraps(action)
    def wrapper(*args):
        logger.addHandler(QLogHandler())
        action(*args)
        logger.handlers.clear()

    return wrapper
