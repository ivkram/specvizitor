import pathlib

import numpy as np
from pyqtgraph.Qt import QtWidgets


class FileBrowser(QtWidgets.QWidget):
    OpenFile = 0
    # OpenFiles = 1
    OpenDirectory = 2
    SaveFile = 3

    def __init__(self, title=None, mode=OpenFile, filename_extensions='All files (*.*)', default_path=None,
                 button_text='Browse...', parent=None):

        super().__init__(parent=parent)

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
        self._button.clicked.connect(self._get_file)
        layout.addWidget(self._button)

        self.setLayout(layout)

    def _get_file(self):
        filepath = ""

        if self._browser_mode == FileBrowser.OpenFile:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, caption='Choose File',
                                                             directory=self._default_path,
                                                             filter=self._filter)[0]
        # elif self._browser_mode == FileBrowser.OpenFiles:
        #     self._filepaths.extend(QtWidgets.QFileDialog.getOpenFileNames(self, caption='Choose Files',
        #                                                                   directory=self._default_path,
        #                                                                   filter=self._filter)[0])
        elif self._browser_mode == FileBrowser.OpenDirectory:
            filepath = QtWidgets.QFileDialog.getExistingDirectory(self, caption='Choose Directory',
                                                                  directory=self._default_path)
        elif self._browser_mode == FileBrowser.SaveFile:
            options = QtWidgets.QFileDialog.Options()
            # if sys.platform == 'darwin':
            #    options |= QtWidgets.QFileDialog.DontUseNativeDialog
            filepath, extension = QtWidgets.QFileDialog.getSaveFileName(self, caption='Save/Save As',
                                                                        directory=self._default_path,
                                                                        filter=self._filter, options=options)

        if filepath:
            self._line_edit.setText(filepath)

    def get_path(self):
        return self._line_edit.text()


class CustomSlider(QtWidgets.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._n = int((max_value - min_value) / step) + 1
        self._arr = np.linspace(min_value, max_value, self._n)

        self.default_index = self.index_from_value(default_value)

        self.setRange(1, self._n)
        self.setSingleStep(1)
        self.setValue(self.default_index)

        self._index = self.default_index

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, i):
        self._index = i
        self.setValue(i)

    @property
    def value(self):
        return self._arr[self.index - 1]

    def index_from_value(self, value):
        if value is None:
            return 1
        else:
            return self._arr.searchsorted(value, side='right')

    def reset(self):
        self.index = self.default_index
