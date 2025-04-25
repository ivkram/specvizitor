from functools import wraps
import logging

from qtpy import QtWidgets


class QLogHandler(logging.Handler):
    def emit(self, record):
        msg = record.msg
        if isinstance(msg, Exception):
            msg = str(msg)
            if msg.startswith("'") and msg.endswith("'"):
                msg = msg[1:-1]

        level = record.levelno
        if level <= logging.INFO:
            return
        LogMessageBox(level, msg, parent=QtWidgets.QApplication.focusWidget())


class LogMessageBox(QtWidgets.QMessageBox):
    PACKAGE = __package__.split('.')[0].capitalize()  # the name of the top-level package

    LOGGING_LEVELS = {
        logging.INFO: QtWidgets.QMessageBox.Information,
        logging.WARNING: QtWidgets.QMessageBox.Warning,
        logging.ERROR: QtWidgets.QMessageBox.Warning,
        logging.CRITICAL: QtWidgets.QMessageBox.Critical
    }

    def __init__(self, level: int, message: str, parent=None):
        super().__init__(self.LOGGING_LEVELS[level], '{} Message'.format(self.PACKAGE), message, parent=parent)
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
