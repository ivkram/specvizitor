import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets

from specvizitor.utils.widgets.ParamTable import TableRowEditor


@pytest.fixture
def editor():
    dialogs = []

    def _editor(header: list[str]) -> TableRowEditor:
        dialog = TableRowEditor(header=header, data=['Ha', '6564.633'])
        dialogs.append(dialog)
        dialog.show()
        QtWidgets.QApplication.processEvents()
        return dialog

    yield _editor

    for dialog in dialogs:
        dialog.close()


def test_long_labels_are_not_cut_off_and_the_editors_line_up(editor):
    dialog = editor(['Line', 'Wavelength (Å, vacuum, rest frame)'])
    labels, editors = zip(*dialog._row_items)

    assert all(label.width() >= label.sizeHint().width() for label in labels)
    assert len({e.x() for e in editors}) == 1
