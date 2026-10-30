"""Which settings can be applied in place, and which genuinely need a restart.

Getting this wrong is invisible in normal use until the user is asked to restart for no reason,
so each case is pinned here.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets

from specvizitor.config import Config
from specvizitor.config.workspace import Workspace
from specvizitor.widgets.Settings import Settings


@pytest.fixture(scope='module')
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def settings(app, tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    workspace = Workspace.create(tmp_path / 'ws', name='Test')
    workspace.config.data.dir = str(data_dir)
    workspace.config.save()

    config = Config()

    # never actually offer to restart
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question',
                        staticmethod(lambda *a, **kw: QtWidgets.QMessageBox.No))

    dialog = Settings(None, config, workspace.config, workspace.spectral_lines)
    yield dialog, config, workspace
    dialog.deleteLater()


def _accept(dialog):
    dialog._button_box.button(QtWidgets.QDialogButtonBox.Ok).click()
    return dialog._restart_required


def test_accepting_without_changes_does_not_ask_for_a_restart(settings):
    dialog, _, _ = settings
    assert _accept(dialog) is False


def test_a_plugin_listed_in_another_order_is_not_a_change(settings):
    dialog, _, workspace = settings
    # the bundled configuration lists the plugins unsorted, while the checkboxes are alphabetical
    assert set(workspace.config.plugins) == set(dialog._tabs['Plugins']._new_plugins or
                                                workspace.config.plugins)
    assert _accept(dialog) is False


def test_changing_the_viewer_geometry_applies_in_place(settings):
    dialog, config, _ = settings
    appearance = dialog._tabs['Appearance']
    appearance._spacing_spinbox.setValue(config.appearance.viewer_spacing + 4)
    appearance._margins_spinbox.setValue(config.appearance.viewer_margins + 2)

    assert _accept(dialog) is False
    assert config.appearance.viewer_spacing == 7
    assert config.appearance.viewer_margins == 5


def test_changing_the_theme_requires_a_restart(settings):
    dialog, config, _ = settings
    appearance = dialog._tabs['Appearance']
    other = next(t for t in appearance.THEMES if t != config.appearance.theme)
    appearance._theme_combobox.setCurrentIndex(appearance.THEMES.index(other))

    assert _accept(dialog) is True


def test_changing_the_unit_aliases_applies_in_place(settings):
    dialog, _, workspace = settings
    applied = []
    dialog.unit_aliases_changed.connect(lambda: applied.append(True))

    dialog._tabs['Data Source']._unit_aliases_table._add_row(['Jy', 'JANSKY'])

    assert _accept(dialog) is False
    assert applied, "the aliases must be re-registered instead of requiring a restart"
    assert workspace.config.data.enabled_unit_aliases['Jy'] == ['JANSKY']


def test_enabling_a_plugin_requires_a_restart(settings):
    dialog, _, workspace = settings
    checkboxes = dialog._tabs['Plugins']._checkboxes
    if not checkboxes:
        pytest.skip('no plugins available')

    # flip whichever plugin is currently enabled
    name, box = next(iter(checkboxes.items()))
    box.setChecked(not box.isChecked())

    assert _accept(dialog) is True


def test_the_image_table_has_no_shared_or_local_column(settings):
    dialog, _, _ = settings
    # image paths are machine-local, exactly like the data directory and the catalogue
    assert dialog._tabs['Data Source']._image_table._header == ['Label', 'Path', 'WCS Source']


def test_the_id_pattern_is_not_in_the_settings(settings):
    dialog, _, _ = settings
    # it is only consulted when a new inspection file is created
    assert not hasattr(dialog._tabs['Data Source'], '_id_pattern')
