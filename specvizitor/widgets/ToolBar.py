from qtpy import QtGui, QtCore, QtWidgets

from functools import partial
import logging
import pathlib

from ..appdata import AppData
from ..config import config
from ..io.inspection_data import InspectionData
from .AbstractWidget import AbstractWidget

logger = logging.getLogger(__name__)


class ToolBar(QtWidgets.QToolBar, AbstractWidget):
    object_selected = QtCore.Signal(int)
    reset_view_button_clicked = QtCore.Signal()
    reset_layout_button_clicked = QtCore.Signal()
    screenshot_button_clicked = QtCore.Signal()
    settings_button_clicked = QtCore.Signal()

    PN_BUTTONS_PARAMS = {'previous': {'shortcut': QtGui.QKeySequence.MoveToPreviousChar, 'icon': 'arrow-backward'},
                         'next': {'shortcut': QtGui.QKeySequence.MoveToNextChar, 'icon': 'arrow-forward'},
                         'previous starred': {'icon': 'arrow-backward-starred'},
                         'next starred': {'icon': 'arrow-forward-starred'}
                         }

    def __init__(self, rd: AppData, appearance: config.Appearance, parent=None):
        self.rd = rd
        self.appearance = appearance

        self._pn_buttons: dict[str, QtWidgets.QAction] | None = None
        self._star_button: QtWidgets.QAction | None = None
        self._reset_view_button: QtWidgets.QAction | None = None
        self._reset_layout_button: QtWidgets.QAction | None = None
        self._screenshot_button: QtWidgets.QAction | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._settings_button: QtWidgets.QAction | None = None

        super().__init__(parent=parent)
        self.setWindowTitle('Commands Bar')

    @property
    def viewer_connected_buttons(self):
        return tuple(self._pn_buttons.values()) + (self._star_button, self._screenshot_button,
                                                   self._reset_view_button, self._reset_layout_button)

    def create_pn_buttons(self) -> dict[str, QtWidgets.QAction]:

        pn_buttons = {}
        for pn_text, pn_properties in self.PN_BUTTONS_PARAMS.items():
            button = QtWidgets.QAction('Go to the {} object'.format(pn_text), self)

            if pn_properties.get('shortcut'):
                button.setShortcut(pn_properties['shortcut'])

            pn_buttons[pn_text] = button

        return pn_buttons

    def set_icons(self):
        for pn_text, pn_properties in self.PN_BUTTONS_PARAMS.items():
            self._pn_buttons[pn_text].setIcon(self.get_icon(pn_properties['icon'] + '.svg'))

        self._star_button.setIcon(self.get_icon(self.get_star_icon_name()))
        self._screenshot_button.setIcon(self.get_icon('screenshot.svg'))
        self._reset_view_button.setIcon(self.get_icon('reset-view.svg'))
        self._reset_layout_button.setIcon(self.get_icon('reset-dock-state.svg'))
        self._settings_button.setIcon(self.get_icon('gear.svg'))

    def init_ui(self):
        # create buttons for switching to the next or previous object
        self._pn_buttons = self.create_pn_buttons()

        # create a `star` button
        self._star_button = QtWidgets.QAction(self)
        self._star_button.setToolTip('Star the object')

        # create a `screenshot` button
        self._screenshot_button = QtWidgets.QAction(self)
        self._screenshot_button.setToolTip('Take a screenshot')

        # create a `reset view` button
        self._reset_view_button = QtWidgets.QAction(self)
        self._reset_view_button.setToolTip('Reset the view')

        # create a `reset layout` button
        self._reset_layout_button = QtWidgets.QAction(self)
        self._reset_layout_button.setToolTip('Reset the layout')

        for b in self.viewer_connected_buttons:
            b.setEnabled(False)

        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self._settings_button = QtWidgets.QAction(self)
        self._settings_button.setToolTip('GUI and Project Settings')

        self.set_icons()

        # connect button signals to slots
        for pn_text, b in self._pn_buttons.items():
            b.triggered.connect(partial(self.previous_next_object, pn_text.split(' ')[0], 'starred' in pn_text))

        self._star_button.triggered.connect(self.star)
        self._reset_view_button.triggered.connect(self.reset_view_button_clicked.emit)
        self._reset_layout_button.triggered.connect(self.reset_layout_button_clicked.emit)
        self._screenshot_button.triggered.connect(self.screenshot_button_clicked.emit)
        self._settings_button.triggered.connect(self.settings_button_clicked)

    def set_layout(self):
        pass

    def populate(self):
        self.addAction(self._pn_buttons['previous starred'])
        self.addAction(self._pn_buttons['previous'])
        self.addAction(self._pn_buttons['next'])
        self.addAction(self._pn_buttons['next starred'])

        self.addSeparator()

        self.addAction(self._star_button)

        self.addSeparator()

        self.addAction(self._reset_view_button)
        self.addAction(self._reset_layout_button)
        self.addAction(self._screenshot_button)

        self.addWidget(self._spacer)

        self.addAction(self._settings_button)

    @QtCore.Slot()
    def load_project(self):
        for b in self.viewer_connected_buttons:
            b.setEnabled(True)

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, notes: InspectionData):
        self._star_button.setIcon(self.get_icon(self.get_star_icon_name(notes.get_value(j, 'starred'))))

        self._pn_buttons['previous starred'].setEnabled(notes.has_starred)
        self._pn_buttons['next starred'].setEnabled(notes.has_starred)

    def previous_next_object(self, command: str, starred: bool):
        j_upd = self.update_index(self.rd.j, self.rd.notes.n_objects, command)

        if starred:
            if self.rd.notes.has_starred:
                while not self.rd.notes.get_value(j_upd, 'starred'):
                    j_upd = self.update_index(j_upd, self.rd.notes.n_objects, command)
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
        icon_path = icon_root_dir / self.appearance.theme / icon_name
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
        starred = not self.rd.notes.get_value(self.rd.j, 'starred')

        self.rd.notes.update_value(self.rd.j, 'starred', starred)
        self._star_button.setIcon(self.get_icon(self.get_star_icon_name(starred)))

        self._pn_buttons['previous starred'].setEnabled(self.rd.notes.has_starred)
        self._pn_buttons['next starred'].setEnabled(self.rd.notes.has_starred)
