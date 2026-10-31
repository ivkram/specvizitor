from qtpy import QtCore
import pyqtgraph as pg


__all__ = [
    "MyTextItem"
]


class MyTextItem(pg.TextItem):
    clicked = QtCore.Signal()
    color_changed = QtCore.Signal(object)

    def mousePressEvent(self, event):
        color = "r"
        self.setColor(color)

        self.clicked.emit()
        super().mousePressEvent(event)

    def setColor(self, color):
        super().setColor(color)
        self.color_changed.emit(color)
