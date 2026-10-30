import subprocess
import sys


def test_the_io_package_does_not_depend_on_qt():
    # in a fresh interpreter: the test session itself has Qt loaded already
    code = ("import sys, specvizitor.io.catalog, specvizitor.io.data_dir, specvizitor.io.inspection_data, "
            "specvizitor.io.viewer_data, specvizitor.io.workspace_archive; "
            "print(sorted(m for m in sys.modules if m.startswith(('qtpy', 'PyQt', 'PySide'))))")
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == '[]'
