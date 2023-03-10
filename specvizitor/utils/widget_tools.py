from qtpy import QtWidgets


def get_widgets(layout: QtWidgets.QLayout) -> list[QtWidgets.QWidget]:
    widgets = []

    index = layout.count() - 1
    while index >= 0:
        widget, sub_layout = layout.itemAt(index).widget(), layout.itemAt(index).layout()
        if widget is not None:
            widgets.append(widget)
        elif layout is not None:
            widgets.extend(get_widgets(sub_layout))
        index -= 1

    return widgets
