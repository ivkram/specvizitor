from functools import wraps
import logging

from qtpy import QtCore, QtWidgets


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

        LogMessageBox(level, msg, parent=QtWidgets.QApplication.activeWindow())


# A message box without a parent is deleted as soon as Python holds no reference to it, so it
# would disappear right after being shown. Keep it here until the user closes it.
_open_message_boxes: set = set()


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
        # closing only hides a box, which would then stay alive as a child of its parent until
        # the parent itself is destroyed -- delete it right away instead
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        _open_message_boxes.add(self)
        self.finished.connect(lambda _: _open_message_boxes.discard(self))

        self.show()


def qlog(func):
    """Surface any warning or error logged during `func` in a message box.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        root_logger = logging.getLogger()

        if any(isinstance(h, QLogHandler) for h in root_logger.handlers):
            return func(*args, **kwargs)

        handler = QLogHandler()
        root_logger.addHandler(handler)
        try:
            return func(*args, **kwargs)
        finally:
            root_logger.removeHandler(handler)

    return wrapper
