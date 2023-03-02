import logging
import pathlib
from functools import partial

import numpy as np

import qtpy
from qtpy import QtGui, QtCore, QtWidgets

from ..runtime.appdata import AppData
from ..runtime import config
from .AbstractWidget import AbstractWidget


logger = logging.getLogger(__name__)


class ControlPanel(QtWidgets.QGroupBox, AbstractWidget):
    reset_button_clicked = QtCore.Signal()
    screenshot_button_clicked = QtCore.Signal(str)
    object_selected = QtCore.Signal(int)

    def __init__(self, rd: AppData, cfg: config.ControlPanel, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg

        self.setTitle('Control Panel')
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # create the ID button
        self._id_button = QtWidgets.QPushButton()
        self._id_button.setText('ID --')
        self._id_button.setToolTip('Reset the view')
        self._id_button.setFixedWidth(self.cfg.button_width)
        self._id_button.clicked.connect(self.reset_button_clicked.emit)

        # create a widget displaying the index of the current object and the total number of objects in the catalogue
        self._number_of_obj_label = QtWidgets.QLabel()

        # create buttons for switching to the next or previous object
        self._pn_buttons = self.create_pn_buttons()

        # create the `starred` button
        self._star_button = QtWidgets.QPushButton()
        self._star_button.setIcon(QtGui.QIcon(self.get_star_icon()))
        self._star_button.setToolTip('Star the object')
        self._star_button.clicked.connect(self.star)

        # create the `screenshot` button
        self._screenshot_button = QtWidgets.QPushButton()
        self._screenshot_button.setIcon(QtGui.QIcon(get_icon_abs_path('screenshot.svg')))
        self._screenshot_button.setToolTip('Take a screenshot')
        self._screenshot_button.clicked.connect(self.screenshot)

        # create the `reset view` button
        self._reset_view_button = QtWidgets.QPushButton()
        self._reset_view_button.setIcon(QtGui.QIcon(get_icon_abs_path('reset-view.svg')))
        self._reset_view_button.setToolTip('Reset the view')
        self._reset_view_button.clicked.connect(self.reset_button_clicked.emit)

        # create a `dark mode` button
        self._dark_mode = QtWidgets.QPushButton()
        self._dark_mode.setIcon(QtGui.QIcon(get_icon_abs_path('dark-mode.svg')))
        self._dark_mode.setToolTip('Turn on the dark theme')

        # create the `Go to ID` button
        self._go_to_id_button = QtWidgets.QPushButton()
        self._go_to_id_button.setText('Go to ID')
        self._go_to_id_button.setFixedWidth(self.cfg.button_width)
        self._go_to_id_button.clicked.connect(self.go_to_id)

        self._id_field = QtWidgets.QLineEdit()
        self._id_field.setFixedWidth(self.cfg.button_width)
        self._id_field.returnPressed.connect(self.go_to_id)

        # create the `Go to index` button
        self._go_to_index_button = QtWidgets.QPushButton()
        self._go_to_index_button.setText('Go to #')
        self._go_to_index_button.setFixedWidth(self.cfg.button_width)
        self._go_to_index_button.clicked.connect(self.go_to_index)

        self._index_field = QtWidgets.QLineEdit()
        self._index_field.setFixedWidth(self.cfg.button_width)
        self._index_field.returnPressed.connect(self.go_to_index)

    def create_pn_buttons(self) -> dict[str, QtWidgets.QPushButton]:
        pn_buttons_params = {'previous': {'shortcut': 'left', 'icon': 'arrow-backward'},
                             'next': {'shortcut': 'right', 'icon': 'arrow-forward'},
                             'previous starred': {'icon': 'arrow-backward-starred'},
                             'next starred': {'icon': 'arrow-forward-starred'}
                             }

        pn_buttons = {}
        for pn_text, pn_properties in pn_buttons_params.items():
            button = QtWidgets.QPushButton('')
            button.setToolTip('Go to the {} object'.format(pn_text))
            button.setIcon(QtGui.QIcon(get_icon_abs_path(pn_properties['icon'])))

            button.clicked.connect(partial(self.previous_next_object, pn_text.split(' ')[0], 'starred' in pn_text))

            if pn_properties.get('shortcut'):
                button.setShortcut(pn_properties['shortcut'])

            pn_buttons[pn_text] = button

        return pn_buttons

    def init_ui(self):
        self.layout.addWidget(self._id_button, 1, 1, 1, 2)
        self.layout.addWidget(self._number_of_obj_label, 1, 3, 1, 2)

        self.layout.addWidget(self._pn_buttons['previous'], 2, 1, 1, 1)
        self.layout.addWidget(self._pn_buttons['next'], 2, 2, 1, 1)
        self.layout.addWidget(self._star_button, 2, 3, 1, 1)
        self.layout.addWidget(self._dark_mode, 2, 4, 1, 1)

        self.layout.addWidget(self._pn_buttons['previous starred'], 3, 1, 1, 1)
        self.layout.addWidget(self._pn_buttons['next starred'], 3, 2, 1, 1)
        self.layout.addWidget(self._reset_view_button, 3, 3, 1, 1)
        self.layout.addWidget(self._screenshot_button, 3, 4, 1, 1)

        self.layout.addWidget(self._go_to_id_button, 4, 1, 1, 2)
        self.layout.addWidget(self._id_field, 4, 3, 1, 2)
        self.layout.addWidget(self._go_to_index_button, 5, 1, 1, 2)
        self.layout.addWidget(self._index_field, 5, 3, 1, 2)

    def load_object(self):
        self._id_button.setText('ID {}'.format(self.rd.id))
        self._number_of_obj_label.setText('(#{} / {})'.format(self.rd.j + 1, self.rd.n_objects))
        self._star_button.setIcon(QtGui.QIcon(self.get_star_icon(self.rd.df.at[self.rd.id, 'starred'])))

        self._pn_buttons['previous starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)
        self._pn_buttons['next starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)
        self._dark_mode.setEnabled(False)

    def previous_next_object(self, command: str, starred: bool):
        j_upd = self.update_index(self.rd.j, self.rd.n_objects, command)

        if starred:
            if np.sum(self.rd.df['starred']) > 0:
                while not self.rd.df.iat[j_upd, self.rd.df.columns.get_loc('starred')]:
                    j_upd = self.update_index(j_upd, self.rd.n_objects, command)
            else:
                return

        self.object_selected.emit(j_upd)

    @staticmethod
    def update_index(current_index, n_objects, command: str):
        j_upd = current_index

        if command == 'next':
            j_upd += 1
        elif command == 'previous':
            j_upd -= 1

        j_upd = j_upd % n_objects

        return j_upd

    @staticmethod
    def get_star_icon(starred=False):
        icon_name = 'star.svg' if starred else 'star-empty.svg'
        return get_icon_abs_path(icon_name)

    def star(self):
        starred = not self.rd.df.at[self.rd.id, 'starred']

        self.rd.df.at[self.rd.id, 'starred'] = starred
        self._star_button.setIcon(QtGui.QIcon(self.get_star_icon(starred)))

        self._pn_buttons['previous starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)
        self._pn_buttons['next starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)

    def screenshot(self):
        default_filename = '{}_ID{}.png'.format(self.rd.output_path.stem.replace(' ', '_'), self.rd.id)
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')

        if path:
            self.screenshot_button_clicked.emit(path)

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


def get_icon_abs_path(icon_name: str) -> str:
    return str(pathlib.Path(__file__).parent.parent / 'data' / 'icons' / icon_name)
