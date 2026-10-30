import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest


@pytest.fixture(scope='session', autouse=True)
def qapp():
    # one QApplication for the whole session: destroying and re-creating it between test modules, while
    # pyqtgraph objects from earlier tests are still waiting to be garbage-collected, segfaults at random
    try:
        from qtpy import QtWidgets
    except ImportError:
        yield None
        return
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
