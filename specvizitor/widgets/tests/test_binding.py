"""qtpy prefers PyQt5 whenever it is installed, as it often is after an upgrade from a Qt5 version of specvizitor:
the application defaults to PyQt6, the binding it depends on, unless QT_API says otherwise.
"""

import os
import subprocess
import sys


def test_pyqt6_is_the_default_binding():
    # in a fresh interpreter: the test session has a binding loaded already
    env = {k: v for k, v in os.environ.items() if k != 'QT_API'}
    code = "import os, specvizitor.main; print(os.environ['QT_API'])"
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)

    assert result.stdout.strip() == 'pyqt6'
