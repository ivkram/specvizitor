import numpy as np
import qtpy
from qtpy import QtGui, QtCore, QtWidgets

from functools import partial
import logging
import pathlib

from ..appdata import AppData
from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class ControlBar(QtWidgets.QToolBar, AbstractWidget):
    reset_view_button_clicked = QtCore.Signal()
    reset_dock_state_button_clicked = QtCore.Signal()
    screenshot_button_clicked = QtCore.Signal(str)
    object_selected = QtCore.Signal(int)

    def __init__(self, rd: AppData, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Control Panel')

        self.rd = rd

        # create buttons for switching to the next or previous object
        self._pn_buttons = self.create_pn_buttons()

        # create the `starred` button
        self._star_button = QtWidgets.QAction(parent=self)
        self._star_button.setIcon(self.get_icon(self.get_star_icon_name()))
        self._star_button.setToolTip('Star the object')
        self._star_button.triggered.connect(self.star)

        # create the `screenshot` button
        self._screenshot_button = QtWidgets.QAction(parent=self)
        self._screenshot_button.setIcon(self.get_icon('screenshot.svg'))
        self._screenshot_button.setToolTip('Take a screenshot')
        self._screenshot_button.triggered.connect(self.screenshot)

        # create the `reset view` button
        self._reset_view_button = QtWidgets.QAction(parent=self)
        self._reset_view_button.setIcon(self.get_icon('reset-view.svg'))
        self._reset_view_button.setToolTip('Reset the view')
        self._reset_view_button.triggered.connect(self.reset_view_button_clicked.emit)

        # create a `dark mode` button
        # self._dark_mode = QtWidgets.QPushButton(parent=self)
        # self._dark_mode.setIcon(self.create_icon(get_icon_abs_path('dark-mode.svg')))
        # self._dark_mode.setToolTip('Turn on the dark theme')

        # create the `reset dock state` button
        self._reset_dock_state_button = QtWidgets.QAction(parent=self)
        self._reset_dock_state_button.setIcon(self.get_icon('reset-dock-state.svg'))
        self._reset_dock_state_button.setToolTip('Reset the dock state')
        self._reset_dock_state_button.triggered.connect(self.reset_dock_state_button_clicked.emit)

    def create_pn_buttons(self) -> dict[str, QtWidgets.QAction]:
        pn_buttons_params = {'previous': {'shortcut': QtGui.QKeySequence.MoveToPreviousChar, 'icon': 'arrow-backward'},
                             'next': {'shortcut': QtGui.QKeySequence.MoveToNextChar, 'icon': 'arrow-forward'},
                             'previous starred': {'icon': 'arrow-backward-starred'},
                             'next starred': {'icon': 'arrow-forward-starred'}
                             }

        pn_buttons = {}
        for pn_text, pn_properties in pn_buttons_params.items():
            button = QtWidgets.QAction('Go to the {} object'.format(pn_text), self)
            button.setIcon(self.get_icon(pn_properties['icon'] + '.svg'))

            button.triggered.connect(partial(self.previous_next_object, pn_text.split(' ')[0], 'starred' in pn_text))
            if pn_properties.get('shortcut'):
                button.setShortcut(pn_properties['shortcut'])

            pn_buttons[pn_text] = button

        return pn_buttons

    def init_ui(self):
        self.addAction(self._pn_buttons['previous starred'])
        self.addAction(self._pn_buttons['previous'])
        self.addAction(self._pn_buttons['next'])
        self.addAction(self._pn_buttons['next starred'])

        self.addSeparator()

        self.addAction(self._screenshot_button)
        self.addAction(self._star_button)

        self.addSeparator()

        self.addAction(self._reset_view_button)
        self.addAction(self._reset_dock_state_button)

    def load_object(self):
        self._star_button.setIcon(self.get_icon(self.get_star_icon_name(self.rd.df.at[self.rd.id, 'starred'])))

        self._pn_buttons['previous starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)
        self._pn_buttons['next starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)

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

    def get_icon_abs_path(self, icon_name: str) -> pathlib.Path:
        icon_root_dir = pathlib.Path(__file__).parent.parent / 'data' / 'icons'
        icon_path = icon_root_dir / self.rd.config.appearance.theme / icon_name
        if not icon_path.exists():
            return icon_root_dir / 'light' / icon_name
        else:
            return icon_path

    @staticmethod
    def get_star_icon_name(starred=False):
        icon_name = 'star.svg' if starred else 'star-empty.svg'
        return icon_name

    def get_icon(self, icon_name):
        return QtGui.QIcon(str(self.get_icon_abs_path(icon_name)))

    def star(self):
        starred = not self.rd.df.at[self.rd.id, 'starred']

        self.rd.df.at[self.rd.id, 'starred'] = starred
        self._star_button.setIcon(self.get_icon(self.get_star_icon_name(starred)))

        self._pn_buttons['previous starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)
        self._pn_buttons['next starred'].setEnabled(np.sum(self.rd.df['starred']) > 0)

    def screenshot(self):
        default_filename = '{}_ID{}.png'.format(self.rd.output_path.stem.replace(' ', '_'), self.rd.id)
        path, extension = qtpy.compat.getsavefilename(self, caption='Save/Save As',
                                                      basedir=str(pathlib.Path().resolve() / default_filename),
                                                      filters='Images (*.png)')

        if path:
            self.screenshot_button_clicked.emit(path)
