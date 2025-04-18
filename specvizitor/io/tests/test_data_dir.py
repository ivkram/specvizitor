from specvizitor.io.data_dir import _get_id_from_filename, get_ids_from_dir


def test_get_id_from_filename():
    obj_id = _get_id_from_filename("stacked_2D_F300M_1.fits", r"\d+")
    assert obj_id == "300"

    obj_id = _get_id_from_filename("stacked_2D_F300M_1.fits", r"(?<![0-9Ff])\d+")
    assert obj_id == "2"

    obj_id = _get_id_from_filename("stacked_2D_F300M_1.fits", r"(?<![0-9Ff])\d+(?![0-9Dd])")
    assert obj_id == "1"

    obj_id = _get_id_from_filename("stacked_2D_F300M_1_234.fits", r"(?<![0-9Ff])\d+(?![0-9Dd])")
    assert obj_id == "234"


def test_get_ids_from_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "123.fits").touch()
    wfss_dir = tmp_path / "wfss"
    wfss_dir.mkdir()
    (wfss_dir / "456.fits").touch()

    ids = get_ids_from_dir(tmp_path)
    assert list(ids) == [123]

    ids = get_ids_from_dir(tmp_path, recursive=True)
    assert list(ids) == [123, 456]
