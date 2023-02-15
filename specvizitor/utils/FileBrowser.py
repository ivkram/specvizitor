import logging
import pathlib

import qtpy.compat
from qtpy import QtWidgets

logger = logging.getLogger(__name__)


class FileBrowser(QtWidgets.QWidget):
    OpenFile = 0
    # OpenFiles = 1
    OpenDirectory = 2
    SaveFile = 3

    def __init__(self, title=None, mode=OpenFile, filename_extensions='All files (*.*)', default_path=None,
                 button_text='Browse...', parent=None):
        super().__init__(parent=parent)
        self._parent = parent

        self._title = title
        self._browser_mode = mode
        self._filter = filename_extensions  # example: 'Images (*.png *.xpm *.jpg);;Text files (*.txt)'
        self._default_path = None if default_path is None else str(pathlib.Path(default_path).resolve())

        layout = QtWidgets.QHBoxLayout()

        self._label = QtWidgets.QLabel(title)
        self._label.setFixedWidth(120)
        layout.addWidget(self._label)

        self._line_edit = QtWidgets.QLineEdit(self)
        self._line_edit.setMinimumWidth(700)
        self._line_edit.setText(self._default_path)
        layout.addWidget(self._line_edit)

        self._button = QtWidgets.QPushButton(button_text)
        self._button.setFixedWidth(120)
        self._button.clicked.connect(self._browse)
        layout.addWidget(self._button)

        self.setLayout(layout)

    @property
    def path(self):
        return self._line_edit.text()

    def filled(self):
        if not self.path:
            logger.error('The field `{}` is empty'.format(self._title.rstrip(':')))
            return False
        return True

    def exists(self):
        if self._browser_mode == FileBrowser.SaveFile:
            path_to_check = pathlib.Path(self.path).parent
        else:
            path_to_check = pathlib.Path(self.path)

        if not path_to_check.exists():
            if self._browser_mode == FileBrowser.OpenFile:
                msg = 'The file `{}` does not exist'.format(path_to_check)
            elif self._browser_mode in (FileBrowser.OpenDirectory, FileBrowser.SaveFile):
                msg = 'The directory `{}` does not exist'.format(path_to_check)
            else:
                msg = 'The path `{}` does not exist'.format(path_to_check)

            logger.error(msg)
            return False

        return True

    def _browse(self):
        path = None

        if self._browser_mode == FileBrowser.OpenFile:
            path = qtpy.compat.getopenfilename(self, caption='Choose File', basedir=self._default_path,
                                               filters=self._filter)[0]

        # elif self._browser_mode == FileBrowser.OpenFiles:
        #     self._filepaths.extend(qtpy.compat.getopenfilenames(self, caption='Choose Files',
        #                                                                   basedir=self._default_path,
        #                                                                   filters=self._filter)[0])

        elif self._browser_mode == FileBrowser.OpenDirectory:
            path = qtpy.compat.getexistingdirectory(self, caption='Choose Directory', basedir=self._default_path)

        elif self._browser_mode == FileBrowser.SaveFile:
            options = QtWidgets.QFileDialog.Options()
            # if sys.platform == 'darwin':
            #    options |= QtWidgets.QFileDialog.DontUseNativeDialog
            path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As', basedir=self._default_path,
                                                          filters=self._filter, options=options)

        if path:
            self._line_edit.setText(path)
