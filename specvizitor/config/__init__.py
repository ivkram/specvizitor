import pathlib

from platformdirs import user_cache_dir, user_config_dir

from .. import APPLICATION
from .config import Config
from .data_widgets import DataWidgets
from .spectral_lines import SpectralLineData
from .workspace import Workspace, WorkspaceConfig, WorkspaceLayout, WorkspaceRegistry, WorkspaceState

__all__ = [
    "CACHE_DIR",
    "CONFIG_DIR",
    "DEFAULT_WORKSPACE_NAME",
    "REGISTRY_FILENAME",
    "SPECTRAL_LINES_FILENAME",
    "WORKSPACES_DIR",
    "Config",
    "DataWidgets",
    "SpectralLineData",
    "Workspace",
    "WorkspaceConfig",
    "WorkspaceLayout",
    "WorkspaceRegistry",
    "WorkspaceState"
]


application_lower = APPLICATION.lower()

CONFIG_DIR = user_config_dir(application_lower)
CACHE_DIR = user_cache_dir(application_lower)

# the default location for new workspaces
WORKSPACES_DIR = str(pathlib.Path(CONFIG_DIR) / 'workspaces')

DEFAULT_WORKSPACE_NAME = 'Default'

REGISTRY_FILENAME = 'workspaces.yml'
SPECTRAL_LINES_FILENAME = 'spectral_lines.yml'

del application_lower
