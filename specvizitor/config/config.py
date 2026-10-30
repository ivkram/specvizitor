from dataclasses import dataclass, field
from typing import Any

from ..utils.params import Params


@dataclass
class Catalog:
    filename: str | None = None
    translate: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Image:
    filename: str | None = None
    wcs_source: str | None = None
    loader: str = 'auto'
    loader_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSources:
    dir: str | None = None
    images: dict[str, Image] = field(default_factory=dict)
    id_pattern: str = r'\d+'
    enabled_unit_aliases: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Appearance:
    theme: str = 'dark'
    antialiasing: bool = False
    viewer_spacing: int = 3
    viewer_margins: int = 3


@dataclass
class InspectionResults:
    default_flags: list[str] = field(default_factory=list)


@dataclass
class DataViewer:
    default_screenshot_location: str | None = None
    redshift_step: float = 0.01
    redshift_small_step: float = 0.0005


@dataclass
class Config(Params):
    # user preferences, shared by all workspaces (workspace settings are in WorkspaceConfig)
    appearance: Appearance = field(default_factory=Appearance)
    data_viewer: DataViewer = field(default_factory=DataViewer)
