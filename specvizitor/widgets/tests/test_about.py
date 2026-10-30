from datetime import date

import pytest

pytest.importorskip('qtpy')

from qtpy import QtCore, QtWidgets

from specvizitor.widgets.MainWindow import MainWindow


def test_the_about_dialog_links_to_the_homepage_and_names_the_current_year(monkeypatch):
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, 'about', staticmethod(lambda parent, title, text: shown.append(text)))

    MainWindow._about_action(None)

    url = "https://specvizitor.ivkram.space"
    assert f'<a href="{url}">{url}</a>' in shown[0]
    assert f"2023–{date.today().year}" in shown[0]
    assert QtCore.Qt.mightBeRichText(shown[0])  # otherwise the link is shown as plain text
