from qtpy import QtCore, QtWidgets


class MyQLineEdit(QtWidgets.QLineEdit):
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.clearFocus()
            return
        super().keyReleaseEvent(event)
