"""Regression tests for the cutout parameter handling in ViewerDataLoader.

The cutout centre is derived from the WCS for every object. It used to be written into the
widget configuration itself, which both polluted the file that gets shared with collaborators
and made it unserialisable, since `wcs.world_to_pixel` returns numpy arrays.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

pytest.importorskip('qtpy')

from astropy.wcs import WCS

from specvizitor.config import config as config_module
from specvizitor.config import data_widgets
from specvizitor.widgets.ViewerDataLoader import ViewerDataLoader

AUTHORED_LOADER_PARAMS = {'extname': 'DSCI', 'cutout_size': 20}


def _wcs_header():
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crval = [3.5, -30.4]
    wcs.wcs.crpix = [1000.0, 1200.0]
    wcs.wcs.cdelt = [-1e-5, 1e-5]
    return wcs.to_header()


class _StubViewerData:
    def __init__(self, header):
        self._header = header

    def load(self, filename, **kwargs):
        return None, self._header


class _StubCatalogEntry:
    def __init__(self, ra, dec):
        self._cols = {'ra': ra, 'dec': dec}

    def get_col(self, name):
        return self._cols[name]


class _StubWidget:
    def __init__(self, cfg):
        self.cfg = cfg
        self.title = 'Cutout'


@pytest.fixture
def loader():
    data_sources = config_module.DataSources(
        dir='/data',
        images={'Mosaic': config_module.Image(filename='mosaic.fits')},
    )
    return ViewerDataLoader(widgets={}, j=0, review=None, viewer_data=_StubViewerData(_wcs_header()),
                            data_sources=data_sources, cat_entry=_StubCatalogEntry(3.5, -30.4))


@pytest.fixture
def widget():
    cfg = data_widgets.Image(data=data_widgets.DataElement(source='Mosaic',
                                                            loader_params=dict(AUTHORED_LOADER_PARAMS)))
    return _StubWidget(cfg)


def test_the_cutout_centre_is_computed(loader, widget):
    params = loader._get_loader_params(widget)

    assert params['create_cutout'] is True
    assert 'x0' in params and 'y0' in params
    # the authored parameters are carried through alongside the computed ones
    assert params['extname'] == 'DSCI'
    assert params['cutout_size'] == 20


def test_the_cutout_centre_is_a_plain_float(loader, widget):
    params = loader._get_loader_params(widget)

    # numpy scalars reach the configuration and the YAML writer, so they must not survive here
    assert type(params['x0']) is float
    assert type(params['y0']) is float


def test_the_widget_configuration_is_left_untouched(loader, widget):
    loader._get_loader_params(widget)

    assert widget.cfg.data.loader_params == AUTHORED_LOADER_PARAMS


def test_repeated_loads_do_not_accumulate_parameters(loader, widget):
    for _ in range(3):
        loader._get_loader_params(widget)

    assert widget.cfg.data.loader_params == AUTHORED_LOADER_PARAMS


def test_a_widget_without_a_source_passes_its_parameters_through(loader):
    cfg = data_widgets.Plot1D(data=data_widgets.DataElement(filename='spec.fits',
                                                             loader_params={'extname': 'F356W'}))
    params = loader._get_loader_params(_StubWidget(cfg))

    assert params == {'extname': 'F356W'}
