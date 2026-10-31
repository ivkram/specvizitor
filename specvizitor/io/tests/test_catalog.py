from astropy.table import MaskedColumn, Table
import numpy as np
import pytest

from specvizitor.io.catalog import Catalog

TRANSLATE = {'id': ['NUMBER', 'ID'], 'redshift': ['z', 'Z_SPEC']}


def _write(tmp_path, name='cat.fits', **columns) -> str:
    path = tmp_path / name
    Table(columns).write(path)
    return str(path)


@pytest.fixture
def cat_file(tmp_path):
    return _write(tmp_path, NUMBER=[3, 1, 2], z=[0.5, 1.5, 2.5], FIELD=['GN', 'GS', 'GN'])


def test_create_indexes_single_ids():
    cat = Catalog.create([10, 20, 30])

    assert len(cat) == 3
    assert cat.indices == ['id']
    assert cat.get_cat_entry(20).get_col('id') == 20


def test_create_indexes_composite_ids():
    cat = Catalog.create([(1, 'a'), (1, 'b'), (2, 'a')])

    assert cat.indices == ['id', 'id2']
    entry = cat.get_cat_entry((1, 'b'))
    assert (entry.get_col('id'), entry.get_col('id2')) == (1, 'b')


def test_read_finds_the_id_column_through_its_alias(cat_file):
    cat = Catalog.read(cat_file, translate=TRANSLATE)

    assert cat.indices == ['NUMBER']
    assert list(cat.get_col('id')) == [3, 1, 2]
    assert cat.get_cat_entry(1).get_col('redshift') == pytest.approx(1.5)


def test_read_without_aliases_needs_an_id_column(tmp_path, caplog):
    assert Catalog.read(_write(tmp_path, id=[1, 2], z=[0.1, 0.2])) is not None
    assert Catalog.read(_write(tmp_path, 'no_id.fits', NUMBER=[1, 2])) is None
    assert '`id` column not found' in caplog.text


def test_the_columns_are_annotated_with_their_aliases(cat_file):
    cat = Catalog.read(cat_file, translate=TRANSLATE)

    assert cat.annotated_colnames == {'NUMBER': 'NUMBER (id)', 'z': 'z (redshift)', 'FIELD': 'FIELD'}
    assert set(cat.extended_colnames) == {'NUMBER', 'z', 'FIELD', 'id', 'redshift'}


def test_a_missing_column_names_its_aliases(cat_file):
    cat = Catalog.read(cat_file, translate={**TRANSLATE, 'ra': ['RA', 'ALPHA_J2000']})

    with pytest.raises(KeyError, match='RA, ALPHA_J2000'):
        cat.get_col('ra')
    with pytest.raises(KeyError, match='`dec` column not found'):
        cat.get_col('dec')


def test_an_unreadable_file_is_reported(tmp_path, caplog):
    assert Catalog.read(str(tmp_path / 'missing.fits')) is None
    assert 'Failed to load the catalog' in caplog.text


def test_missing_ids_make_the_catalog_invalid(tmp_path, caplog):
    path = tmp_path / 'cat.fits'
    Table({'id': MaskedColumn([1, 2, 3], mask=[False, True, False])}).write(path)

    assert Catalog.read(str(path)) is None
    assert 'Some IDs are missing' in caplog.text


def test_the_catalog_can_be_filtered_by_the_data_directory(cat_file, tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    for obj_id in (1, 3, 99):
        (data_dir / f'spec_{obj_id}.fits').touch()

    cat = Catalog.read(cat_file, translate=TRANSLATE, data_dir=data_dir)

    assert sorted(cat.get_col('id')) == [1, 3]


def test_a_catalog_left_empty_by_the_filter_is_refused(cat_file, tmp_path, caplog):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'spec_99.fits').touch()

    assert Catalog.read(cat_file, translate=TRANSLATE, data_dir=data_dir) is None
    assert 'The processed catalog is empty' in caplog.text


def test_a_missing_object_is_reported_unless_ignored(caplog):
    cat = Catalog.create([1, 2])

    assert cat.get_cat_entry(7, ignore_missing=True) is None
    assert caplog.text == ''

    assert cat.get_cat_entry(7) is None
    assert 'Object not found in the catalog (ID: 7)' in caplog.text


def test_a_duplicate_id_is_reported(caplog):
    cat = Catalog.create([1, 2, 2])

    assert cat.get_cat_entry(2) is None
    assert 'multiple entries' in caplog.text


def test_an_id_of_an_unknown_type_is_reported(caplog):
    cat = Catalog.create([1, 2])

    assert cat.get_cat_entry(np.float64(1.0)) is None
    assert 'Unknown object ID type' in caplog.text


def test_update_translate_re_resolves_the_id_column(tmp_path):
    cat = Catalog.read(_write(tmp_path, ID=[1, 2], OBJ=[5, 6]), translate={'id': ['ID']})

    updated = cat.update_translate({'id': ['OBJ']})

    assert updated.indices == ['OBJ']
    assert updated.get_cat_entry(6).get_col('ID') == 2


def test_update_translate_without_aliases(tmp_path):
    cat = Catalog.read(_write(tmp_path, id=[1, 2]), translate={'id': ['ID']})

    assert cat.update_translate(None) is not None
