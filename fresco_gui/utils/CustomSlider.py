import numpy as np
from pyqtgraph.Qt import QtGui


class CustomSlider(QtGui.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)

        n = int((max_value - min_value) / step) + 1
        self._arr = np.linspace(min_value, max_value, n)

        if default_value is None:
            self._default_index = 1
        else:
            self._default_index = self._index_from_value(default_value)

        self.setRange(1, n)
        self.setSingleStep(1)
        self.setValue(self._default_index)

        self.index = self._default_index

    @property
    def value(self):
        return self._arr[self.index - 1]

    def _index_from_value(self, value):
        index = self._arr.searchsorted(value) + 1
        if index == len(self._arr) + 1:
            index = len(self._arr)
        return index

    def update_index(self, value):
        self.index = self._index_from_value(value)
        self.setValue(self.index)

    def reset(self):
        self.index = self._default_index
        self.setValue(self._default_index)
