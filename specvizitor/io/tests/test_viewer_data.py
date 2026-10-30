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


@pytest.fixture
def fits_file(tmp_path):
    from astropy.io import fits
    import numpy as np

    path = tmp_path / 'data.fits'
    hdus = [fits.PrimaryHDU()] + [fits.ImageHDU(np.full((2, 2), i), name='LINE', ver=i + 1) for i in range(2)]
    fits.HDUList(hdus).writeto(path)
    return str(path)


@pytest.fixture
def fits_loader(fits_file):
    from specvizitor.io.viewer_data import GenericFITSLoader

    loader = GenericFITSLoader()
    loader.open(fits_file)
    yield loader
    loader.close()


@pytest.fixture
def viewer_data():
    from specvizitor.io.viewer_data import ViewerData

    viewer_data = ViewerData()
    yield viewer_data
    viewer_data.close_all()


def test_fits_extension_is_selected_by_extver_index(fits_loader):
    data, _ = fits_loader.load(extname='LINE', extver_index=-1)
    assert data[0, 0] == 1


def test_missing_fits_extension_is_reported_by_name(fits_loader):
    with pytest.raises(KeyError, match='Extension `SCI` not found'):
        fits_loader.load(extname='SCI')


def test_missing_fits_extension_with_extver_index_is_reported_by_name(fits_loader):
    with pytest.raises(KeyError, match='Extension `SCI` not found'):
        fits_loader.load(extname='SCI', extver_index=0)


def test_out_of_range_extver_index_is_reported(fits_loader):
    with pytest.raises(IndexError, match='out of range'):
        fits_loader.load(extname='LINE', extver_index=5)


def test_a_missing_extension_is_logged_without_quotes(fits_file, viewer_data, caplog):
    data, _ = viewer_data.load(fits_file, extname='SCI')

    assert data is None
    assert "GenericFITSLoader: Extension `SCI` not found (filename:" in caplog.text


def test_an_unknown_loader_is_reported_without_raising(fits_file, viewer_data, caplog):
    data, meta = viewer_data.load(fits_file, loader='fitz')

    assert (data, meta) == (None, None)
    assert "Unknown loader type: `fitz`" in caplog.text
