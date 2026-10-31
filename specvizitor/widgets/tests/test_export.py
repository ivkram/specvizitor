import pathlib

from astropy.table import Table
import pandas as pd
import pytest

from specvizitor.io.inspection_data import InspectionData
from specvizitor.widgets.MainWindow import MainWindow

FITS, CSV = 'FITS Files (*.fits)', 'CSV Files (*.csv)'


@pytest.mark.parametrize('path, selected_filter, expected', [
    ('out.fits', FITS, ('out.fits', 'fits')),
    ('out.csv', CSV, ('out.csv', 'csv')),
    # the extension wins over the filter
    ('out.csv', FITS, ('out.csv', 'csv')),
    ('out.FITS', CSV, ('out.FITS', 'fits')),
    # no known extension: the filter picks the format and its extension is appended
    ('out', CSV, ('out.csv', 'csv')),
    ('out.v2', FITS, ('out.v2.fits', 'fits')),
])
def test_export_target(path, selected_filter, expected):
    assert MainWindow.export_target(path, selected_filter) == (pathlib.Path(expected[0]), expected[1])


def test_inspection_results_export_to_both_formats(tmp_path):
    inspection_data = InspectionData.create([1, 2, 3], flags=['broad_line'])
    inspection_data.update_value(1, 'starred', True)

    for fmt in ('csv', 'fits'):
        assert inspection_data.write(*MainWindow.export_target(tmp_path / 'out', f'{fmt.upper()} Files (*.{fmt})'))

    from_csv = pd.read_csv(tmp_path / 'out.csv', index_col='id')
    from_fits = Table.read(tmp_path / 'out.fits')
    assert list(from_csv['starred']) == list(from_fits['starred']) == [False, True, False]
    assert 'broad_line' in from_csv.columns and 'broad_line' in from_fits.colnames


def test_a_failed_export_is_reported(tmp_path, caplog):
    inspection_data = InspectionData.create([1, 2, 3])

    assert inspection_data.write(tmp_path / 'missing_dir' / 'out.csv') is False
    assert 'Failed to write the inspection data' in caplog.text
