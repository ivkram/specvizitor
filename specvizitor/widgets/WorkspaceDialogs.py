from qtpy import QtCore, QtWidgets

import logging
import pathlib

from ..config import WORKSPACES_DIR
from ..config.workspace import Workspace, WorkspaceRegistry
from ..io.workspace_archive import (ARCHIVE_EXTENSION, ARCHIVE_FILTER, ExportOptions, archive_workspace_name,
                                    export_workspace, import_workspace, unset_paths)
from ..utils.logs import qlog
from ..utils.paths import absolute_path
from ..utils.widgets import FileBrowser, cat_browser, data_browser

logger = logging.getLogger(__name__)

__all__ = [
    "NewWorkspaceDialog",
    "CloneWorkspaceDialog",
    "RenameWorkspaceDialog",
    "OpenWorkspaceDialog",
    "ForgetWorkspaceDialog",
    "ImportWorkspaceDialog",
    "ExportWorkspaceDialog",
    "ResolvePathsDialog"
]


def _safe_directory_name(name: str) -> str:
    return ''.join(c if (c.isalnum() or c in '-_. ') else '_' for c in name).strip().replace(' ', '_')


def _button_box(dialog: QtWidgets.QDialog) -> QtWidgets.QDialogButtonBox:
    box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, dialog)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


class NewWorkspaceDialog(QtWidgets.QDialog):
    workspace_created = QtCore.Signal(str)

    def __init__(self, registry: WorkspaceRegistry, default_name: str = 'Untitled',
                 default_location=WORKSPACES_DIR, parent=None):
        self._registry = registry
        self._default_name = default_name
        self._default_location = default_location

        self._name_edit: QtWidgets.QLineEdit | None = None
        self._location: FileBrowser | None = None
        self._info_label: QtWidgets.QLabel | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
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

    @property
    def _name(self) -> str:
        return self._name_edit.text().strip()

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
        if not self._registry.validate_name(self._name):
            return False

        target = self._target_path()
        if target is None:
            logger.error("Invalid workspace name or location")
            return False

        if target.exists():
            logger.error(f"A directory of that name already exists (path: {target})")
            return False

        return True

    @qlog
    def create_workspace(self) -> Workspace | None:
        return Workspace.create(self._target_path(), name=self._name)

    def accept(self):
        if not self.validate():
            return

        workspace = self.create_workspace()
        if workspace is None:
            return

        super().accept()
        self.workspace_created.emit(str(workspace.path))


class CloneWorkspaceDialog(NewWorkspaceDialog):
    def __init__(self, registry: WorkspaceRegistry, source: Workspace, parent=None):
        self._source = source

        super().__init__(registry,
                         default_name=registry.unique_name(source.name),
                         default_location=source.path.parent,
                         parent=parent)
        self.setWindowTitle("Clone Workspace")

    @qlog
    def create_workspace(self) -> Workspace | None:
        return self._source.copy(self._target_path(), name=self._name)


class RenameWorkspaceDialog(QtWidgets.QDialog):
    workspace_renamed = QtCore.Signal(str)

    def __init__(self, registry: WorkspaceRegistry, workspace: Workspace, parent=None):
        self._registry = registry
        self._workspace = workspace

        self._name_edit: QtWidgets.QLineEdit | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Rename Workspace")

        self.init_ui()
        self.set_layout()
        self.populate()

    @property
    def _default_name(self) -> str:
        return self._workspace.name

    def init_ui(self):
        self._name_edit = QtWidgets.QLineEdit(self._default_name, self)
        self._name_edit.selectAll()

        self._button_box = _button_box(self)

    def set_layout(self):
        self.setLayout(QtWidgets.QFormLayout())

    def populate(self):
        self.layout().addRow("Name:", self._name_edit)
        self.layout().addRow(self._button_box)

    @property
    def _name(self) -> str:
        return self._name_edit.text().strip()

    @qlog
    def validate(self) -> bool:
        return self._registry.validate_name(self._name, path=self._workspace.path)

    def accept(self):
        if not self.validate():
            return

        name = self._name
        renamed = name != self._workspace.name
        if renamed:
            self._workspace.rename(name)

        super().accept()
        if renamed:
            self.workspace_renamed.emit(name)


class OpenWorkspaceDialog(RenameWorkspaceDialog):
    """ Asks for another name for a workspace being opened, when its own is already taken by a known workspace.
    """
    def __init__(self, registry: WorkspaceRegistry, workspace: Workspace, parent=None):
        self._info_label: QtWidgets.QLabel | None = None

        super().__init__(registry, workspace, parent=parent)
        self.setWindowTitle("Open Workspace")

    @property
    def _default_name(self) -> str:
        return self._registry.unique_name(self._workspace.name)

    def init_ui(self):
        super().init_ui()

        self._info_label = QtWidgets.QLabel(
            f"Another workspace is already called `{self._workspace.name}`. Choose a different name for this one.",
            self)
        self._info_label.setWordWrap(True)

    def populate(self):
        self.layout().addRow(self._info_label)
        super().populate()


class ForgetWorkspaceDialog(QtWidgets.QDialog):
    def __init__(self, path: str, parent=None):
        self._path = path

        self._info_label: QtWidgets.QLabel | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Workspace Unavailable")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._info_label = QtWidgets.QLabel(
            f"`{Workspace.name_at(self._path)}` is not there any more:\n\n{self._path}\n\n"
            f"Forget this workspace? Keep it if it lives on storage that is only temporarily unavailable.", self)
        self._info_label.setWordWrap(True)

        self._button_box = _button_box(self)
        self._button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Forget Workspace")
        self._button_box.button(QtWidgets.QDialogButtonBox.Cancel).setDefault(True)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        self.layout().addWidget(self._info_label)
        self.layout().addWidget(self._button_box)


class ImportWorkspaceDialog(NewWorkspaceDialog):
    def __init__(self, registry: WorkspaceRegistry, archive, contents: list[str], parent=None):
        self._archive = pathlib.Path(archive)
        self._contents = contents

        self._archive_label: QtWidgets.QLabel | None = None
        self._contents_label: QtWidgets.QLabel | None = None

        name = archive_workspace_name(archive) or self._archive.stem
        super().__init__(registry, default_name=registry.unique_name(name), parent=parent)
        self.setWindowTitle("Import Workspace")

    def init_ui(self):
        super().init_ui()

        self._archive_label = QtWidgets.QLabel(self._archive.name, self)
        self._archive_label.setToolTip(str(self._archive))

        self._contents_label = QtWidgets.QLabel(", ".join(sorted(self._contents)), self)
        self._contents_label.setWordWrap(True)

    def populate(self):
        self.layout().addRow("Archive:", self._archive_label)
        self.layout().addRow("Contains:", self._contents_label)
        super().populate()

    @qlog
    def create_workspace(self) -> Workspace | None:
        workspace = import_workspace(self._archive, self._target_path())
        if workspace is None:
            return None

        workspace.rename(self._name)
        if unset_paths(workspace.config):
            ResolvePathsDialog(workspace, parent=self).exec()
        return workspace


class ExportWorkspaceDialog(QtWidgets.QDialog):
    def __init__(self, workspace: Workspace, parent=None):
        self._workspace = workspace

        self._checkboxes: dict[str, QtWidgets.QCheckBox] = {}
        self._destination: FileBrowser | None = None
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Export Workspace")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        results = self._workspace.state.last_inspection_file
        has_results = bool(results) and pathlib.Path(results).is_file()

        labels = {
            'include_widgets': "Data viewer configuration",
            'include_layout': "Window layout",
            'include_results': f"Inspection results ({pathlib.Path(results).name})" if has_results
                               else "Inspection results",
            'include_local_paths': "This machine's data paths (only for a shared filesystem)",
        }
        defaults = ExportOptions()
        for attr, label in labels.items():
            self._checkboxes[attr] = QtWidgets.QCheckBox(label, self)
            self._checkboxes[attr].setChecked(getattr(defaults, attr))
        self._checkboxes['include_results'].setEnabled(has_results)

        default_path = pathlib.Path.home() / f"{self._workspace.path.name}{ARCHIVE_EXTENSION}"
        self._destination = FileBrowser(mode=FileBrowser.SaveFile, filename_extensions=ARCHIVE_FILTER,
                                        default_path=default_path, title="Export to", parent=self)

        self._button_box = _button_box(self)

    def set_layout(self):
        self.setLayout(QtWidgets.QVBoxLayout())

    def populate(self):
        for box in self._checkboxes.values():
            self.layout().addWidget(box)
        self.layout().addWidget(self._destination)
        self.layout().addWidget(self._button_box)

    def _destination_path(self) -> pathlib.Path:
        return absolute_path(self._destination.path).with_suffix(ARCHIVE_EXTENSION)

    @qlog
    def validate(self) -> bool:
        if not self._destination.validate(verbose=True):
            return False

        # FileBrowser has checked the path without the extension
        dest = self._destination_path()
        if dest.exists():
            logger.error(f"File `{dest}` already exists")
            return False

        return True

    @qlog
    def export(self) -> bool:
        options = ExportOptions(**{attr: box.isChecked() for attr, box in self._checkboxes.items()})
        return export_workspace(self._workspace, self._destination_path(), options)

    def accept(self):
        if not self.validate() or not self.export():
            return

        super().accept()


class ResolvePathsDialog(QtWidgets.QDialog):
    def __init__(self, workspace: Workspace, parent=None):
        self._workspace = workspace

        self._info_label: QtWidgets.QLabel | None = None
        self._rows: list[tuple[str, object, str, FileBrowser]] = []
        self._button_box: QtWidgets.QDialogButtonBox | None = None

        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Locate Workspace Data")

        self.init_ui()
        self.set_layout()
        self.populate()

    def init_ui(self):
        self._info_label = QtWidgets.QLabel(
            f"Set the paths to the data of <b>{self._workspace.name}</b> on this machine, "
            f"or leave them for later in the settings.", self)
        self._info_label.setWordWrap(True)

        cfg = self._workspace.config
        for title, obj, attr in unset_paths(cfg):
            if obj is cfg.data:
                browser = data_browser(None, parent=self)
            elif obj is cfg.catalog:
                browser = cat_browser(None, parent=self)
            else:
                browser = FileBrowser(parent=self)
            self._rows.append((title, obj, attr, browser))

        self._button_box = _button_box(self)
        self._button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText("Skip")

    def set_layout(self):
        self.setLayout(QtWidgets.QFormLayout())

    def populate(self):
        self.layout().addRow(self._info_label)
        for title, _, _, browser in self._rows:
            self.layout().addRow(f"{title}:", browser)
        self.layout().addRow(self._button_box)

    @qlog
    def validate(self) -> bool:
        # an empty field can be set later in the settings
        return all(browser.validate(verbose=True) for *_, browser in self._rows if browser.is_filled())

    def accept(self):
        if not self.validate():
            return

        for _, obj, attr, browser in self._rows:
            setattr(obj, attr, browser.path or None)
        self._workspace.config.save()
        super().accept()
