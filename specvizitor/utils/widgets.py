import pathlib

import numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui


class FileBrowser(QtWidgets.QWidget):
    OpenFile = 0
    OpenFiles = 1
    OpenDirectory = 2
    SaveFile = 3

    def __init__(self, title, default_path="", button_text="Search...", mode=OpenFile):
        super().__init__()

        self._browser_mode = mode
        self._filter = 'All files (*.*)'
        self._default_path = pathlib.Path().resolve() if default_path is None else default_path

        layout = QtWidgets.QHBoxLayout()

        self._label = QtWidgets.QLabel(title)
        self._label.setFixedWidth(250)
        layout.addWidget(self._label)

        self._line_edit = QtWidgets.QLineEdit(self)
        self._line_edit.setMinimumWidth(700)
        self._line_edit.setText(default_path)
        layout.addWidget(self._line_edit)

        self._button = QtWidgets.QPushButton(button_text)
        self._button.setFixedWidth(120)
        self._button.clicked.connect(self._get_file)
        layout.addWidget(self._button)

        self.setLayout(layout)

    # --------------------------------------------------------------------
    # For example,
    #    setFileFilter('Images (*.png *.xpm *.jpg)')
    def _set_file_filter(self, text):
        self._filter = text

    def _get_file(self):
        self.filepaths = []

        if self._browser_mode == FileBrowser.OpenFile:
            self.filepaths.append(QtWidgets.QFileDialog.getOpenFileName(self, caption='Choose File',
                                                                        directory=self._default_path,
                                                                        filter=self._filter)[0])
        elif self._browser_mode == FileBrowser.OpenFiles:
            self.filepaths.extend(QtWidgets.QFileDialog.getOpenFileNames(self, caption='Choose Files',
                                                                         directory=self._default_path,
                                                                         filter=self._filter)[0])
        elif self._browser_mode == FileBrowser.OpenDirectory:
            self.filepaths.append(QtWidgets.QFileDialog.getExistingDirectory(self, caption='Choose Directory',
                                                                             directory=self._default_path))
        else:
            options = QtWidgets.QFileDialog.Options()
            # if sys.platform == 'darwin':
            #    options |= QtWidgets.QFileDialog.DontUseNativeDialog
            self.filepaths.append(QtWidgets.QFileDialog.getSaveFileName(self, caption='Save/Save As',
                                                                        directory=self._default_path,
                                                                        filter=self._filter,
                                                                        options=options)[0])
        if len(self.filepaths) == 0:
            return
        elif len(self.filepaths) == 1:
            self._line_edit.setText(self.filepaths[0])
        else:
            self._line_edit.setText(",".join(self.filepaths))

    def _get_paths(self):
        return self.filepaths


class CustomSlider(QtWidgets.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._n = int((max_value - min_value) / step) + 1
        self._arr = np.linspace(min_value, max_value, self._n)

        if default_value is None:
            self._default_index = 1
        else:
            self._default_index = self._get_index_from_value(default_value)

        self.setRange(1, self._n)
        self.setSingleStep(1)
        self.setValue(self._default_index)

        self.index = self._default_index

    def _get_index_from_value(self, value):
        return self._arr.searchsorted(value, side='right')

    @property
    def value(self):
        return self._arr[self.index - 1]

    def update_index(self, value):
        self.index = self._get_index_from_value(value)
        self.setValue(self.index)

    def reset(self):
        self.index = self._default_index
        self.setValue(self._default_index)
