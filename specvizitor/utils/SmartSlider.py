import logging

import numpy as np
from astropy.table import Table
from qtpy import QtWidgets, QtCore

from .AbstractWidget import AbstractWidget
from .table_tools import column_not_found_message


logger = logging.getLogger(__name__)


class SmartSliderCore(QtWidgets.QSlider):
    value_changed = QtCore.Signal()

    def __init__(self, min_value=0, max_value=100, step=1, default_value=0,
                 orientation=QtCore.Qt.Orientation.Vertical, parent=None):

        super().__init__(orientation, parent)

        self._n = int((max_value - min_value) / step) + 1
        self._arr = np.linspace(min_value, max_value, self._n)

        self.step = step
        self.default_value = default_value

        self.setRange(1, self._n)
        self.setSingleStep(1)
        self.setValue(self.default_index)

        self._index = self.default_index

        self.valueChanged[int].connect(self.update)

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

    def update(self, index: int):
        self.index = index
        self.value_changed.emit()


class SmartSlider(AbstractWidget):
    value_changed = QtCore.Signal(float)

    def __init__(self, parameter: str = 'x', full_name: str | None = None, action: str | None = None,
                 visible: bool = True, cat_name: str | None = None, text_editor: bool = False, precision: int = 6,
                 parent=None, **kwargs):

        super().__init__(parent=parent)

        self.layout.setSpacing(5)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setHidden(not visible)

        self.parameter = parameter if cat_name is None else cat_name
        self.full_name = parameter if full_name is None else full_name
        self.action = f"change {self.full_name}" if action is None else action

        self.cat_name = cat_name
        self.text_editor = text_editor
        self.precision = precision

        # create a slider
        self._slider = SmartSliderCore(orientation=QtCore.Qt.Orientation.Horizontal if self.text_editor
                                       else QtCore.Qt.Orientation.Vertical, parent=self, **kwargs)
        self._slider.value_changed.connect(self.update_from_slider)
        self._slider.setToolTip(f'Slide to {self.action}')

        self._default_value_backup = self._slider.default_value

        # create a label
        self._label = QtWidgets.QLabel(f'{self.parameter} =', parent=self)

        # create a text editor
        self._editor = QtWidgets.QLineEdit(parent=self)
        self._editor.returnPressed.connect(self._update_from_editor)
        self._editor.setMaximumWidth(120)

        self._label.setHidden(not text_editor)
        self._editor.setHidden(not text_editor)

    def init_ui(self):
        self.layout.addWidget(self._slider, 1, 1, 1, 1)
        self.layout.addWidget(self._label, 1, 2, 1, 1)
        self.layout.addWidget(self._editor, 1, 3, 1, 1)

    @property
    def value(self):
        return self._slider.value

    def update_from_slider(self):
        self._editor.setText('{value:.{precision}f}'.format(value=self.value, precision=self.precision))
        self.value_changed.emit(self.value)

    def _update_from_editor(self):
        try:
            self._slider.index = self._slider.index_from_value(float(self._editor.text()))
            self.update_from_slider()
        except ValueError:
            logger.error(f'Invalid {self.full_name} value: {self._editor.text()}')
            self._slider.reset()

    def update_from_cat(self, cat: Table, object_id, translate):
        try:
            self._slider.default_value = cat.loc[object_id][self.cat_name]
        except KeyError:
            logger.warning(column_not_found_message(self.cat_name, translate))
            self._slider.default_value = self._default_value_backup

    def reset(self):
        self._slider.reset()
        self.update_from_slider()

    def clear(self):
        self._editor.setText("")
