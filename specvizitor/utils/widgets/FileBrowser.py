import qtpy.compat
from qtpy import QtWidgets

import logging
import pathlib

from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class FileBrowser(AbstractWidget):
    OpenFile = 0
    # OpenFiles = 1
    OpenDirectory = 2
    SaveFile = 3

    def __init__(self, mode=OpenFile, filename_extensions='All files (*.*)', default_path=None,
                 title: str = '', title_width: int | None = None, button_text='Browse...', parent=None):

        self._browser_mode = mode
        self._filter = filename_extensions  # example: 'Images (*.png *.xpm *.jpg);;Text files (*.txt)'
        self._default_path = None if default_path is None else str(pathlib.Path(default_path).resolve())

        self._title = title
        self._title_width = title_width
        self._button_text = button_text

        self._label: QtWidgets.QLabel | None = None
        self._line_edit: QtWidgets.QLineEdit | None = None
        self._button: QtWidgets.QPushButton | None = None

        super().__init__(parent=parent)

    def init_ui(self):
        self._label = QtWidgets.QLabel(self._title, self)
        if self._title_width is None:
            self._label.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        else:
            self._label.setFixedWidth(self._title_width)

        self._line_edit = QtWidgets.QLineEdit(self)
        self._line_edit.setMinimumWidth(700)
        self._line_edit.setText(self._default_path)

        self._button = QtWidgets.QPushButton(self._button_text, self)
        self._button.setFixedWidth(120)

        self._button.clicked.connect(self._browse)

    def set_layout(self):
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

    def populate(self):
        self.layout().addWidget(self._label)
        self.layout().addWidget(self._line_edit)
        self.layout().addWidget(self._button)

    @property
    def path(self) -> str:
        return self._line_edit.text()

    def is_filled(self, verbose=False) -> bool:
        if not self.path:
            if verbose:
                logger.error('The field `{}` is empty'.format(self._title.rstrip(':')))
            return False
        return True

    def exists(self, verbose=False):
        if self._browser_mode == FileBrowser.SaveFile:
            path_to_check = pathlib.Path(self.path).parent
        else:
            path_to_check = pathlib.Path(self.path)

        if not path_to_check.exists():
            if verbose:
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
            path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As', basedir=self._default_path,
                                                          filters=self._filter)

        if path:
            self._line_edit.setText(path)
