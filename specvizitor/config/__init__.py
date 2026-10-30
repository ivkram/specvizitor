from platformdirs import user_config_dir, user_cache_dir

import pathlib

from .. import APPLICATION

from .config import Config
from .data_widgets import DataWidgets
from .spectral_lines import SpectralLineData
from .workspace import Workspace, WorkspaceConfig, WorkspaceLayout, WorkspaceRegistry, WorkspaceState


__all__ = [
    "Config",
    "DataWidgets",
    "SpectralLineData",
    "Workspace",
    "WorkspaceConfig",
    "WorkspaceLayout",
    "WorkspaceRegistry",
    "WorkspaceState",
    "CONFIG_DIR",
    "CACHE_DIR",
    "WORKSPACES_DIR",
    "REGISTRY_FILENAME"
]


application_lower = APPLICATION.lower()

CONFIG_DIR = user_config_dir(application_lower)
CACHE_DIR = user_cache_dir(application_lower)

# the default location for new workspaces
WORKSPACES_DIR = str(pathlib.Path(CONFIG_DIR) / 'workspaces')

REGISTRY_FILENAME = 'workspaces.yml'

del application_lower
