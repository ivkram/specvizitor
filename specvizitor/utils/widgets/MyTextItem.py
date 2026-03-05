from qtpy import QtCore
import pyqtgraph as pg


__all__ = [
    "MyTextItem"
]


class MyTextItem(pg.TextItem, QtCore.QObject):
    clicked = QtCore.Signal()
    color_changed = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        QtCore.QObject.__init__(self)
        pg.TextItem.__init__(self, *args, **kwargs)

    def mousePressEvent(self, event):
        color = "r"
        self.setColor(color)

        self.clicked.emit()
        super().mousePressEvent(event)

    def setColor(self, color):
        super().setColor(color)
        self.color_changed.emit(color)
