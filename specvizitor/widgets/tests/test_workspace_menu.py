"""Dispatch tests for the workspace entries of the File menu.

These exist because a slot can be wired up incorrectly in a way that no direct call to the
method reveals: `QAction.triggered` passes a `checked` flag, and a decorator that takes *args
(such as `@qlog`) defeats the argument-count introspection PyQt uses to suppress it. The only
way to catch that is to trigger the actions the way a user does.

The window is built once for the whole module: repeatedly creating and destroying a MainWindow
in a single process is not stable, since its pyqtgraph widgets are torn down by the garbage
collector rather than deterministically.
"""

import gc
import os

# must be set before qtpy imports Qt, so that the suite stays headless-safe
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys

import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets
import qtpy.compat

import specvizitor.widgets.MainWindow as main_window_module
from specvizitor.config import Config, WorkspaceRegistry
from specvizitor.config.workspace import Workspace
from specvizitor.widgets.MainWindow import MainWindow

FILE_MENU_TITLE = '&File'
RECENT_MENU_TITLE = 'Recent Wor&kspaces'
# NewFile is in here because the sweep below triggers every File entry, and it now shares the
# menu with the workspace commands
DIALOG_NAMES = ('NewWorkspaceDialog', 'ImportWorkspaceDialog', 'ExportWorkspaceDialog',
                'ResolvePathsDialog', 'CloneWorkspaceDialog', 'RenameWorkspaceDialog', 'ForgetWorkspaceDialog',
                'NewFile')


class _StubSignal:
    """Accepts a connection and never fires.
    """

    def connect(self, *args, **kwargs):
        pass


class _StubDialog:
    """Stands in for a modal dialog: records that it was opened, then reports "cancelled".
    """
    opened: list = []

    def __init__(self, *args, **kwargs):
        type(self).opened.append(self)

    def exec(self):
        return 0

    def exec_(self):
        return 0

    def __getattr__(self, name):
        # callers wire up a dialog's signals before exec()ing it
        return _StubSignal()


@pytest.fixture(scope='module')
def gui(tmp_path_factory):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    tmp_path = tmp_path_factory.mktemp('workspaces')

    # two workspaces, so that the menu also lists something to switch to
    active = Workspace.create(tmp_path / 'active', name='Active')
    other = Workspace.create(tmp_path / 'other', name='Other')

    registry = WorkspaceRegistry()
    registry.register(other.path)
    registry.set_active(active.path)

    patch = pytest.MonkeyPatch()

    # neutralise everything modal or external that the actions would otherwise reach for
    for name in DIALOG_NAMES:
        patch.setattr(main_window_module, name, type(name, (_StubDialog,), {'opened': []}))

    patch.setattr(qtpy.compat, 'getexistingdirectory', lambda *a, **kw: '')
    patch.setattr(qtpy.compat, 'getopenfilename', lambda *a, **kw: ('', ''))
    patch.setattr(qtpy.compat, 'getsavefilename', lambda *a, **kw: ('', ''))

    restarts = []
    patch.setattr(MainWindow, 'restart', lambda self: restarts.append(True))

    win = MainWindow(config=Config(), workspace=active, registry=registry, plugins=[])

    yield dict(win=win, registry=registry, active=active, other=other, restarts=restarts, app=app)

    patch.undo()

    # tear the window down while the QApplication is still alive; leaving its pyqtgraph
    # widgets to interpreter shutdown segfaults, which would fail the suite even when every
    # assertion passed
    win.close()
    win.deleteLater()
    app.processEvents()
    del win
    gc.collect()
    app.processEvents()


@pytest.fixture(autouse=True)
def reset(gui):
    """Undo the side effects of triggering actions, so the tests stay order-independent.
    """
    gui['restarts'].clear()
    for name in DIALOG_NAMES:
        getattr(main_window_module, name).opened.clear()
    gui['registry'].set_active(gui['active'].path)
    # the menu entries live in an exclusive action group, so a triggered entry leaves its
    # checkmark behind for the next test
    for action in _recent_entries(gui['win']):
        if action.isCheckable() and action.text() == 'Active':
            action.setChecked(True)
    yield


@pytest.fixture
def slot_errors(monkeypatch):
    """Collect exceptions raised inside slots, which PyQt otherwise routes to sys.excepthook.
    """
    errors = []
    monkeypatch.setattr(sys, 'excepthook', lambda exc_type, exc, tb: errors.append(exc))
    return errors


def _menu_entries(win):
    action = next(a for a in win.menuBar().actions() if a.text() == FILE_MENU_TITLE)
    return [a for a in action.menu().actions() if not a.isSeparator()]


def _recent_menu(win):
    action = next(a for a in _menu_entries(win) if a.text() == RECENT_MENU_TITLE)
    return action.menu()


def _recent_entries(win):
    return [a for a in _recent_menu(win).actions() if not a.isSeparator()]


def _entry(win, label):
    return next(a for a in _menu_entries(win) if a.text() == label)


def _recent_entry(win, label):
    return next(a for a in _recent_entries(win) if a.text() == label)


def test_the_menu_exposes_the_expected_commands(gui):
    labels = [a.text() for a in _menu_entries(gui['win'])]
    assert labels == ['&New...', 'New &Workspace...', '&Open...', RECENT_MENU_TITLE,
                      '&Clone Workspace...', '&Rename Workspace...', 'Ex&port Workspace...',
                      '&Export Inspection Results...', '&Quit']


def test_every_menu_entry_has_a_distinct_mnemonic(gui):
    """Two entries sharing an accelerator makes keyboard navigation pick the wrong one.

    Worth asserting because the labels have been reshuffled more than once, and "New Workspace"
    and "Recent Workspaces" want the same letter.
    """
    mnemonics = [label[label.index('&') + 1].lower()
                 for label in (a.text() for a in _menu_entries(gui['win'])) if '&' in label]

    assert len(mnemonics) == len(set(mnemonics)), sorted(mnemonics)
    # every entry should have one at all
    assert len(mnemonics) == len(_menu_entries(gui['win']))


def test_the_menu_no_longer_carries_the_removed_commands(gui):
    labels = [a.text() for a in _menu_entries(gui['win'])]
    assert not any('Delete' in label or 'Folder' in label for label in labels)
    # and the separate Workspace menu is gone
    assert '&Workspace' not in [a.text() for a in gui['win'].menuBar().actions()]


def test_every_menu_entry_can_be_triggered(gui, slot_errors):
    # the regression this module exists for: a mis-declared slot raises on dispatch, before any
    # of the action's own code runs
    for action in _menu_entries(gui['win']) + _recent_entries(gui['win']):
        # Quit would take the window down with it, and the submenu itself has nothing to trigger
        if action.isEnabled() and action.text() not in ('&Quit', RECENT_MENU_TITLE):
            action.trigger()

    assert slot_errors == []


@pytest.mark.parametrize('label,dialog_name', [
    ('New &Workspace...', 'NewWorkspaceDialog'),
    ('&Clone Workspace...', 'CloneWorkspaceDialog'),
    ('Ex&port Workspace...', 'ExportWorkspaceDialog'),
])
def test_triggering_an_action_reaches_its_dialog(gui, slot_errors, label, dialog_name):
    _entry(gui['win'], label).trigger()

    assert slot_errors == []
    # proves the action body ran, not merely that dispatch did not raise
    assert getattr(main_window_module, dialog_name).opened


def test_the_active_workspace_is_listed_and_checked(gui):
    listed = [a for a in _recent_entries(gui['win']) if a.isCheckable()]
    assert [a.text() for a in listed] == ['Active', 'Other']
    assert [a.isChecked() for a in listed] == [True, False]


def test_the_workspace_entries_have_switching_shortcuts(gui):
    listed = [a for a in _recent_entries(gui['win']) if a.isCheckable()]
    assert [a.shortcut().toString() for a in listed] == ['Ctrl+1', 'Ctrl+2']


def test_triggering_another_workspace_switches_to_it(gui, slot_errors):
    _recent_entry(gui['win'], 'Other').trigger()

    assert slot_errors == []
    assert gui['restarts'], "switching should have requested a restart"
    assert gui['registry'].active == str(gui['other'].path)


def test_triggering_the_active_workspace_does_nothing(gui, slot_errors):
    _recent_entry(gui['win'], 'Active').trigger()

    assert slot_errors == []
    assert not gui['restarts'], "switching to the current workspace should be a no-op"


def _accepting_rename(name):
    """A stand-in for the rename dialog that reports `name` as accepted.
    """
    return type('_Rename', (_StubDialog,), {'opened': [], 'exec': lambda self: 1,
                                            'workspace_name': name})


def test_renaming_the_workspace_updates_the_menu_and_the_title(gui, slot_errors, monkeypatch):
    monkeypatch.setattr(main_window_module, 'RenameWorkspaceDialog', _accepting_rename('Renamed'))

    _entry(gui['win'], '&Rename Workspace...').trigger()

    assert slot_errors == []
    assert gui['win']._ws.name == 'Renamed'
    assert 'Renamed' in gui['win'].windowTitle()
    assert 'Renamed' in [a.text() for a in _recent_entries(gui['win']) if a.isCheckable()]
    # the directory stays where the registry points, and no restart is needed
    assert gui['win']._ws.path.name == 'active'
    assert not gui['restarts']

    # restore, so the shared fixture stays predictable for the other tests
    gui['win']._ws.rename('Active')
    gui['win']._update_window_title()
    gui['win']._populate_workspace_list()


def test_a_cancelled_rename_changes_nothing(gui, slot_errors):
    # the fixture's stub reports "cancelled"
    _entry(gui['win'], '&Rename Workspace...').trigger()

    assert slot_errors == []
    assert gui['win']._ws.name == 'Active'


def test_a_rejected_name_leaves_the_rename_dialog_standing(gui, slot_errors):
    """The dialog validates itself, so a taken name does not close it or lose what was typed.
    """
    from specvizitor.widgets.WorkspaceDialogs import RenameWorkspaceDialog

    dialog = RenameWorkspaceDialog(gui['registry'], gui['win']._ws)
    dialog._name_edit.setText('Other')
    dialog.accept()

    assert dialog.workspace_name is None
    assert dialog.result() == 0, "the dialog should not have been accepted"
    assert dialog._name_edit.text() == 'Other', "the rejected name should still be there to edit"
    assert gui['win']._ws.name == 'Active'


def test_the_rename_dialog_accepts_a_free_name(gui):
    from specvizitor.widgets.WorkspaceDialogs import RenameWorkspaceDialog

    dialog = RenameWorkspaceDialog(gui['registry'], gui['win']._ws)
    dialog._name_edit.setText('Something Else')
    dialog.accept()

    assert dialog.workspace_name == 'Something Else'


def test_the_rename_dialog_accepts_the_current_name_unchanged(gui):
    # `exclude` is what keeps a workspace from clashing with itself
    from specvizitor.widgets.WorkspaceDialogs import RenameWorkspaceDialog

    dialog = RenameWorkspaceDialog(gui['registry'], gui['win']._ws)
    dialog.accept()

    assert dialog.workspace_name == 'Active'




def test_the_clone_dialog_proposes_a_unique_name(gui):
    from specvizitor.widgets.WorkspaceDialogs import CloneWorkspaceDialog

    dialog = CloneWorkspaceDialog(gui['registry'], gui['win']._ws)

    assert dialog._name_edit.text() == 'Active (2)'
    # and it defaults to sitting next to the workspace it came from
    assert dialog._location.path == str(gui['win']._ws.path.parent)


def test_the_clone_dialog_refuses_a_name_already_taken(gui, slot_errors):
    from specvizitor.widgets.WorkspaceDialogs import CloneWorkspaceDialog

    dialog = CloneWorkspaceDialog(gui['registry'], gui['win']._ws)
    dialog._name_edit.setText('Other')
    dialog.accept()

    assert dialog.workspace_path is None


def test_the_clone_dialog_suffixes_again_when_the_obvious_clone_name_is_taken(gui, tmp_path):
    from specvizitor.config.workspace import Workspace as _Workspace
    from specvizitor.widgets.WorkspaceDialogs import CloneWorkspaceDialog

    taken = _Workspace.create(tmp_path / 'already', name='Active (2)')
    gui['registry'].register(taken.path)
    try:
        dialog = CloneWorkspaceDialog(gui['registry'], gui['win']._ws)
        assert dialog._name_edit.text() == 'Active (3)'
    finally:
        gui['registry'].forget(taken.path)


def test_open_accepts_all_three_kinds_of_target(gui):
    # the filter list is what the user sees; keep the three supported kinds in it
    assert 'workspace.yml' in MainWindow.OPEN_FILTERS
    assert '*.sviz' in MainWindow.OPEN_FILTERS
    assert '*.csv' in MainWindow.OPEN_FILTERS


def test_open_dispatches_an_archive_to_the_import_dialog(gui, slot_errors, tmp_path):
    from specvizitor.io.workspace_archive import export_workspace

    archive = tmp_path / 'shared.sviz'
    assert export_workspace(gui['other'], archive)

    gui['win'].open_path(str(archive))

    assert slot_errors == []
    assert main_window_module.ImportWorkspaceDialog.opened


def test_an_invalid_archive_does_not_reach_the_import_dialog(gui, slot_errors, tmp_path):
    archive = tmp_path / 'broken.sviz'
    archive.write_bytes(b'')

    gui['win'].open_path(str(archive))

    assert slot_errors == []
    assert not main_window_module.ImportWorkspaceDialog.opened


def test_open_dispatches_a_workspace_config_to_a_switch(gui, slot_errors):
    gui['win'].open_path(str(gui['other'].path / 'workspace.yml'))

    assert slot_errors == []
    assert gui['restarts'], "selecting workspace.yml should have switched workspaces"
    assert gui['registry'].active == str(gui['other'].path)


def test_open_dispatches_a_workspace_directory_to_a_switch(gui, slot_errors):
    # not reachable through the file dialog, but `--workspace` and a drop would land here
    gui['win'].open_path(str(gui['other'].path))

    assert slot_errors == []
    assert gui['restarts']
    assert gui['registry'].active == str(gui['other'].path)


def test_opening_an_unknown_workspace_with_a_taken_name_is_refused(gui, slot_errors, tmp_path):
    clash = Workspace.create(tmp_path / 'clash', name='Other')

    gui['win'].open_path(str(clash.path))

    assert slot_errors == []
    assert not gui['restarts']


def test_open_dispatches_anything_else_to_the_inspection_file_reader(gui, slot_errors, monkeypatch):
    opened = []
    monkeypatch.setattr(MainWindow, 'open_file', lambda self, path: opened.append(path))

    gui['win'].open_path('/nowhere/results.csv')

    assert slot_errors == []
    assert opened == ['/nowhere/results.csv']
    assert not gui['restarts']


def test_the_import_dialog_describes_a_preselected_archive(gui, tmp_path):
    """`File -> Open...` picks the archive, so the dialog must open already describing it.

    The dispatch tests above see a stubbed dialog, which is exactly what let an ordering bug in
    the real one (contents described before the label existed) through.
    """
    from specvizitor.io.workspace_archive import ExportOptions, export_workspace
    from specvizitor.widgets.WorkspaceDialogs import ImportWorkspaceDialog

    archive = tmp_path / 'shared.sviz'
    assert export_workspace(gui['other'], str(archive), ExportOptions())

    dialog = ImportWorkspaceDialog(gui['registry'], archive=str(archive))

    assert 'workspace.yml' in dialog._contents_label.text()


def _unavailable_workspace(registry, win, tmp_path, dirname='Gone'):
    """Register a workspace and then delete it, as a user clearing one out would.
    """
    import shutil

    workspace = Workspace.create(tmp_path / dirname, name='Gone')
    registry.register(workspace.path)
    shutil.rmtree(workspace.path)
    win._populate_workspace_list()
    return workspace


def test_an_unavailable_workspace_stays_clickable(gui, tmp_path):
    """Clicking a dead entry is the only way to get rid of it, so it must not be disabled.
    """
    gone = _unavailable_workspace(gui['registry'], gui['win'], tmp_path)
    try:
        entry = _recent_entry(gui['win'], 'Gone  (unavailable)')

        assert entry.isEnabled()
        # a shortcut would let Ctrl+N raise the removal prompt by accident
        assert entry.shortcut().toString() == ''
    finally:
        gui['registry'].forget(gone.path)
        gui['win']._populate_workspace_list()


def test_an_unavailable_workspace_is_listed_by_its_directory_name(gui, tmp_path):
    """With workspace.yml deleted along with the rest, there is no name left to read.
    """
    gone = _unavailable_workspace(gui['registry'], gui['win'], tmp_path, dirname='dr2_products')
    try:
        labels = [a.text() for a in _recent_entries(gui['win'])]
        assert 'dr2_products  (unavailable)' in labels
    finally:
        gui['registry'].forget(gone.path)
        gui['win']._populate_workspace_list()


def test_discarding_an_unavailable_workspace_drops_it_from_the_list(gui, slot_errors, tmp_path,
                                                                   monkeypatch):
    monkeypatch.setattr(main_window_module, 'ForgetWorkspaceDialog',
                        type('_Forget', (_StubDialog,), {'opened': [], 'exec': lambda self: 1}))

    gone = _unavailable_workspace(gui['registry'], gui['win'], tmp_path)

    _recent_entry(gui['win'], 'Gone  (unavailable)').trigger()

    assert slot_errors == []
    assert str(gone.path) not in gui['registry'].known
    assert 'Gone' not in [a.text() for a in _recent_entries(gui['win'])]
    assert not gui['restarts'], "removing an entry from the list is not a switch"


def test_keeping_an_unavailable_workspace_leaves_it_listed(gui, slot_errors, tmp_path):
    # the fixture's stub answers Cancel
    gone = _unavailable_workspace(gui['registry'], gui['win'], tmp_path)
    try:
        _recent_entry(gui['win'], 'Gone  (unavailable)').trigger()

        assert slot_errors == []
        assert str(gone.path) in gui['registry'].known
    finally:
        gui['registry'].forget(gone.path)
        gui['win']._populate_workspace_list()


def test_exporting_onto_an_existing_archive_is_refused(gui, tmp_path):
    from specvizitor.widgets.WorkspaceDialogs import ExportWorkspaceDialog

    (tmp_path / 'taken.sviz').write_bytes(b'')

    dialog = ExportWorkspaceDialog(gui['win']._ws)
    dialog._destination._line_edit.setText(str(tmp_path / 'taken.sviz'))
    dialog.accept()

    assert dialog.destination is None


def test_exporting_is_refused_even_when_the_extension_is_left_off(gui, tmp_path):
    """The extension is appended on export, so the check has to look at the resulting filename.
    """
    from specvizitor.widgets.WorkspaceDialogs import ExportWorkspaceDialog

    (tmp_path / 'taken.sviz').write_bytes(b'')

    dialog = ExportWorkspaceDialog(gui['win']._ws)
    dialog._destination._line_edit.setText(str(tmp_path / 'taken'))
    dialog.accept()

    assert dialog.destination is None


def test_exporting_to_a_free_path_is_accepted(gui, tmp_path):
    from specvizitor.widgets.WorkspaceDialogs import ExportWorkspaceDialog

    dialog = ExportWorkspaceDialog(gui['win']._ws)
    dialog._destination._line_edit.setText(str(tmp_path / 'fresh'))
    dialog.accept()

    assert dialog.destination == tmp_path / 'fresh.sviz'


def test_the_import_dialog_names_the_archive_but_does_not_offer_to_change_it(gui, tmp_path):
    from specvizitor.io.workspace_archive import ExportOptions, export_workspace
    from specvizitor.widgets.WorkspaceDialogs import ImportWorkspaceDialog

    archive = tmp_path / 'shared.sviz'
    assert export_workspace(gui['other'], str(archive), ExportOptions())

    dialog = ImportWorkspaceDialog(gui['registry'], archive=str(archive))

    # the archive was chosen in `File -> Open...`, so it is stated rather than browsed for
    assert dialog._archive_label.text() == 'shared.sviz'
    assert dialog._archive_label.toolTip() == str(archive)
    # the name is the author's, made unique for this machine: `Other` is the workspace in the
    # fixture, so its own name is already taken here
    assert dialog._name_edit.text() == 'Other (2)'
    assert dialog._name_edit.isEnabled()


def test_the_import_dialog_derives_the_directory_from_the_name(gui, tmp_path):
    from specvizitor.io.workspace_archive import ExportOptions, export_workspace
    from specvizitor.widgets.WorkspaceDialogs import ImportWorkspaceDialog

    archive = tmp_path / 'shared.sviz'
    assert export_workspace(gui['other'], str(archive), ExportOptions())

    dialog = ImportWorkspaceDialog(gui['registry'], archive=str(archive))
    dialog._name_edit.setText('JADES DR3')
    dialog._location._line_edit.setText(str(tmp_path))
    dialog.accept()

    assert dialog.workspace_name == 'JADES DR3'
    assert dialog.workspace_path == tmp_path / 'JADES_DR3'


def test_the_import_dialog_refuses_a_name_already_taken(gui, tmp_path):
    from specvizitor.io.workspace_archive import ExportOptions, export_workspace
    from specvizitor.widgets.WorkspaceDialogs import ImportWorkspaceDialog

    archive = tmp_path / 'shared.sviz'
    assert export_workspace(gui['other'], str(archive), ExportOptions())

    dialog = ImportWorkspaceDialog(gui['registry'], archive=str(archive))
    dialog._name_edit.setText('Active')
    dialog._location._line_edit.setText(str(tmp_path))
    dialog.accept()

    assert dialog.workspace_path is None


def test_the_resolve_dialog_sets_the_filled_paths_only(gui, tmp_path):
    from specvizitor.widgets.WorkspaceDialogs import ResolvePathsDialog

    workspace = Workspace.create(tmp_path / 'imported')
    dialog = ResolvePathsDialog(workspace)
    data_dir = dialog._rows[0][3]
    data_dir._line_edit.setText(str(tmp_path))
    dialog.accept()

    reopened = Workspace.open(workspace.path)
    assert reopened.config.data.dir == str(tmp_path)
    assert reopened.config.catalog.filename is None


def test_the_resolve_dialog_offers_only_the_unset_paths(gui, tmp_path):
    from specvizitor.widgets.WorkspaceDialogs import ResolvePathsDialog

    workspace = Workspace.create(tmp_path / 'imported')
    workspace.config.data.dir = str(tmp_path)
    titles = [row[0] for row in ResolvePathsDialog(workspace)._rows]

    assert 'Data directory' not in titles
    assert 'Catalog' in titles


def test_the_forget_dialog_defaults_to_keeping_the_workspace(gui, tmp_path):
    from specvizitor.widgets.WorkspaceDialogs import ForgetWorkspaceDialog

    dialog = ForgetWorkspaceDialog(str(tmp_path / 'gone'))

    assert dialog._button_box.button(QtWidgets.QDialogButtonBox.Cancel).isDefault()
    assert dialog._button_box.button(QtWidgets.QDialogButtonBox.Ok).text() == 'Forget Workspace'
