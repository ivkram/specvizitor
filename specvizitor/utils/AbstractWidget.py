import abc

from qtpy import QtWidgets

from specvizitor.utils.widget_tools import get_widgets


class QtAbcMeta(type(QtWidgets.QWidget), type(abc.ABC)):
    pass


class AbstractWidget(QtWidgets.QWidget, abc.ABC, metaclass=QtAbcMeta):
    def __init__(self, layout: QtWidgets.QLayout = None, parent=None):
        super().__init__(parent)

        if layout is not None:
            self.setLayout(layout)

        self.setEnabled(False)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        self.layout().setSpacing(spacing)

        if isinstance(margins, int):
            margins = tuple(margins for _ in range(4))
        self.layout().setContentsMargins(*margins)

    @abc.abstractmethod
    def init_ui(self):
        pass

    def reset_layout(self):
        for widget in get_widgets(self.layout()):
            self.layout().removeWidget(widget)
            widget.destroy()
        self.init_ui()

    def activate(self, a0: bool = True):
        self.setEnabled(a0)

        for widget in get_widgets(self.layout()):
            if isinstance(widget, AbstractWidget):
                widget.activate(a0)
            else:
                widget.setEnabled(a0)

