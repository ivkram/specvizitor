from qtpy import QtCore, QtWidgets


class MyQTextEdit(QtWidgets.QTextEdit):
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.clearFocus()
            return
        super().keyReleaseEvent(event)
