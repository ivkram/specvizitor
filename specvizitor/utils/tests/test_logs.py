"""Tests for the message-box logging handler.

A decorated function may call another one -- a menu action opening a dialog that validates
itself, for instance. Each nested scope used to install its own handler, so one logged error
produced one message box per scope.
"""

import logging
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets

import specvizitor.utils.logs as logs_module
from specvizitor.utils.logs import qlog

logger = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def shown(app, monkeypatch):
    """Collect the messages that would have been shown, instead of showing them.
    """
    messages = []

    class _Recorder(logs_module.LogMessageBox):
        def __init__(self, level, message, parent=None):
            messages.append(message)

    monkeypatch.setattr(logs_module, 'LogMessageBox', _Recorder)
    monkeypatch.setattr(logging.getLogger(), 'level', logging.DEBUG)
    return messages


@qlog
def _report(message='a problem'):
    logger.error(message)


@qlog
def _report_via_another_scope():
    _report()


@qlog
def _report_three_deep():
    _report_via_another_scope()


def test_an_error_is_reported_once(shown):
    _report()
    assert shown == ['a problem']


def test_a_nested_scope_does_not_duplicate_the_message(shown):
    _report_via_another_scope()
    assert shown == ['a problem']


def test_deeper_nesting_does_not_duplicate_either(shown):
    _report_three_deep()
    assert shown == ['a problem']


def test_nothing_is_reported_outside_a_scope(shown):
    logger.error('unreported')
    assert shown == []


def test_the_handler_is_removed_after_a_nested_scope(shown):
    _report_via_another_scope()
    shown.clear()

    logger.error('after')

    assert shown == []


def test_info_messages_are_not_shown(shown):
    @qlog
    def _info():
        logger.info('just information')

    _info()
    assert shown == []


def test_the_handler_is_removed_even_if_the_function_raises(shown):
    @qlog
    def _boom():
        raise ValueError('boom')

    with pytest.raises(ValueError):
        _boom()

    logger.error('after')
    assert shown == []


def test_a_message_box_survives_when_nothing_has_focus(app, monkeypatch):
    """The reported symptom: renaming to a taken name logged to the terminal but showed nothing.

    focusWidget() is None right after a modal dialog closes. The box then had no parent, so Qt
    did not own it, and the handler kept no reference of its own -- it was collected before it
    could appear.
    """
    monkeypatch.setattr(logging.getLogger(), 'level', logging.DEBUG)
    logs_module._open_message_boxes.clear()
    assert QtWidgets.QApplication.focusWidget() is None

    @qlog
    def _report():
        logger.error('name already taken')

    _report()

    assert len(logs_module._open_message_boxes) == 1
    box = next(iter(logs_module._open_message_boxes))
    assert box.text() == 'name already taken'

    box.close()
    app.processEvents()
    assert not logs_module._open_message_boxes


def test_a_message_box_is_parented_to_the_active_window(app, monkeypatch):
    monkeypatch.setattr(logging.getLogger(), 'level', logging.DEBUG)
    logs_module._open_message_boxes.clear()

    window = QtWidgets.QMainWindow()
    window.show()
    app.processEvents()
    monkeypatch.setattr(QtWidgets.QApplication, 'activeWindow', staticmethod(lambda: window))

    @qlog
    def _report():
        logger.error('a problem')

    _report()

    box = next(iter(logs_module._open_message_boxes))
    assert box.parent() is window

    box.close()
    app.processEvents()
    window.close()
