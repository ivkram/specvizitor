"""Switching objects aborts the running loader without waiting for it: it finishes the widget it is loading in the
background, and the next loader waits for it in its own thread. The main thread used to wait instead, which froze
the interface for as long as one widget took to load.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import threading
import time

import pytest

pytest.importorskip('qtpy')

from specvizitor.config import data_widgets
from specvizitor.widgets.Image2D import Image2D
from specvizitor.widgets.ViewerDataLoader import LoaderState, LoadTask, ViewerDataLoader


class _StubViewerData:
    def __init__(self):
        self.calls = []

    def close(self, filename):
        self.calls.append(('close', filename))

    def reopen(self, filename):
        self.calls.append(('reopen', filename))


def _task(title='Spectrum', source=None) -> LoadTask:
    return LoadTask(title=title, cfg=data_widgets.Image(data=data_widgets.DataElement(source=source)),
                    widget_type=Image2D)


def _loader(state, viewer_data=None, tasks=None, j=0):
    return ViewerDataLoader(tasks=tasks or [], j=j, inspection_data=None, viewer_data=viewer_data,
                            data_sources=None, cat_entry=None, t_grace=0, state=state)


def test_the_file_to_close_comes_from_the_loaders_not_the_widget():
    # the widget may not have received the data of a stale loader yet, so its data path can be out of date
    state, viewer_data = LoaderState(), _StubViewerData()
    state.open_files['Spectrum'] = 'spectrum_2.fits'
    _loader(state, viewer_data)._free_resources(_task())

    assert viewer_data.calls == [('close', 'spectrum_2.fits')]
    assert 'Spectrum' not in state.open_files


def test_a_shared_image_is_reopened_rather_than_closed():
    state, viewer_data = LoaderState(), _StubViewerData()
    state.open_files['Stamp'] = 'mosaic.fits'
    _loader(state, viewer_data)._free_resources(_task('Stamp', source='Mosaic'))

    assert viewer_data.calls == [('reopen', 'mosaic.fits')]


def test_nothing_is_freed_for_a_widget_without_data():
    viewer_data = _StubViewerData()
    _loader(LoaderState(), viewer_data)._free_resources(_task())

    assert viewer_data.calls == []


def test_the_next_loader_waits_for_a_stale_one_in_its_own_thread():
    state, events = LoaderState(), []
    tasks = [_task('A'), _task('B')]
    entered = threading.Event()

    def slow_load(j):
        def _load_data(w0):
            entered.set()
            events.append(('start', j, w0.title))
            time.sleep(0.3)
            events.append(('end', j, w0.title))
        return _load_data

    stale = _loader(state, tasks=tasks, j=1)
    stale._load_data = slow_load(1)
    stale.start()
    assert entered.wait(5)
    stale.abort()

    successor = _loader(state, tasks=tasks, j=2)
    successor._load_data = slow_load(2)
    successor.start()

    assert successor.wait(5000) and stale.wait(5000)
    # the stale loader only finished the widget it was loading, and before the successor started
    assert events == [('start', 1, 'A'), ('end', 1, 'A'),
                      ('start', 2, 'A'), ('end', 2, 'A'), ('start', 2, 'B'), ('end', 2, 'B')]
