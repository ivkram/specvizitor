from dataclasses import dataclass, field
import logging
import pathlib
import shutil

from ..utils.params import LocalFile, Params, read_yaml
from ..utils.paths import absolute_path

from .config import Catalogue, DataSources, InspectionResults
from .data_widgets import DataWidgets

logger = logging.getLogger(__name__)

__all__ = [
    "WorkspaceConfig",
    "WorkspaceLayout",
    "WorkspaceState",
    "WorkspaceRegistry",
    "Workspace",
    "WORKSPACE_CONFIG_FILENAME",
    "WORKSPACE_LAYOUT_FILENAME",
    "WORKSPACE_STATE_FILENAME",
    "WORKSPACE_WIDGETS_FILENAME",
]

# a directory is a workspace if it contains this file
WORKSPACE_CONFIG_FILENAME = 'workspace.yml'
WORKSPACE_LAYOUT_FILENAME = 'layout.yml'
WORKSPACE_STATE_FILENAME = 'state.yml'
WORKSPACE_WIDGETS_FILENAME = 'data_widgets.yml'


@dataclass
class WorkspaceConfig(Params):
    name: str | None = None
    catalogue: Catalogue = field(default_factory=Catalogue)
    data: DataSources = field(default_factory=DataSources)
    inspection_results: InspectionResults = field(default_factory=InspectionResults)
    plugins: list[str] = field(default_factory=list)


@dataclass
class WorkspaceLayout(Params):
    dock_layout: dict | None = None


@dataclass
class WorkspaceState(Params):
    last_inspection_file: str | None = None
    last_object_index: int | None = None
    last_subset_file: str | None = None


@dataclass
class WorkspaceRegistry(Params):
    active: str | None = None
    # most recently used first
    known: list[str] = field(default_factory=list)

    MAX_KNOWN = 15

    def register(self, path) -> str:
        path = str(absolute_path(path))
        self.known = ([path] + [p for p in self.known if p != path])[:self.MAX_KNOWN]
        return path

    def forget(self, path) -> None:
        path = str(absolute_path(path))
        self.known = [p for p in self.known if p != path]
        if self.active == path:
            self.active = self.known[0] if self.known else None

    def set_active(self, path) -> str:
        path = self.register(path)
        self.active = path
        return path

    def find_by_name(self, name: str) -> str | None:
        for path in self.known:
            if Workspace.name_at(path) == name:
                return path
        return None

    # `path` is the workspace being named, which may already carry the name
    def validate_name(self, name: str, path=None) -> bool:
        if not name:
            logger.error("Workspace name is empty")
            return False

        taken = self.find_by_name(name)
        if taken is not None and (path is None or taken != str(absolute_path(path))):
            logger.error(f"Another workspace is already called `{name}` (path: {taken})")
            return False

        return True

    def unique_name(self, base: str) -> str:
        if self.find_by_name(base) is None:
            return base
        i = 2
        while self.find_by_name(f'{base} ({i})') is not None:
            i += 1
        return f'{base} ({i})'

    def resolve_active(self) -> str | None:
        # unreachable workspaces are kept in the list: a network share may only be offline
        candidates = ([self.active] if self.active else []) + list(self.known)
        for path in candidates:
            if Workspace.is_workspace(path):
                return path
        return None


@dataclass
class Workspace:
    path: pathlib.Path
    config: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    widgets: DataWidgets = field(default_factory=DataWidgets)
    layout: WorkspaceLayout = field(default_factory=WorkspaceLayout)
    state: WorkspaceState = field(default_factory=WorkspaceState)

    @property
    def name(self) -> str:
        return self.config.name or self.path.name

    @staticmethod
    def name_at(path) -> str:
        path = pathlib.Path(path)
        try:
            data = read_yaml(path / WORKSPACE_CONFIG_FILENAME)
        except Exception:
            return path.name
        if not isinstance(data, dict):
            return path.name
        return data.get('name') or path.name

    @staticmethod
    def is_workspace(path) -> bool:
        if not path:
            return False
        try:
            return (pathlib.Path(path) / WORKSPACE_CONFIG_FILENAME).is_file()
        except OSError:
            return False

    @classmethod
    def _load(cls, path: pathlib.Path) -> "Workspace | None":
        directory = str(path)
        try:
            return cls(
                path=path,
                config=WorkspaceConfig.read_user_params(
                    LocalFile(directory, WORKSPACE_CONFIG_FILENAME, 'Workspace configuration'),
                    default=WORKSPACE_CONFIG_FILENAME),
                widgets=DataWidgets.read_user_params(
                    LocalFile(directory, WORKSPACE_WIDGETS_FILENAME, 'Data viewer configuration'),
                    default=WORKSPACE_WIDGETS_FILENAME),
                layout=WorkspaceLayout.read_user_params(
                    LocalFile(directory, WORKSPACE_LAYOUT_FILENAME, 'Workspace layout', auto_backup=False)),
                state=WorkspaceState.read_user_params(
                    LocalFile(directory, WORKSPACE_STATE_FILENAME, 'Workspace state', auto_backup=False)),
            )
        except Exception as e:
            logger.error(f"Failed to open the workspace: {e} (path: {path})")
            return None

    def _named(self, name: str | None, action: str) -> "Workspace":
        if name:
            self.rename(name)
        logger.info(f"Workspace {action} (name: {self.name}, path: {self.path})")
        return self

    @classmethod
    def open(cls, path) -> "Workspace | None":
        path = absolute_path(path)
        if not cls.is_workspace(path):
            logger.error(f"Not a workspace: no {WORKSPACE_CONFIG_FILENAME} found (path: {path})")
            return None

        workspace = cls._load(path)
        return workspace._named(None, 'opened') if workspace else None

    @classmethod
    def create(cls, path, name: str | None = None) -> "Workspace | None":
        path = absolute_path(path)
        if cls.is_workspace(path):
            logger.error(f"A workspace already exists here (path: {path})")
            return None

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create the workspace directory: {e} (path: {path})")
            return None

        workspace = cls._load(path)
        return workspace._named(name, 'created') if workspace else None

    def copy(self, dest, name: str | None = None) -> "Workspace | None":
        dest = absolute_path(dest)
        if dest.exists():
            logger.error(f"A directory of that name already exists (path: {dest})")
            return None

        self.save_all()
        try:
            shutil.copytree(self.path, dest)
        except OSError as e:
            logger.error(f"Failed to copy the workspace: {e} (path: {dest})")
            return None

        workspace = self._load(dest)
        return workspace._named(name, 'copied') if workspace else None

    def rename(self, new_name: str) -> None:
        self.config.name = new_name
        self.config.save()

    def delete(self) -> bool:
        if not self.is_workspace(self.path):
            logger.error(f"Refusing to delete a directory that is not a workspace (path: {self.path})")
            return False

        try:
            shutil.rmtree(self.path)
        except OSError as e:
            logger.error(f"Failed to delete the workspace: {e} (path: {self.path})")
            return False

        logger.warning(f"Workspace deleted (path: {self.path})")
        return True

    def save_all(self) -> None:
        for params in (self.config, self.widgets, self.layout, self.state):
            params.save()
