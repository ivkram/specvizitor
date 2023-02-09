import logging
from functools import partial

from pyqtgraph.Qt import QtCore, QtWidgets


from ..utils.params import save_cache


logger = logging.getLogger(__name__)


class ControlPanel(QtWidgets.QGroupBox):
    reset_button_clicked = QtCore.pyqtSignal()
    object_selected = QtCore.pyqtSignal(int)

    def __init__(self, config, cache, parent=None):
        self._config = config
        self._cache = cache

        self._j = None
        self._cat = None

        super().__init__(parent)
        self.setTitle('Control Panel')
        self.setMaximumWidth(self._config['max_width'])
        self.setEnabled(False)

        grid = QtWidgets.QGridLayout()

        # add a reset button
        self._reset_button = QtWidgets.QPushButton()
        self._reset_button.setText('ID --')
        self._reset_button.setToolTip('Reset view')
        self._reset_button.setFixedWidth(self._config['button_width'])
        self._reset_button.clicked.connect(self.reset_button_clicked.emit)
        grid.addWidget(self._reset_button, 1, 1, 1, 1)

        # add a widget displaying the index of the current object and the total number of objects in the catalogue
        self._number_of_obj_label = QtWidgets.QLabel()
        grid.addWidget(self._number_of_obj_label, 1, 2, 1, 1)

        # set buttons for next or previous object
        pn_buttons_params = {'previous': {'shortcut': 'left', 'layout': (2, 1, 1, 1)},
                             'next': {'shortcut': 'right', 'layout': (2, 2, 1, 1)}}
        for pn_text, pn_properties in pn_buttons_params.items():
            b = QtWidgets.QPushButton('')
            # b.setIcon(QtGui.QIcon(pn_text + '.png'))
            b.setToolTip('Look at the {} object.'.format(pn_text))
            b.setText(pn_text)
            b.setFixedWidth(self._config['button_width'])
            b.clicked.connect(partial(self.previous_next_object, pn_text))
            b.setShortcut(pn_properties['shortcut'])
            grid.addWidget(b, *pn_properties['layout'])

        # add a `Go to ID` button
        self._go_to_id_button = QtWidgets.QPushButton()
        self._go_to_id_button.setText('Go to ID')
        self._go_to_id_button.setFixedWidth(self._config['button_width'])
        self._go_to_id_button.clicked.connect(self.go_to_id)
        grid.addWidget(self._go_to_id_button, 3, 1, 1, 1)

        self._id_field = QtWidgets.QLineEdit()
        self._id_field.setFixedWidth(self._config['button_width'])
        self._id_field.returnPressed.connect(self.go_to_id)
        grid.addWidget(self._id_field, 3, 2, 1, 1)

        # add a `Go to index` button
        self._go_to_index_button = QtWidgets.QPushButton()
        self._go_to_index_button.setText('Go to #')
        self._go_to_index_button.setFixedWidth(self._config['button_width'])
        self._go_to_index_button.clicked.connect(self.go_to_index)
        grid.addWidget(self._go_to_index_button, 4, 1, 1, 1)

        self._index_field = QtWidgets.QLineEdit()
        self._index_field.setFixedWidth(self._config['button_width'])
        self._index_field.returnPressed.connect(self.go_to_index)
        grid.addWidget(self._index_field, 4, 2, 1, 1)

        self.setLayout(grid)

    def load_object(self, j):
        self._cache['last_object_index'] = j
        save_cache(self._cache)

        self._j = j

        self._reset_button.setText('ID {}'.format(self._cat['id'][self._j]))
        self._number_of_obj_label.setText('(#{} / {})'.format(self._j + 1, len(self._cat)))

    def previous_next_object(self, command: str):
        j_upd = self._j

        if command == 'next':
            j_upd += 1
        elif command == 'previous':
            j_upd -= 1

        j_upd = j_upd % len(self._cat)

        self.object_selected.emit(j_upd)

    def go_to_id(self):
        text = self._id_field.text()
        self._id_field.clear()

        try:
            id_upd = int(text)
        except ValueError:
            logger.error('Invalid ID')
            return

        if id_upd in self._cat['id']:
            self.object_selected.emit(self._cat.loc[id_upd].index)
        else:
            logger.error('ID not found')
            return

    def go_to_index(self):
        text = self._index_field.text()
        self._index_field.clear()

        try:
            index_upd = int(text)
        except ValueError:
            logger.error('Invalid index')
            return

        if 0 < index_upd <= len(self._cat):
            self.object_selected.emit(index_upd - 1)
        else:
            logger.error('Index out of range')
            return

    def load_project(self, cat):
        self._cat = cat
        self._cat.add_index('id')
        self.setEnabled(True)
