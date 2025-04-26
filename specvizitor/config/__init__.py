from platformdirs import user_config_dir, user_cache_dir

from .. import APPLICATION

from .cache import Cache
from .config import Config
from .data_widgets import DataWidgets
from .spectral_lines import SpectralLineData


__all__ = [
    "Cache",
    "Config",
    "DataWidgets",
    "SpectralLineData",
    "CONFIG_DIR",
    "CACHE_DIR"
]


application_lower = APPLICATION.lower()

CONFIG_DIR = user_config_dir(application_lower)
CACHE_DIR = user_cache_dir(application_lower)

del application_lower
