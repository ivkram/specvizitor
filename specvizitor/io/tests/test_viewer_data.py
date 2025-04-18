from specvizitor.io.viewer_data import get_id_from_filename


def test_get_id_from_filename():
    idf = get_id_from_filename("stacked_2D_F300M_1.fits", r"\d+")
    assert idf == "300"

    idf = get_id_from_filename("stacked_2D_F300M_1.fits", r"(?<![0-9Ff])\d+")
    assert idf == "2"

    idf = get_id_from_filename("stacked_2D_F300M_1.fits", r"(?<![0-9Ff])\d+(?![0-9Dd])")
    assert idf == "1"

    idf = get_id_from_filename("stacked_2D_F300M_1_234.fits", r"(?<![0-9Ff])\d+(?![0-9Dd])")
    assert idf == "234"
