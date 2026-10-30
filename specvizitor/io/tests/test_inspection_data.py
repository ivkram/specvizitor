import numpy as np
import pandas as pd
import pytest

from specvizitor.io.inspection_data import FieldType, InspectionData


@pytest.fixture
def review():
    return InspectionData.create([1, 2], flags=['bad_data'])


@pytest.mark.parametrize('values, field_type', [([True, False], FieldType.BOOLEAN), ([3, 1], FieldType.INTEGER),
                                                ([0.5, np.nan], FieldType.FLOAT), (['ok', ''], FieldType.TEXT)])
def test_field_types_are_inferred_from_the_column(values, field_type):
    assert FieldType.of(pd.Series(values)) is field_type


def test_the_default_columns_are_not_fields(review):
    assert review.fields == {'bad_data': FieldType.BOOLEAN}


@pytest.mark.parametrize('field_type', list(FieldType))
def test_a_new_field_of_any_type_starts_out_empty(review, field_type):
    review.add_field('new', field_type)

    assert review.fields['new'] is field_type
    assert not review.has_data('new')


@pytest.mark.parametrize('field_type, value', [(FieldType.BOOLEAN, True), (FieldType.INTEGER, 2),
                                               (FieldType.FLOAT, 0.5), (FieldType.TEXT, 'ok')])
def test_a_field_has_data_once_a_value_is_set(review, field_type, value):
    review.add_field('new', field_type)
    review.update_value(1, 'new', value)

    assert review.has_data('new')


def test_columns_can_swap_their_names(review):
    review.add_field('emitter', FieldType.BOOLEAN)
    review.update_value(0, 'bad_data', True)

    review.rename_columns({'bad_data': 'emitter', 'emitter': 'bad_data'})

    assert list(review.fields) == ['emitter', 'bad_data']
    assert list(review.df['emitter']) == [True, False]
    assert list(review.df['bad_data']) == [False, False]


def _round_trip(review, tmp_path) -> InspectionData:
    review.write(tmp_path / 'inspection.csv')
    return InspectionData.read(tmp_path / 'inspection.csv')


def test_field_types_survive_a_round_trip_through_csv(review, tmp_path):
    for field_type, values in ((FieldType.INTEGER, [3, 1]), (FieldType.FLOAT, [0.5, 1.5]),
                               (FieldType.TEXT, ['ok', 'ok'])):
        review.add_field(field_type.value, field_type)
        for j, value in enumerate(values):
            review.update_value(j, field_type.value, value)

    assert _round_trip(review, tmp_path).fields == review.fields


@pytest.mark.xfail(strict=True, reason="CSV carries no schema: an integer column with gaps is read back as float")
def test_an_integer_field_with_gaps_survives_a_round_trip_through_csv(review, tmp_path):
    review.add_field('integer', FieldType.INTEGER)
    review.update_value(0, 'integer', 3)

    assert _round_trip(review, tmp_path).fields['integer'] is FieldType.INTEGER
