from qtpy import QtGui, QtCore, QtWidgets

import logging
import pathlib

from ..config import config
from ..io.inspection_data import InspectionData
from ..utils.widgets import AbstractWidget

logger = logging.getLogger(__name__)


class ToolBar(QtWidgets.QToolBar, AbstractWidget):
    navigation_button_clicked = QtCore.Signal(str, bool)
    star_button_clicked = QtCore.Signal()
    reset_view_button_clicked = QtCore.Signal()
    reset_layout_button_clicked = QtCore.Signal()
    screenshot_button_clicked = QtCore.Signal()
    settings_button_clicked = QtCore.Signal()

    NAVIGATION_BUTTON_PARAMS = {'previous': {'shortcut': QtGui.QKeySequence.MoveToPreviousChar,
                                             'icon': 'arrow-backward'},
                                'next': {'shortcut': QtGui.QKeySequence.MoveToNextChar,
                                         'icon': 'arrow-forward'},
                                'previous starred': {'icon': 'arrow-backward-starred'},
                                'next starred': {'icon': 'arrow-forward-starred'}
                                }

    def __init__(self, appearance: config.Appearance, parent=None):
        self.appearance = appearance

        self._navigation_buttons: dict[str, QtWidgets.QAction] | None = None
        self._star_button: QtWidgets.QAction | None = None
        self._reset_view_button: QtWidgets.QAction | None = None
        self._reset_layout_button: QtWidgets.QAction | None = None
        self._screenshot_button: QtWidgets.QAction | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._settings_button: QtWidgets.QAction | None = None

        super().__init__(parent=parent)
        self.setWindowTitle('Commands Bar')

    @property
    def _viewer_connected_buttons(self):
        return tuple(self._navigation_buttons.values()) + (self._star_button, self._screenshot_button,
                                                           self._reset_view_button, self._reset_layout_button)

    def _create_navigation_buttons(self) -> dict[str, QtWidgets.QAction]:
        navig_buttons = {}
        for button_name, button_properties in self.NAVIGATION_BUTTON_PARAMS.items():
            button = QtWidgets.QAction('Go to the {} object'.format(button_name), self)

            if button_properties.get('shortcut'):
                button.setShortcut(button_properties['shortcut'])

            navig_buttons[button_name] = button

        return navig_buttons

    @staticmethod
    def _get_star_icon_name(starred=False):
        icon_name = 'star.svg' if starred else 'star-empty.svg'
        return icon_name

    def _get_icon(self, icon_name):
        icon_root_dir = pathlib.Path(__file__).parent.parent / 'data' / 'icons'
        icon_path = icon_root_dir / self.appearance.theme / icon_name
        if not icon_path.exists():
            icon_path = icon_root_dir / 'light' / icon_name

        return QtGui.QIcon(str(icon_path))

    def _set_icons(self):
        for button_name, button in self._navigation_buttons.items():
            button.setIcon(self._get_icon(self.NAVIGATION_BUTTON_PARAMS[button_name]['icon'] + '.svg'))

        self._star_button.setIcon(self._get_icon(self._get_star_icon_name()))
        self._screenshot_button.setIcon(self._get_icon('screenshot.svg'))
        self._reset_view_button.setIcon(self._get_icon('reset-view.svg'))
        self._reset_layout_button.setIcon(self._get_icon('reset-dock-state.svg'))
        self._settings_button.setIcon(self._get_icon('gear.svg'))

    def init_ui(self):
        # create buttons for switching to the next or previous object
        self._navigation_buttons = self._create_navigation_buttons()

        # create a `star` button
        self._star_button = QtWidgets.QAction(self)
        self._star_button.setShortcut('S')
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

        for b in self._viewer_connected_buttons:
            b.setEnabled(False)

        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self._settings_button = QtWidgets.QAction(self)
        self._settings_button.setToolTip('GUI and Project Settings')

        self._set_icons()

        # connect button signals to slots
        for button_name, button in self._navigation_buttons.items():
            button.triggered.connect(lambda s, command=button_name.split(' ')[0], find_starred='starred' in button_name:
                                     self.navigation_button_clicked.emit(command, find_starred))

        self._star_button.triggered.connect(self.star_button_clicked.emit)
        self._reset_view_button.triggered.connect(self.reset_view_button_clicked.emit)
        self._reset_layout_button.triggered.connect(self.reset_layout_button_clicked.emit)
        self._screenshot_button.triggered.connect(self.screenshot_button_clicked.emit)
        self._settings_button.triggered.connect(self.settings_button_clicked)

    def set_layout(self):
        pass

    def populate(self):
        self.addAction(self._navigation_buttons['previous starred'])
        self.addAction(self._navigation_buttons['previous'])
        self.addAction(self._navigation_buttons['next'])
        self.addAction(self._navigation_buttons['next starred'])

        self.addSeparator()

        self.addAction(self._star_button)

        self.addSeparator()

        self.addAction(self._reset_view_button)
        self.addAction(self._reset_layout_button)
        self.addAction(self._screenshot_button)

        self.addWidget(self._spacer)

        self.addAction(self._settings_button)

    @QtCore.Slot(InspectionData)
    def load_project(self, review: InspectionData):
        for b in self._viewer_connected_buttons:
            b.setEnabled(True)

        self._navigation_buttons['previous starred'].setEnabled(review.has_data('starred'))
        self._navigation_buttons['next starred'].setEnabled(review.has_data('starred'))

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        self._star_button.setIcon(self._get_icon(self._get_star_icon_name(review.get_value(j, 'starred'))))

    @QtCore.Slot(bool, bool)
    def update_star_button_icon(self, starred: bool, has_starred: bool):
        self._star_button.setIcon(self._get_icon(self._get_star_icon_name(starred)))

        self._navigation_buttons['previous starred'].setEnabled(has_starred)
        self._navigation_buttons['next starred'].setEnabled(has_starred)
