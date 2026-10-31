"""Items registered with a widget belong to the current object, and so do the connections made for them:
both go away once another object is loaded. Connections used to pile up on long-lived senders instead.
"""

import gc

import pytest

pytest.importorskip('qtpy')

import pyqtgraph as pg
import qtpy
from qtpy import QtCore

from specvizitor.config import config, data_widgets
from specvizitor.config.spectral_lines import SpectralLineData
from specvizitor.widgets.Plot1D import Plot1D


class _Slider(QtCore.QObject):
    value_changed = QtCore.Signal(float)

    def count_receivers(self) -> int:
        # PySide6 only takes the signal by its signature
        if qtpy.PYSIDE6:
            return self.receivers(QtCore.SIGNAL('value_changed(double)'))
        return self.receivers(self.value_changed)


@pytest.fixture
def widget():
    widget = Plot1D(cfg=data_widgets.Plot1D(), title='Redshift PDF', appearance=config.Appearance(),
                    spectral_lines=SpectralLineData())
    yield widget

    # delete the pyqtgraph widget for real: garbage-collecting it later segfaults
    widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def _register_marker(widget: Plot1D, slider: _Slider) -> pg.InfiniteLine:
    line = pg.InfiniteLine(0)
    widget.register_item(line, connections=[(slider.value_changed, line.setPos)])
    return line


def test_the_connections_of_an_item_follow_it(widget):
    slider = _Slider()
    line = _register_marker(widget, slider)

    slider.value_changed.emit(2.0)
    assert line.value() == 2.0

    widget.remove_registered_items()
    assert slider.count_receivers() == 0


def test_connections_do_not_pile_up_from_one_object_to_the_next(widget):
    slider = _Slider()
    for _ in range(3):
        widget.remove_registered_items()  # what loading another object does
        line = _register_marker(widget, slider)

    assert slider.count_receivers() == 1

    slider.value_changed.emit(3.0)
    assert line.value() == 3.0


def test_the_sender_may_be_deleted_first(widget):
    # e.g. a slider of another widget, re-created when a viewer configuration is restored
    slider = _Slider()
    _register_marker(widget, slider)

    slider.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    widget.remove_registered_items()
