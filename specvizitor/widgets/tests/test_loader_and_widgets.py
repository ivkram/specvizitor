"""The loader thread works from a snapshot of the widgets, and the viewer hands what it loads to the widgets on the
main thread. The loader used to hold the widgets themselves: rebuilding them during a load (e.g. opening a viewer
configuration) made it connect to a deleted widget, which raises in the loader thread and aborts the application.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gc
import sys
import threading
import time

import numpy as np
import pytest
from astropy.io import fits

pytest.importorskip('qtpy')

from qtpy import QtCore, QtWidgets

from specvizitor.config import config, data_widgets
from specvizitor.config.spectral_lines import SpectralLineData
from specvizitor.io.inspection_data import InspectionData
from specvizitor.io.viewer_data import ViewerData
from specvizitor.widgets.DataViewer import DataViewer

INSPECTION_DATA = InspectionData.create([1, 2])
LOAD_TIME = 0.3


def _widget_cfg() -> data_widgets.DataWidgets:
    return data_widgets.DataWidgets(images={
        title: data_widgets.Image(data=data_widgets.DataElement(filename='{id}.fits')) for title in ('A', 'B')
    })


@pytest.fixture
def slow_viewer(tmp_path, monkeypatch):
    for obj_id in (1, 2):
        fits.PrimaryHDU(np.full((5, 5), float(obj_id))).writeto(tmp_path / f'{obj_id}.fits')

    # each file takes a while to load, so that the test can act in the middle of a load
    loading = threading.Event()
    load = ViewerData.load

    def slow_load(self, *args, **kwargs):
        loading.set()
        time.sleep(LOAD_TIME)
        return load(self, *args, **kwargs)

    monkeypatch.setattr(ViewerData, 'load', slow_load)

    errors = []
    monkeypatch.setattr(sys, 'excepthook', lambda exc_type, exc, tb: errors.append(exc))

    viewer = DataViewer(config.DataViewer(), config.DataSources(dir=str(tmp_path)), _widget_cfg(),
                        config.Appearance(), spectral_lines=SpectralLineData(), plugins=[])
    yield viewer, loading, errors

    viewer.free_resources()
    viewer.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def _process_events(duration: float):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < duration:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)


def test_rebuilding_the_widgets_during_a_load_is_safe(slow_viewer):
    viewer, loading, errors = slow_viewer
    old_widgets = dict(viewer.widgets)

    viewer.load_object(0, INSPECTION_DATA, None)
    assert loading.wait(5)
    viewer.update_viewer_configuration(_widget_cfg())
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)  # the old widgets go for real
    _process_events(3 * LOAD_TIME)

    assert errors == []
    assert all(viewer.widgets[wt] is not w0 for wt, w0 in old_widgets.items())
    # what the stopped loader sent was for the old widgets: the new ones wait for the reload
    assert all(w0.data is None for w0 in viewer.widgets.values())


def test_reopening_the_images_lets_a_load_finish(slow_viewer):
    viewer, loading, errors = slow_viewer
    loaded = []
    viewer.object_loaded.connect(lambda: loaded.append(1))

    viewer.load_object(1, INSPECTION_DATA, None)
    assert loading.wait(5)
    viewer.open_images()  # e.g. an image path changed in the settings: nothing reloads the object afterwards
    _process_events(LOAD_TIME)

    assert errors == []
    assert loaded == [1]
    assert all(np.all(w0.data == 2) for w0 in viewer.widgets.values())
