from qtpy import QtWidgets


def get_widgets(layout: QtWidgets.QLayout) -> list[QtWidgets.QWidget]:
    widgets = []

    index = layout.count() - 1
    while index >= 0:
        widgets.append(layout.itemAt(index).widget())
        index -= 1

    return widgets


def wrap_widget(widget: QtWidgets.QWidget, margins=tuple(5 for _ in range(4))) -> QtWidgets.QLayout:
    layout = QtWidgets.QGridLayout()
    layout.setContentsMargins(*margins)
    layout.addWidget(widget)

    return layout
