from qtpy import QtCore, QtWidgets

import logging
import pathlib

from ..config import WORKSPACES_DIR
from ..config.workspace import Workspace, WorkspaceRegistry
from ..utils.logs import qlog
from ..utils.paths import absolute_path
from ..utils.widgets import FileBrowser

logger = logging.getLogger(__name__)

__all__ = [
    "NewWorkspaceDialog",
    "CloneWorkspaceDialog",
    "RenameWorkspaceDialog"
]


def _safe_directory_name(name: str) -> str:
    return ''.join(c if (c.isalnum() or c in '-_. ') else '_' for c in name).strip().replace(' ', '_')


def _button_box(dialog: QtWidgets.QDialog) -> QtWidgets.QDialogButtonBox:
    box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, dialog)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


class NewWorkspaceDialog(QtWidgets.QDialog):
    def __init__(self, registry: WorkspaceRegistry, default_name: str = 'Untitled',
                 default_location=WORKSPACES_DIR, parent=None):
        self._registry = registry
        self._default_name = default_name
        self._default_location = default_location

        self._name_edit: QtWidgets.QLineEdit | None = None
        self._location: FileBrowser | None = None
        self._info_label: QtWidgets.QLabel | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        self.workspace_path: pathlib.Path | None = None
        self.workspace_name: str | None = None

        super().__init__(parent)
        self.setWindowTitle("New Workspace")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._name_edit = QtWidgets.QLineEdit(self._default_name, self)
        self._name_edit.textChanged.connect(self._update_info)

        self._location = FileBrowser(mode=FileBrowser.OpenDirectory, default_path=self._default_location,
                                     parent=self)
        self._location.textChanged.connect(self._update_info)

        self._info_label = QtWidgets.QLabel(self)
        self._info_label.setWordWrap(True)

        self._button_box = _button_box(self)

        self._update_info()

    def set_layout(self):
        self.setLayout(QtWidgets.QFormLayout())

    def populate(self):
        self.layout().addRow("Name:", self._name_edit)
        self.layout().addRow("Location:", self._location)
        self.layout().addRow(self._info_label)
        self.layout().addRow(self._button_box)

    def _target_path(self) -> pathlib.Path | None:
        name = _safe_directory_name(self._name_edit.text())
        location = self._location.path.strip()
        if not name or not location:
            return None
        return absolute_path(location) / name

    @QtCore.Slot()
    def _update_info(self):
        target = self._target_path()
        self._info_label.setText(f"Will be created in: {target}" if target else "Enter a name and a location.")

    @qlog
    def validate(self) -> bool:
        if not self._registry.validate_name(self._name_edit.text().strip()):
            return False

        target = self._target_path()
        if target is None:
            logger.error("Invalid workspace name or location")
            return False

        if target.exists():
            logger.error(f"A directory of that name already exists (path: {target})")
            return False

        return True

    def accept(self):
        if not self.validate():
            return

        self.workspace_path = self._target_path()
        self.workspace_name = self._name_edit.text().strip()
        super().accept()


class CloneWorkspaceDialog(NewWorkspaceDialog):
    def __init__(self, registry: WorkspaceRegistry, source: Workspace, parent=None):
        super().__init__(registry,
                         default_name=registry.unique_name(source.name),
                         default_location=source.path.parent,
                         parent=parent)
        self.setWindowTitle("Clone Workspace")


class RenameWorkspaceDialog(QtWidgets.QDialog):
    def __init__(self, registry: WorkspaceRegistry, workspace: Workspace, parent=None):
        self._registry = registry
        self._workspace = workspace

        self._name_edit: QtWidgets.QLineEdit | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        self.workspace_name: str | None = None

        super().__init__(parent)
        self.setWindowTitle("Rename Workspace")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._name_edit = QtWidgets.QLineEdit(self._workspace.name, self)
        self._name_edit.selectAll()

        self._button_box = _button_box(self)

    def set_layout(self):
        self.setLayout(QtWidgets.QFormLayout())

    def populate(self):
        self.layout().addRow("Name:", self._name_edit)
        self.layout().addRow(self._button_box)

    @qlog
    def validate(self) -> bool:
        name = self._name_edit.text().strip()
        return name == self._workspace.name or self._registry.validate_name(name)

    def accept(self):
        if not self.validate():
            return

        self.workspace_name = self._name_edit.text().strip()
        super().accept()
