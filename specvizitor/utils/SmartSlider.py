import numpy as np
from qtpy import QtWidgets


class SmartSlider(QtWidgets.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._n = int((max_value - min_value) / step) + 1
        self._arr = np.linspace(min_value, max_value, self._n)

        self.default_value = default_value

        self.setRange(1, self._n)
        self.setSingleStep(1)
        self.setValue(self.default_index)

        self._index = self.default_index

    @property
    def default_index(self):
        try:
            return self.index_from_value(self.default_value)
        except (TypeError, ValueError):
            return 1

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
        return self._arr.searchsorted(value, side='right')

    def reset(self):
        self.index = self.default_index
