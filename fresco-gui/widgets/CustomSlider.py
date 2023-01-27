import numpy as np
from pyqtgraph.Qt import QtGui


class CustomSlider(QtGui.QSlider):
    def __init__(self, *args, min_value=0, max_value=1, step=1, default_value=0, **kwargs):
        super().__init__(*args, **kwargs)

        self.min = min_value
        self.max = max_value
        self.step = step
        self.default = default_value

        self.setRange(0, self.n)
        self.setSingleStep(1)

        self.index = default_value

    @property
    def n(self):
        return int((self.max - self.min) / self.step)

    @property
    def arr(self):
        return np.linspace(self.min, self.max, self.n + 1)

    @property
    def value(self):
        return self.arr[self.index]
