import pytest
import astropy.units as u

from specvizitor.io.viewer_data import set_unit_aliases


def test_aliases_are_registered():
    set_unit_aliases({'AA': ['ANGSTROMS', 'Angstroms']})

    assert u.Unit('ANGSTROMS') == u.AA
    assert u.Unit('Angstroms') == u.AA


def test_registering_replaces_the_previous_set():
    # replacing rather than adding is what lets an alias be removed without a restart
    set_unit_aliases({'AA': ['ANGSTROMS']})
    set_unit_aliases({'AA': ['Angstroms']})

    assert u.Unit('Angstroms') == u.AA
    with pytest.raises(ValueError):
        u.Unit('ANGSTROMS')


def test_removing_every_alias_takes_effect():
    set_unit_aliases({'AA': ['ANGSTROMS']})
    set_unit_aliases({})

    with pytest.raises(ValueError):
        u.Unit('ANGSTROMS')


def test_an_invalid_unit_is_reported_and_skipped(caplog):
    set_unit_aliases({'not-a-unit': ['NOPE'], 'AA': ['ANGSTROMS']})

    assert 'Invalid unit' in caplog.text
    # the valid entry is still registered
    assert u.Unit('ANGSTROMS') == u.AA


def teardown_module():
    set_unit_aliases({})
