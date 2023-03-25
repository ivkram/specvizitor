from astropy.table import Table
import numpy as np
from qtpy import QtWidgets, QtCore

import logging

from ..utils.table_tools import column_not_found_message
from .AbstractWidget import AbstractWidget


logger = logging.getLogger(__name__)


class SmartSlider(QtWidgets.QSlider):
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

        self.valueChanged[int].connect(self.value_changed_action)

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
        i = self._arr.searchsorted(value, side='right')
        return i if i > 0 else 1

    def reset(self):
        self.index = self.default_index

    def value_changed_action(self, index: int):
        self.index = index
        self.value_changed.emit()


class SmartSliderWithEditor(AbstractWidget):
    value_changed = QtCore.Signal(float)

    def __init__(self, parameter: str = 'x', full_name: str | None = None, action: str | None = None,
                 visible: bool = True, name_in_catalogue: str | None = None, show_text_editor: bool = False,
                 n_decimal_places: int = 6, parent=None, **kwargs):

        self.parameter = parameter if name_in_catalogue is None else name_in_catalogue
        self.full_name = parameter if full_name is None else full_name
        self.action = f"change {self.full_name}" if action is None else action

        self.name_in_catalogue = name_in_catalogue
        self.show_text_editor = show_text_editor
        self.n_decimal_places = n_decimal_places

        self._slider_kwargs = kwargs

        self._slider: SmartSlider | None = None
        self._label: QtWidgets.QLabel | None = None
        self._editor: QtWidgets.QLineEdit | None = None

        super().__init__(parent=parent)
        self.setHidden(not visible)

        self._default_value_backup = self._slider.default_value

    def init_ui(self):
        # create a slider
        if self.show_text_editor:
            orientation = QtCore.Qt.Orientation.Horizontal
        else:
            orientation = QtCore.Qt.Orientation.Vertical

        self._slider = SmartSlider(orientation=orientation, parent=self, **self._slider_kwargs)
        self._slider.setToolTip(f'Slide to {self.action}')

        # create a label
        self._label = QtWidgets.QLabel(f'{self.parameter} =', self)

        # create a text editor
        self._editor = QtWidgets.QLineEdit(self)
        self._editor.setMaximumWidth(120)

        self._label.setHidden(not self.show_text_editor)
        self._editor.setHidden(not self.show_text_editor)

        self._slider.value_changed.connect(self.update_from_slider)
        self._editor.returnPressed.connect(self._update_from_editor)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=5, margins=0)

    def populate(self):
        self.layout().addWidget(self._slider, 1, 1, 1, 1)
        self.layout().addWidget(self._label, 1, 2, 1, 1)
        self.layout().addWidget(self._editor, 1, 3, 1, 1)

    @property
    def value(self):
        return self._slider.value

    def _update_editor_text(self):
        self._editor.setText('{value:.{num_decimal_places}f}'.format(value=self.value,
                                                                     num_decimal_places=self.n_decimal_places))

    def update_from_slider(self):
        self._update_editor_text()
        self.value_changed.emit(self.value)

    def _update_from_editor(self):
        try:
            self._slider.index = self._slider.index_from_value(float(self._editor.text()))

            # the true slider value might stay the same, which would require a manual update of the text editor
            self._update_editor_text()

        except ValueError:
            logger.error(f'Invalid {self.full_name} value: {self._editor.text()}')
            self.reset()

    def update_default_value(self, cat: Table, object_id):
        try:
            self._slider.default_value = cat.loc[object_id][self.name_in_catalogue]
        except KeyError:
            logger.warning(column_not_found_message(self.name_in_catalogue, cat.meta.get('aliases')))
            self._slider.default_value = self._default_value_backup

    def reset(self):
        self._slider.reset()

        # see a comment in _update_from_editor
        self._update_editor_text()

    def clear(self):
        self._editor.setText("")
