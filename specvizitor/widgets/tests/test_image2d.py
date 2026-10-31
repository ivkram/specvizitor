import gc

from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import numpy as np
import pytest

pytest.importorskip('qtpy')

from qtpy import QtCore

from specvizitor.config import config, data_widgets
from specvizitor.config.spectral_lines import SpectralLineData
from specvizitor.io.catalog import Catalog
from specvizitor.io.inspection_data import InspectionData
from specvizitor.io.viewer_data import LocalPath
from specvizitor.utils.widgets import MyTextItem
from specvizitor.widgets.Image2D import Image2D

INSPECTION_DATA = InspectionData.create([1])


@pytest.fixture
def make_image():
    widgets = []

    def _make_image(data, meta=None, cat_entry=None, cat=None, prepared=None, **cfg) -> Image2D:
        widget = Image2D(cfg=data_widgets.Image(**cfg), title='Image', appearance=config.Appearance(),
                         spectral_lines=SpectralLineData())
        widgets.append(widget)
        data = np.asarray(data, dtype=float)
        if prepared is None:  # as the loader does, in its thread
            prepared = widget.prepare_data(data, meta)
        widget.set_data(data, meta, LocalPath('image.fits'), prepared)
        widget.load_object(0, INSPECTION_DATA, cat_entry, cat)
        return widget

    yield _make_image

    # delete the pyqtgraph widgets for real: garbage-collecting them later segfaults
    for widget in widgets:
        widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def _levels(widget: Image2D) -> tuple[float, float]:
    return widget._default_levels.min, widget._default_levels.max


def _ramp(nx=20, ny=10) -> np.ndarray:
    return np.arange(nx * ny, dtype=float).reshape(ny, nx)


def test_an_image_spans_its_pixels(make_image):
    widget = make_image(_ramp(nx=20, ny=10))

    assert widget.image_item in widget._registered_items
    assert widget._axes.x.limits == (0, 20)
    assert widget._axes.y.limits == (0, 10)


def test_the_default_levels_are_the_data_range(make_image):
    data = _ramp()
    data[0, 0] = np.nan

    assert _levels(make_image(data)) == (1, 199)


def test_user_levels_fall_back_to_the_data_range(make_image):
    limits = data_widgets.ColorBarLimits(type='user', min=50)
    widget = make_image(_ramp(), color_bar=data_widgets.ColorBar(limits=limits))

    assert _levels(widget) == (50, 199)


def test_zscale_levels_lie_within_the_data(make_image):
    limits = data_widgets.ColorBarLimits(type='zscale')
    lo, hi = _levels(make_image(_ramp(), color_bar=data_widgets.ColorBar(limits=limits)))

    assert 0 <= lo < hi <= 199


@pytest.mark.parametrize('data', [np.zeros((5, 5)), np.full((5, 5), np.nan)])
def test_an_empty_image_keeps_the_default_levels(make_image, data):
    assert _levels(make_image(data)) == (0, 1)


def test_the_levels_prepared_by_the_loader_are_used(make_image):
    # the loader thread computes them, so that the main thread does not have to
    assert _levels(make_image(_ramp(), prepared={'levels': (3, 7)})) == (3, 7)


def test_the_levels_are_not_computed_on_the_main_thread(make_image):
    # e.g. if preparing the data failed in the loader: computing them again would likely fail again
    assert _levels(make_image(_ramp(), prepared={})) == (0, 1)


def test_resetting_an_unsmoothed_image_does_not_set_it_again(make_image):
    # setting an image recomputes the histogram of its colorbar and of every colorbar linked to it
    widget = make_image(_ramp())
    images_set = []
    widget.image_item.sigImageChanged.connect(lambda: images_set.append(1))
    widget.reset_view()

    assert images_set == []


def test_the_data_is_shown_again_once_the_smoothing_is_undone(make_image):
    widget = make_image(_ramp())
    widget.smooth_data(2.0)
    assert not np.array_equal(widget.image_item.image, _ramp())

    widget.smooth_data(0)
    assert np.array_equal(widget.image_item.image, _ramp())


def test_reset_view_applies_the_default_levels(make_image):
    widget = make_image(_ramp())
    widget.reset_view()

    assert widget.cbar.getLevels() == pytest.approx((0, 199))


def test_central_axes_and_crosshair_are_drawn(make_image):
    plain = make_image(_ramp())
    decorated = make_image(_ramp(), central_axes=data_widgets.ImageCentralAxes(x=True, y=True),
                           central_crosshair=True)

    assert len(decorated._registered_items) == len(plain._registered_items) + 4


def test_loading_another_object_replaces_the_items(make_image):
    widget = make_image(_ramp(), central_crosshair=True)
    n_items = len(widget._registered_items)

    widget.load_object(0, INSPECTION_DATA, None, None)

    assert len(widget._registered_items) == n_items


@pytest.mark.parametrize('angle', [30, 90, 180, 270])
def test_a_fixed_rotation_is_applied(make_image, angle):
    widget = make_image(_ramp(), rotate=angle)

    assert widget._qtransform.m12() == pytest.approx(np.sin(np.radians(angle)), abs=1e-9)
    assert widget.container.getViewBox().state['aspectLocked'] == pytest.approx(1)


def test_the_aspect_ratio_keeps_the_sign_of_a_flipped_axis():
    from qtpy import QtGui

    flipped = QtGui.QTransform(-2, 0, 0, 1, 0, 0)

    assert Image2D._aspect_ratio(flipped) == pytest.approx(-0.5)
    assert Image2D._aspect_ratio(QtGui.QTransform().rotate(90)) == pytest.approx(1)


def _cat_entry(**columns) -> Catalog:
    return Catalog(Table({'id': [1], **{k: [v] for k, v in columns.items()}}), indices=['id']).get_cat_entry(1)


def test_auto_rotation_reads_the_position_angle(make_image):
    widget = make_image(_ramp(), cat_entry=_cat_entry(PA=90.0), rotate='auto')

    assert widget._qtransform.m12() == pytest.approx(1)


def test_auto_rotation_without_a_position_angle_is_skipped(make_image, caplog):
    widget = make_image(_ramp(), cat_entry=_cat_entry(), rotate='auto')

    assert widget._qtransform.isIdentity()
    assert '`PA` column not found' in caplog.text


def test_smoothing_can_be_undone(make_image):
    data = np.zeros((21, 21))
    data[10, 10] = 1
    widget = make_image(data)

    widget.smooth_data(2)
    assert widget.image_item.image[10, 10] < 1
    assert widget.image_item.image[10, 12] > 0

    widget.smooth_data(0)
    assert np.array_equal(widget.image_item.image, data)


def _wcs_header(nx=20, ny=10) -> fits.Header:
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    wcs.wcs.crval = [150, 2]
    wcs.wcs.crpix = [nx / 2 + 0.5, ny / 2 + 0.5]
    wcs.wcs.cdelt = [-1 / 3600, 1 / 3600]
    return wcs.to_header()


def test_sources_inside_the_image_are_labelled(make_image):
    # one source at the centre, one a degree away
    cat = Catalog(Table({'id': [7, 8], 'ra': [150.0, 151.0], 'dec': [2.0, 2.0]}), indices=['id'])

    widget = make_image(_ramp(), meta=_wcs_header(), cat=cat, show_sources=True)

    labels = [item for item in widget._registered_items if isinstance(item, MyTextItem)]
    assert [label.textItem.toPlainText() for label in labels] == ['7']
    assert labels[0].pos().x() == pytest.approx(9.5, abs=0.01)


def test_sources_need_coordinates(make_image, caplog):
    cat = Catalog(Table({'id': [7]}), indices=['id'])

    widget = make_image(_ramp(), meta=_wcs_header(), cat=cat, show_sources=True)

    assert not [item for item in widget._registered_items if isinstance(item, MyTextItem)]
    assert '`ra` column not found' in caplog.text
