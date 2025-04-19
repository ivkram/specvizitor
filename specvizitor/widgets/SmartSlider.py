import numpy as np
from qtpy import QtWidgets, QtCore

import logging

from ..io.catalog import Catalog
from ..utils.widgets import AbstractWidget

__all__ = [
    'SmartSlider'
]

logger = logging.getLogger(__name__)


class SmartSliderBase(QtWidgets.QSlider):
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
    def index(self, i: int):
        self._index = i
        self.setValue(i)

    @property
    def value(self):
        return self._arr[self.index - 1]

    def index_from_value(self, value: float):
        i = self._arr.searchsorted(value, side='right')
        return i if i > 0 else 1

    def reset(self):
        self.index = self.default_index

    def value_changed_action(self, index: int):
        self.index = index
        self.value_changed.emit()


class SmartSlider(AbstractWidget):
    value_changed = QtCore.Signal(float)
    save_button_clicked = QtCore.Signal(float)

    def __init__(self, short_name: str = 'x', full_name: str | None = None, action: str | None = None,
                 visible: bool = True, catalog_name: str | None = None, link_to: str | None = None,
                 show_text_editor: bool = False, n_decimal_places: int = 6, show_save_button: bool = False,
                 parent=None, **kwargs):

        if catalog_name is not None:
            self.short_name = catalog_name
        else:
            self.short_name = short_name

        self.full_name = short_name if full_name is None else full_name
        self.action = f"change {self.full_name}" if action is None else action

        self.catalog_name = catalog_name
        self.link_to = link_to
        self.show_text_editor = show_text_editor
        self.n_decimal_places = n_decimal_places
        self.show_save_button = show_save_button

        self._slider_kwargs = kwargs

        self._slider: SmartSliderBase | None = None
        self._label: QtWidgets.QLabel | None = None
        self._editor: QtWidgets.QLineEdit | None = None
        self._save_button: QtWidgets.QPushButton | None = None

        super().__init__(parent=parent)
        self.setHidden(not visible)

        self._default_value_fallback = self._slider.default_value

    def init_ui(self):
        # create a slider
        orientation = QtCore.Qt.Orientation.Horizontal if self.show_text_editor else QtCore.Qt.Orientation.Vertical
        self._slider = SmartSliderBase(orientation=orientation, parent=self, **self._slider_kwargs)
        self._slider.setToolTip(f'Slide to {self.action}')

        # create a label
        self._label = QtWidgets.QLabel(f'{self.short_name} =', self)

        # create a text editor
        self._editor = QtWidgets.QLineEdit(self)
        self._editor.setMaximumWidth(120)

        # create a save button
        self._save_button = QtWidgets.QPushButton('Save!', self)

        self._label.setVisible(self.show_text_editor)
        self._editor.setVisible(self.show_text_editor)
        self._save_button.setVisible(self.show_save_button)

        self._slider.value_changed.connect(self.update_from_slider)
        self._editor.returnPressed.connect(self._update_from_editor)
        self._save_button.clicked.connect(self.save_value)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=5, margins=0)

    def populate(self):
        self.layout().addWidget(self._slider, 1, 1, 1, 1)
        self.layout().addWidget(self._label, 1, 2, 1, 1)
        self.layout().addWidget(self._editor, 1, 3, 1, 1)
        self.layout().addWidget(self._save_button, 1, 4, 1, 1)

    @property
    def value(self):
        return self._slider.value

    def set_value(self, value):
        self._slider.index = self._slider.index_from_value(value)
        self._update_editor_text()

    def _update_editor_text(self):
        self._editor.setText('{value:.{num_decimal_places}f}'.format(value=self.value,
                                                                     num_decimal_places=self.n_decimal_places))

    def update_from_slider(self):
        self._update_editor_text()
        self.value_changed.emit(self.value)

    def _update_from_editor(self):
        try:
            self._slider.index = self._slider.index_from_value(float(self._editor.text()))
        except ValueError:
            logger.error(f'Invalid {self.full_name} value: {self._editor.text()}')
            self.reset()
        else:
            # the true slider value might stay the same, which would require a manual update of the text editor
            self.update_from_slider()

    @QtCore.Slot()
    def save_value(self):
        self.save_button_clicked.emit(self.value)

    def set_default_value(self, default_value: float):
        self._slider.default_value = default_value

    def set_default_value_from_catalog(self, cat_entry: Catalog | None):
        if cat_entry is None or self.catalog_name is None:
            return

        try:
            self._slider.default_value = cat_entry.get_col(self.catalog_name)
        except KeyError as e:
            logger.warning(e)
            return

    def reset(self):
        self._slider.reset()
        self.update_from_slider()  # see comment in _update_from_editor

    def clear(self):
        self._slider.default_value = self._default_value_fallback
        self._editor.setText("")
