import abc

from qtpy import QtWidgets

from specvizitor.utils.widget_tools import get_widgets


class QtAbcMeta(type(QtWidgets.QWidget), type(abc.ABC)):
    pass


class AbstractWidget(QtWidgets.QWidget, abc.ABC, metaclass=QtAbcMeta):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)

        self.setEnabled(False)

    @abc.abstractmethod
    def init_ui(self):
        pass

    def reset_layout(self):
        for widget in get_widgets(self.layout):
            self.layout.removeWidget(widget)
            widget.destroy()
        self.init_ui()

    def activate(self, a0: bool = True):
        self.setEnabled(a0)

        for widget in get_widgets(self.layout):
            if isinstance(widget, AbstractWidget):
                widget.activate(a0)
            else:
                widget.setEnabled(a0)

