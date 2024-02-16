from astropy.wcs import WCS
import numpy as np
from qtpy import QtCore, QtWidgets


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


def get_qtransform_matrix_from_wcs(w: WCS) -> np.ndarray:
    transformation_matrix = np.zeros((3, 3))
    transformation_matrix[:2, :2] = w.pixel_scale_matrix
    # transformation_matrix[:2, 2] = w.wcs.crpix
    transformation_matrix[2, :2] = w.wcs.crval
    transformation_matrix[2, 2] = 1.0

    return transformation_matrix


def safe_disconnect(signal: QtCore.Signal):
    try:
        signal.disconnect()
    except TypeError:
        pass
