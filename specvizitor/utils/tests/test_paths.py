import os
import stat
import sys

import pandas as pd
import pytest
import yaml

from specvizitor.io.inspection_data import InspectionData
from specvizitor.utils.params import save_yaml
from specvizitor.utils.paths import atomic_write


def test_atomic_write_creates_the_file_and_leaves_nothing_else(tmp_path):
    path = tmp_path / 'out.txt'
    with atomic_write(path) as tmp:
        tmp.write_text('new')

    assert path.read_text() == 'new'
    assert os.listdir(tmp_path) == ['out.txt']


def test_atomic_write_keeps_the_old_file_on_error(tmp_path):
    path = tmp_path / 'out.txt'
    path.write_text('old')

    with pytest.raises(RuntimeError), atomic_write(path) as tmp:
        tmp.write_text('half')
        raise RuntimeError

    assert path.read_text() == 'old'
    assert os.listdir(tmp_path) == ['out.txt']


def test_atomic_write_keeps_the_extension(tmp_path):
    with atomic_write(tmp_path / 'results.csv.gz') as tmp:
        assert tmp.name.endswith('.results.csv.gz')
        tmp.write_bytes(b'')


@pytest.mark.skipif(sys.platform == 'win32', reason="no POSIX permissions")
def test_atomic_write_keeps_the_permissions(tmp_path):
    path = tmp_path / 'out.txt'
    path.write_text('old')
    path.chmod(0o640)

    with atomic_write(path) as tmp:
        tmp.write_text('new')

    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_a_failed_save_keeps_the_inspection_file(tmp_path, monkeypatch):
    path = tmp_path / 'inspection.csv'
    inspection_data = InspectionData.create([1, 2, 3])
    inspection_data.write(path)
    before = path.read_text()

    def crash(self, filename, *args, **kwargs):
        with open(filename, 'w') as f:
            f.write('id,starr')
        raise OSError('disk full')

    monkeypatch.setattr(pd.DataFrame, 'to_csv', crash)
    inspection_data.update_value(0, 'starred', True)
    assert inspection_data.write(path) is False

    assert path.read_text() == before
    assert os.listdir(tmp_path) == ['inspection.csv']


def test_a_failed_yaml_save_keeps_the_file(tmp_path):
    path = tmp_path / 'config.yml'
    save_yaml(path, {'a': 1})
    before = path.read_text()

    with pytest.raises(yaml.YAMLError):
        save_yaml(path, {'a': object()})

    assert path.read_text() == before
    assert os.listdir(tmp_path) == ['config.yml']
