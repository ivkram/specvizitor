from specvizitor.utils.errors import error_message


def test_a_key_error_message_is_not_quoted():
    assert error_message(KeyError("Column `ra` not found")) == "Column `ra` not found"


def test_other_errors_are_unchanged():
    assert error_message(IndexError("out of range")) == "out of range"
    assert error_message(KeyError("a", "b")) == "('a', 'b')"
