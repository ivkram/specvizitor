import logging
from functools import partial

from qtpy import QtCore, QtWidgets

from ..runtime.appdata import AppData
from ..runtime import config
from .AbstractWidget import AbstractWidget


logger = logging.getLogger(__name__)


class ControlPanel(QtWidgets.QGroupBox, AbstractWidget):
    reset_button_clicked = QtCore.Signal()
    object_selected = QtCore.Signal(int)

    def __init__(self, rd: AppData, cfg: config.ControlPanel, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setTitle('Control Panel')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # create a reset button
        self._reset_button = QtWidgets.QPushButton()
        self._reset_button.setText('ID --')
        self._reset_button.setToolTip('Reset the view')
        self._reset_button.setFixedWidth(self.cfg.button_width)
        self._reset_button.clicked.connect(self.reset_button_clicked.emit)

        # create a widget displaying the index of the current object and the total number of objects in the catalogue
        self._number_of_obj_label = QtWidgets.QLabel()

        # create buttons for switching to the next or previous object
        self._pn_buttons = self.create_pn_buttons()

        # create a `Go to ID` button
        self._go_to_id_button = QtWidgets.QPushButton()
        self._go_to_id_button.setText('Go to ID')
        self._go_to_id_button.setFixedWidth(self.cfg.button_width)
        self._go_to_id_button.clicked.connect(self.go_to_id)

        self._id_field = QtWidgets.QLineEdit()
        self._id_field.setFixedWidth(self.cfg.button_width)
        self._id_field.returnPressed.connect(self.go_to_id)

        # create a `Go to index` button
        self._go_to_index_button = QtWidgets.QPushButton()
        self._go_to_index_button.setText('Go to #')
        self._go_to_index_button.setFixedWidth(self.cfg.button_width)
        self._go_to_index_button.clicked.connect(self.go_to_index)

        self._index_field = QtWidgets.QLineEdit()
        self._index_field.setFixedWidth(self.cfg.button_width)
        self._index_field.returnPressed.connect(self.go_to_index)

    def create_pn_buttons(self) -> dict[str, QtWidgets.QPushButton]:
        pn_buttons_params = {'previous': {'shortcut': 'left'},
                             'next': {'shortcut': 'right'}}

        pn_buttons = {}
        for pn_text, pn_properties in pn_buttons_params.items():
            button = QtWidgets.QPushButton('')
            # button.setIcon(QtGui.QIcon(pn_text + '.png'))
            button.setToolTip('Look at the {} object'.format(pn_text))
            button.setText(pn_text)
            button.setFixedWidth(self.cfg.button_width)
            button.clicked.connect(partial(self.previous_next_object, pn_text))
            button.setShortcut(pn_properties['shortcut'])

            pn_buttons[pn_text] = button

        return pn_buttons

    def init_ui(self):
        self.layout.addWidget(self._reset_button, 1, 1, 1, 1)
        self.layout.addWidget(self._number_of_obj_label, 1, 2, 1, 1)

        self.layout.addWidget(self._pn_buttons['previous'], 2, 1, 1, 1)
        self.layout.addWidget(self._pn_buttons['next'], 2, 2, 1, 1)

        self.layout.addWidget(self._go_to_id_button, 3, 1, 1, 1)
        self.layout.addWidget(self._id_field, 3, 2, 1, 1)
        self.layout.addWidget(self._go_to_index_button, 4, 1, 1, 1)
        self.layout.addWidget(self._index_field, 4, 2, 1, 1)

    def load_object(self):
        self._reset_button.setText('ID {}'.format(self.rd.id))
        self._number_of_obj_label.setText('(#{} / {})'.format(self.rd.j + 1, self.rd.n_objects))

    def previous_next_object(self, command: str):
        j_upd = self.rd.j

        if command == 'next':
            j_upd += 1
        elif command == 'previous':
            j_upd -= 1

        j_upd = j_upd % self.rd.n_objects

        self.object_selected.emit(j_upd)

    def go_to_id(self):
        text = self._id_field.text()
        self._id_field.clear()

        try:
            id_upd = int(text)
        except ValueError:
            logger.error('Invalid ID')
            return

        if id_upd in self.rd.df.index:
            self.object_selected.emit(self.rd.df.index.get_loc(id_upd))
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

        if 0 < index_upd <= self.rd.n_objects:
            self.object_selected.emit(index_upd - 1)
        else:
            logger.error('Index out of range')
            return
