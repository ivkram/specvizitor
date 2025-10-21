from qtpy import QtGui, QtCore, QtWidgets

from functools import partial
import logging
import pathlib

from ..config import config
from ..io.inspection_data import InspectionData
from ..utils.widgets import AbstractWidget

from .NavigationAction import NavigationAction

logger = logging.getLogger(__name__)


class ToolBar(QtWidgets.QToolBar, AbstractWidget):
    navigation_action_triggered = QtCore.Signal(NavigationAction)
    star_action_triggered = QtCore.Signal()
    reset_view_action_triggered = QtCore.Signal()
    reset_layout_action_triggered = QtCore.Signal()
    screenshot_action_triggered = QtCore.Signal()
    settings_action_triggered = QtCore.Signal()

    def __init__(self, navigation_cfg: tuple[NavigationAction, ...], appearance: config.Appearance, parent=None):
        self._navigation_cfg = navigation_cfg
        self._appearance = appearance

        self._navigation_actions: tuple[QtWidgets.QAction, ...] | None = None
        self._star_action: QtWidgets.QAction | None = None
        self._reset_view_action: QtWidgets.QAction | None = None
        self._reset_layout_action: QtWidgets.QAction | None = None
        self._screenshot_action: QtWidgets.QAction | None = None
        self._spacer: QtWidgets.QWidget | None = None
        self._settings_action: QtWidgets.QAction | None = None

        super().__init__(parent=parent)
        self.setWindowTitle("Commands Bar")

    @property
    def _viewer_connected_actions(self):
        return self._navigation_actions + (self._star_action, self._screenshot_action, self._reset_view_action,
                                           self._reset_layout_action)

    def _create_navigation_actions(self):
        navigation_actions = []
        for action_cfg in self._navigation_cfg:
            navigation_actions.append(QtWidgets.QAction(f"Go to the {action_cfg.name.lower()} object", self))

        self._navigation_actions = tuple(navigation_actions)

    @staticmethod
    def _get_star_icon_name(starred=False):
        icon_name = "star.svg" if starred else "star-empty.svg"
        return icon_name

    def _get_icon(self, icon_name):
        icon_root_dir = pathlib.Path(__file__).parent.parent / 'data' / 'icons'
        icon_path = icon_root_dir / self._appearance.theme / icon_name
        if not icon_path.exists():
            icon_path = icon_root_dir / 'light' / icon_name

        return QtGui.QIcon(str(icon_path))

    def _set_icons(self):
        for action_cfg, action in zip(self._navigation_cfg, self._navigation_actions):
            action.setIcon(self._get_icon(f"arrow-{action_cfg.name.lower().replace(' ', '-')}.svg"))

        self._star_action.setIcon(self._get_icon(self._get_star_icon_name()))
        self._screenshot_action.setIcon(self._get_icon("screenshot.svg"))
        self._reset_view_action.setIcon(self._get_icon("reset-view.svg"))
        self._reset_layout_action.setIcon(self._get_icon("reset-dock-state.svg"))
        self._settings_action.setIcon(self._get_icon("gear.svg"))

    def init_ui(self):
        self._create_navigation_actions()

        self._star_action = QtWidgets.QAction(self)
        self._star_action.setToolTip("Star the object")

        self._screenshot_action = QtWidgets.QAction(self)
        self._screenshot_action.setToolTip("Take a screenshot")

        self._reset_view_action = QtWidgets.QAction(self)
        self._reset_view_action.setToolTip("Reset the view")

        self._reset_layout_action = QtWidgets.QAction(self)
        self._reset_layout_action.setToolTip("Reset the layout")

        for action in self._viewer_connected_actions:
            action.setEnabled(False)

        self._spacer = QtWidgets.QWidget(self)
        self._spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self._settings_action = QtWidgets.QAction(self)
        self._settings_action.setToolTip("GUI and Project Settings")

        self._set_icons()

        for action_cfg, action in zip(self._navigation_cfg, self._navigation_actions):
            action.triggered.connect(partial(self.navigation_action_triggered.emit, action_cfg))

        self._star_action.triggered.connect(self.star_action_triggered.emit)
        self._reset_view_action.triggered.connect(self.reset_view_action_triggered.emit)
        self._reset_layout_action.triggered.connect(self.reset_layout_action_triggered.emit)
        self._screenshot_action.triggered.connect(self.screenshot_action_triggered.emit)
        self._settings_action.triggered.connect(self.settings_action_triggered)

    def set_layout(self):
        pass

    def populate(self):
        for action in self._navigation_actions:
            self.addAction(action)

        self.addSeparator()

        self.addAction(self._star_action)

        self.addSeparator()

        self.addAction(self._reset_view_action)
        self.addAction(self._reset_layout_action)
        self.addAction(self._screenshot_action)

        self.addWidget(self._spacer)

        self.addAction(self._settings_action)

    @QtCore.Slot(InspectionData)
    def load_project(self, review: InspectionData):
        for a in self._viewer_connected_actions:
            a.setEnabled(True)
        self.update_navigation_actions(review.has_data("starred"))

    @QtCore.Slot(int, InspectionData)
    def load_object(self, j: int, review: InspectionData):
        pass

    @QtCore.Slot(bool)
    def star_object(self, starred: bool):
        self._star_action.setIcon(self._get_icon(self._get_star_icon_name(starred)))

    @QtCore.Slot(bool)
    def update_navigation_actions(self, has_starred: bool):
        for action_cfg, action in zip(self._navigation_cfg, self._navigation_actions):
            if action_cfg.starred_only:
                action.setEnabled(has_starred)
