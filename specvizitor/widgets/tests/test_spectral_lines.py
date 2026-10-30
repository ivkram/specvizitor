import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import gc

import pytest

pytest.importorskip('qtpy')

from qtpy import QtWidgets

from specvizitor.config import config, data_widgets
from specvizitor.config.spectral_lines import SpectralLineData
from specvizitor.widgets.Plot1D import Plot1D


@pytest.fixture
def line_position():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widgets = []

    def _line_position(wave_unit: str, wavelength: float, x_unit: str | None, redshift: float = 0) -> float:
        cfg = data_widgets.Plot1D(x_axis=data_widgets.Axis(unit=x_unit))
        lines = SpectralLineData(wave_unit=wave_unit, wavelengths={'Ha': wavelength})

        widget = Plot1D(cfg=cfg, title='Spectrum 1D', appearance=config.Appearance(), spectral_lines=lines)
        widgets.append(widget)
        widget.set_spectral_line_positions(redshift)

        return widget._spectral_line_artists['Ha'][0].value()

    yield _line_position

    # delete the pyqtgraph widgets while the QApplication is alive: garbage-collecting them later segfaults
    for widget in widgets:
        widget.deleteLater()
    app.processEvents()
    widgets.clear()
    gc.collect()


def test_line_wavelengths_are_read_in_their_own_unit(line_position):
    assert line_position('micron', 0.6564633, x_unit='AA') == pytest.approx(6564.633)


def test_line_wavelengths_in_angstrom_are_unchanged(line_position):
    assert line_position('angstrom', 6564.633, x_unit='micron', redshift=1) == pytest.approx(1.3129266)


def test_line_wavelengths_stay_in_their_own_unit_without_an_axis_unit(line_position):
    assert line_position('micron', 0.6564633, x_unit=None) == pytest.approx(0.6564633)


@pytest.mark.parametrize('wave_unit, header', [('angstrom', 'Wavelength (Å)'), ('micron', 'Wavelength (µm)'),
                                               ('not-a-unit', 'Wavelength (not-a-unit)')])
def test_the_settings_table_shows_the_wavelength_unit(wave_unit, header):
    from specvizitor.widgets.Settings import spectral_lines_table_factory

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    table = spectral_lines_table_factory(SpectralLineData(wave_unit=wave_unit, wavelengths={'Ha': 6564.633}))

    assert table._header == ['Line', header]

    table.deleteLater()
    app.processEvents()
