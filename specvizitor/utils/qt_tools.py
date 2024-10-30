from astropy.wcs import WCS
import numpy as np
from qtpy import QtCore, QtGui, QtWidgets


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


def get_qtransform_from_wcs(w: WCS) -> np.ndarray:
    transformation_matrix = np.zeros((3, 3))
    transformation_matrix[:2, :2] = w.pixel_scale_matrix
    transformation_matrix[2, :2] = w.wcs.crval
    transformation_matrix[2, 2] = 1.0

    # in pyqtgraph, the first pixel spans the [0, 1] range, whereas in WCS it's [-0.5, 0.5]
    qtransform1 = QtGui.QTransform.fromTranslate(-0.5, -0.5)

    qtransform2 = QtGui.QTransform()
    qtransform2.setMatrix(*transformation_matrix.flatten())

    return qtransform1 * qtransform2


def safe_disconnect(signal: QtCore.Signal):
    try:
        signal.disconnect()
    except TypeError:
        pass
