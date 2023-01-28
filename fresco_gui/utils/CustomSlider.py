import numpy as np
from pyqtgraph.Qt import QtGui


class CustomSlider(QtGui.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._min = min_value
        self._max = max_value
        self._step = step

        self._n = int((self._max - self._min) / self._step)
        self._arr = np.linspace(self._min, self._max, self._n + 1)

        self.setRange(0, self._n)
        self.setSingleStep(1)

        if default_value is None:
            self.default_index = 0
        else:
            self.default_index = np.searchsorted(self._arr, default_value)

        self.index = self.default_index

    @property
    def value(self):
        return self._arr[self.index]
