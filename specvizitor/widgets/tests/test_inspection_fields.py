"""The inspection field editor lists every user-defined field with its type, while new fields can only
be of a type that the inspection results widget can display.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import re
from types import SimpleNamespace

import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets

from specvizitor.io.inspection_data import FieldType, InspectionData
from specvizitor.utils.widgets.ParamTable import TableRowEditor
from specvizitor.widgets.InspectionFieldEditor import inspection_field_table_factory
from specvizitor.widgets.MainWindow import MainWindow


@pytest.fixture
def review(tmp_path):
    # `quality` is not a flag, e.g. a column added by hand
    path = tmp_path / 'inspection.csv'
    path.write_text("id,starred,z_sviz,comment,quality,bad_data,emitter\n"
                    "1,False,-1.0,,3,False,True\n"
                    "2,False,-1.0,,1,True,False\n")
    return InspectionData.read(path)


@pytest.fixture
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widgets = []
    yield widgets.append
    for widget in widgets:
        widget.deleteLater()
    app.processEvents()


def _apply(review, fields, is_deleted):
    window = SimpleNamespace(rd=SimpleNamespace(review=review))
    MainWindow.update_inspection_fields(window, fields, is_deleted, set_as_default=False)


def test_the_editor_lists_every_field_with_its_type(review, app):
    table = inspection_field_table_factory(review)
    app(table)

    assert table._old_data == [['quality', 'integer'], ['bad_data', 'boolean'], ['emitter', 'boolean']]
    assert table._row_editor_kwargs['item_choices'] == [None, ['boolean']]


@pytest.mark.parametrize('name, reserved', [('starred', True), ('z_sviz', True), ('id', True), ('  ', True),
                                            ('agn', False)])
def test_a_new_field_cannot_take_the_name_of_a_default_column(review, app, name, reserved):
    table = inspection_field_table_factory(review)
    app(table)

    pattern = table._row_editor_kwargs['regex_pattern'][0]
    assert bool(re.match(pattern, name)) is reserved


def test_the_type_of_a_field_that_cannot_be_created_is_kept_on_edit(app):
    editor = TableRowEditor(header=['Field', 'Type'], data=['quality', 'integer'], item_choices=[None, ['boolean']])
    app(editor)

    combo = editor._row_items[1][1]
    assert [combo.itemText(i) for i in range(combo.count())] == ['integer']
    assert not combo.isEnabled()


def test_deleting_a_flag_leaves_the_other_fields_alone(review):
    _apply(review, [('quality', 'integer'), ('bad_data', 'boolean'), ('emitter', 'boolean')], [False, False, True])

    assert review.fields == {'quality': FieldType.INTEGER, 'bad_data': FieldType.BOOLEAN}
    assert list(review.df['quality']) == [3, 1]
    assert list(review.df['bad_data']) == [False, True]


def test_a_field_that_is_not_a_flag_can_be_renamed(review):
    _apply(review, [('grade', 'integer'), ('bad_data', 'boolean'), ('emitter', 'boolean')], [False, False, False])

    assert list(review.fields) == ['grade', 'bad_data', 'emitter']
    assert list(review.df['grade']) == [3, 1]


def test_two_fields_can_swap_their_names(review):
    _apply(review, [('quality', 'integer'), ('emitter', 'boolean'), ('bad_data', 'boolean')], [False, False, False])

    assert list(review.df['emitter']) == [False, True]
    assert list(review.df['bad_data']) == [True, False]


def test_a_new_field_is_added_after_the_existing_ones(review):
    _apply(review, [('quality', 'integer'), ('bad_data', 'boolean'), ('emitter', 'boolean'), ('agn', 'boolean')],
           [False, False, False, False])

    assert review.fields == {'quality': FieldType.INTEGER, 'bad_data': FieldType.BOOLEAN,
                             'emitter': FieldType.BOOLEAN, 'agn': FieldType.BOOLEAN}
