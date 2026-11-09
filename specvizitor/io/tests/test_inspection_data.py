import numpy as np
import pandas as pd
import pytest
from astropy.table import Table

from specvizitor.io.catalog import Catalog
from specvizitor.io.inspection_data import FieldType, InspectionData


@pytest.fixture
def inspection_data():
    return InspectionData.create([1, 2], flags=['bad_data'])


@pytest.mark.parametrize('values, field_type', [([True, False], FieldType.BOOLEAN), ([3, 1], FieldType.INTEGER),
                                                ([0.5, np.nan], FieldType.FLOAT), (['ok', ''], FieldType.TEXT)])
def test_field_types_are_inferred_from_the_column(values, field_type):
    assert FieldType.of(pd.Series(values)) is field_type


def test_the_default_columns_are_not_fields(inspection_data):
    assert inspection_data.fields == {'bad_data': FieldType.BOOLEAN}


@pytest.mark.parametrize('field_type', list(FieldType))
def test_a_new_field_of_any_type_starts_out_empty(inspection_data, field_type):
    inspection_data.add_field('new', field_type)

    assert inspection_data.fields['new'] is field_type
    assert not inspection_data.has_data('new')


@pytest.mark.parametrize('field_type, value', [(FieldType.BOOLEAN, True), (FieldType.INTEGER, 2),
                                               (FieldType.FLOAT, 0.5), (FieldType.TEXT, 'ok')])
def test_a_field_has_data_once_a_value_is_set(inspection_data, field_type, value):
    inspection_data.add_field('new', field_type)
    inspection_data.update_value(1, 'new', value)

    assert inspection_data.has_data('new')


def test_columns_can_swap_their_names(inspection_data):
    inspection_data.add_field('emitter', FieldType.BOOLEAN)
    inspection_data.update_value(0, 'bad_data', True)

    inspection_data.rename_columns({'bad_data': 'emitter', 'emitter': 'bad_data'})

    assert list(inspection_data.fields) == ['emitter', 'bad_data']
    assert list(inspection_data.df['emitter']) == [True, False]
    assert list(inspection_data.df['bad_data']) == [False, False]


def _round_trip(inspection_data, tmp_path) -> InspectionData:
    inspection_data.write(tmp_path / 'inspection.csv')
    return InspectionData.read(tmp_path / 'inspection.csv')


def test_field_types_survive_a_round_trip_through_csv(inspection_data, tmp_path):
    for field_type, values in ((FieldType.INTEGER, [3, 1]), (FieldType.FLOAT, [0.5, 1.5]),
                               (FieldType.TEXT, ['ok', 'ok'])):
        inspection_data.add_field(field_type.value, field_type)
        for j, value in enumerate(values):
            inspection_data.update_value(j, field_type.value, value)

    assert _round_trip(inspection_data, tmp_path).fields == inspection_data.fields


@pytest.mark.xfail(strict=True, reason="CSV carries no schema: an integer column with gaps is read back as float")
def test_an_integer_field_with_gaps_survives_a_round_trip_through_csv(inspection_data, tmp_path):
    inspection_data.add_field('integer', FieldType.INTEGER)
    inspection_data.update_value(0, 'integer', 3)

    assert _round_trip(inspection_data, tmp_path).fields['integer'] is FieldType.INTEGER


@pytest.mark.parametrize('comments, expected', [(['', ''], ['', '']), (['2', ''], ['2', '']),
                                                (['1.5', 'broad Ha'], ['1.5', 'broad Ha'])])
def test_comments_are_read_as_text(tmp_path, comments, expected):
    # a column with no comments, or only numbers in it, would otherwise be read as numbers
    path = tmp_path / 'inspection.csv'
    rows = '\n'.join(f'{i},False,-1.0,{c}' for i, c in enumerate(comments, start=1))
    path.write_text(f'id,starred,z_sviz,comment\n{rows}\n')

    assert list(InspectionData.read(path).df['comment']) == expected


def test_a_file_with_secondary_ids_is_read_with_a_multi_index(tmp_path):
    path = tmp_path / 'inspection.csv'
    path.write_text('id,id2,starred,z_sviz,comment\n1,10,False,-1.0,\n1,11,True,-1.0,\n')

    inspection_data = InspectionData.read(path)

    assert inspection_data.indices == ['id', 'id2']
    assert inspection_data.get_id(1, full=True) == (1, 11)


def test_a_catalog_is_located_in_the_order_of_the_inspection_file():
    inspection_data = InspectionData.create([5, 3, 8, 1])

    rows = inspection_data.rows_in(Catalog.create([1, 9, 5, 8]))  # 9 is not under inspection

    assert list(rows) == [0, 2, 3]


def test_a_catalog_is_located_by_secondary_ids_too():
    inspection_data = InspectionData.create([1, 1, 2], [10, 11, 10])

    assert list(inspection_data.rows_in(Catalog.create([(2, 10), (1, 11)]))) == [1, 2]
    assert len(inspection_data.rows_in(Catalog.create([1, 2]))) == 0  # the secondary IDs are missing


def test_a_catalog_with_string_ids_from_a_fits_file_is_located(tmp_path):
    path = tmp_path / 'subset.fits'
    Table({'id': ['b', 'x', 'a']}).write(path)

    assert list(InspectionData.create(['a', 'b', 'c']).rows_in(Catalog.read(str(path)))) == [0, 1]
