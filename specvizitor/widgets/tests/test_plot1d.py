import gc

from astropy.table import Table
import astropy.units as u
import numpy as np
import pytest

pytest.importorskip('qtpy')

from qtpy import QtCore

from specvizitor.config import config, data_widgets
from specvizitor.config.spectral_lines import SpectralLineData
from specvizitor.io.inspection_data import InspectionData
from specvizitor.io.viewer_data import LocalPath
from specvizitor.widgets.Plot1D import Plot1D

INSPECTION_DATA = InspectionData.create([1])


def _spectrum(n=50) -> Table:
    wave = np.linspace(1, 2, n) * u.micron
    flux = np.exp(-0.5 * ((wave.value - 1.5) / 0.05) ** 2) * u.Jy
    return Table({'wave': wave, 'flux': flux, 'model': 0.5 * flux})


def _plots(**plots) -> dict[str, data_widgets.LinePlot]:
    return {label: data_widgets.LinePlot(x='wave', y=y, **kwargs) for label, (y, kwargs) in plots.items()}


@pytest.fixture
def make_plot():
    widgets = []

    def _make_plot(data: Table, plots: dict, **cfg) -> Plot1D:
        widget = Plot1D(cfg=data_widgets.Plot1D(plots=plots, **cfg), title='Spectrum 1D',
                        appearance=config.Appearance(), spectral_lines=SpectralLineData())
        widgets.append(widget)
        widget.set_data(data, None, LocalPath('spectrum.fits'))
        widget.load_object(0, INSPECTION_DATA, None, None)
        return widget

    yield _make_plot

    # delete the pyqtgraph widgets for real: garbage-collecting them later segfaults
    for widget in widgets:
        widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def test_each_line_plot_is_drawn(make_plot):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {}), Model=('model', {})))

    assert list(widget.plot_data_items) == ['Data', 'Model']
    assert all(item in widget._registered_items for item in widget.plot_data_items.values())


def test_the_axes_take_their_labels_and_units_from_the_first_line(make_plot):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {}), Model=('model', {})))

    assert (widget._axes.x.label, widget._axes.x.unit) == ('wave', u.micron)
    assert (widget._axes.y.label, widget._axes.y.unit) == ('flux', u.Jy)


def test_the_default_range_covers_every_line(make_plot):
    data = _spectrum()
    data['model'][0] = 3
    widget = make_plot(data, _plots(Data=('flux', {}), Model=('model', {})))

    assert widget._axes.x.limits == pytest.approx((1, 2))
    assert widget._axes.y.limits == pytest.approx((0, 3), abs=1e-6)


def test_infinite_and_missing_values_do_not_stretch_the_range(make_plot):
    data = _spectrum()
    data['flux'][0] = np.inf
    data['flux'][1] = np.nan
    widget = make_plot(data, _plots(Data=('flux', {})))

    finite = data['flux'][2:]
    assert widget._axes.y.limits == pytest.approx((finite.min(), finite.max()))


def test_a_missing_column_skips_its_line(make_plot, caplog):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {}), Error=('flux_err', {})))

    assert list(widget.plot_data_items) == ['Data']
    assert 'Column not found: flux_err' in caplog.text


def test_a_legend_is_shown_only_for_labelled_lines(make_plot):
    hidden = make_plot(_spectrum(), _plots(Data=('flux', {'hide_label': True})))
    labelled = make_plot(_spectrum(), _plots(Data=('flux', {})))

    assert hidden.container.legend is None
    assert labelled.container.legend is not None


def test_the_x_axis_can_be_shown_in_another_unit(make_plot):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {})), x_axis=data_widgets.Axis(unit='AA'))

    x, _ = widget.plot_data_items['Data'].getData()
    assert (x[0], x[-1]) == pytest.approx((1e4, 2e4))


def test_a_log_scale_is_applied_to_the_data(make_plot):
    data = _spectrum()
    widget = make_plot(data, _plots(Data=('flux', {})), y_axis=data_widgets.Axis(scale='log'))

    _, y = widget.plot_data_items['Data'].getData()
    assert y == pytest.approx(np.log10(data['flux'].value))


def test_smoothing_can_be_undone(make_plot):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {})))
    _, original = widget.plot_data_items['Data'].getData()
    original = original.copy()

    widget.smooth_data(3)
    _, smoothed = widget.plot_data_items['Data'].getData()
    assert smoothed.max() < original.max()

    widget.smooth_data(0)
    _, restored = widget.plot_data_items['Data'].getData()
    assert np.array_equal(restored, original)


def test_loading_another_object_replaces_the_lines(make_plot):
    widget = make_plot(_spectrum(), _plots(Data=('flux', {})))
    n_items = len(widget._registered_items)

    widget.load_object(0, INSPECTION_DATA, None, None)

    assert len(widget._registered_items) == n_items
