"""A restart (a workspace switch, or a setting applied at startup) replaces the main window but keeps the
QApplication. Re-creating the QApplication while pyqtgraph items of the previous window were still waiting to
be garbage-collected used to segfault at random.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('qtpy')

from qtpy import QtCore, QtWidgets

from specvizitor.config import Config, Workspace, WorkspaceRegistry
from specvizitor.main import run_window
from specvizitor.widgets.MainWindow import MainWindow


def _main_windows() -> list[MainWindow]:
    return [w for w in QtWidgets.QApplication.topLevelWidgets() if isinstance(w, MainWindow)]


def test_a_restart_replaces_the_window_and_keeps_the_application(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    workspace = Workspace.create(tmp_path / 'ws', name='Test')

    for _ in range(3):
        # restart like a workspace switch would, once the window is up: in the event loop's very first
        # iteration, the quit that follows closing the last window would still win over the restart
        QtCore.QTimer.singleShot(100, lambda: _main_windows()[0].restart())

        exit_code = run_window(app, config=Config(), workspace=workspace, registry=WorkspaceRegistry(), plugins=[])

        assert exit_code == MainWindow.EXIT_CODE_REBOOT
        assert QtWidgets.QApplication.instance() is app
        assert _main_windows() == []  # deleted for real, not left to the garbage collector
