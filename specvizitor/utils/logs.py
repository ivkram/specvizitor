import logging
from functools import wraps

from qtpy import QtWidgets


class QLogHandler(logging.Handler):
    def emit(self, record):
        LogMessageBox(record.levelno, record.msg, parent=QtWidgets.QApplication.focusWidget())


class LogMessageBox(QtWidgets.QMessageBox):
    PACKAGE = __package__.split('.')[0].capitalize()  # the name of the top-level package

    LOGGING_LEVELS = {
        logging.INFO: QtWidgets.QMessageBox.Information,
        logging.WARNING: QtWidgets.QMessageBox.Warning,
        logging.ERROR: QtWidgets.QMessageBox.Warning,
        logging.CRITICAL: QtWidgets.QMessageBox.Critical
    }

    def __init__(self, level: int, message: str, parent=None):
        super().__init__(LogMessageBox.LOGGING_LEVELS[level], '{} Message'.format(self.PACKAGE), message, parent=parent)
        self.show()


def qlog(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        root_logger = logging.getLogger()
        handler = QLogHandler()
        root_logger.addHandler(handler)

        res = func(*args, **kwargs)

        root_logger.removeHandler(handler)

        return res

    return wrapper
