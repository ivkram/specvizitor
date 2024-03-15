from dataclasses import dataclass, field
from typing import Any

from ..utils.params import Params


@dataclass
class Catalogue:
    filename: str | None = None
    translate: dict[str, list[str]] | None = None


@dataclass
class Image:
    filename: str
    wcs_source: str | None = None
    loader: str = 'auto'
    loader_params: dict[str, Any] | None = None


@dataclass
class Data:
    dir: str = '.'
    images: dict[str, Image] | None = None
    id_pattern: str = r'\d+'
    enabled_unit_aliases: dict[str, str] | None = None


@dataclass
class Appearance:
    theme: str = 'light'
    antialiasing: bool = False
    viewer_spacing: int = 5
    viewer_margins: int = 5


@dataclass
class InspectionResults:
    default_flags: list[str] | None = None


@dataclass
class DataViewer:
    redshift_step: float = 0.05
    redshift_small_step: float = 0.0025


@dataclass
class Config(Params):
    appearance: Appearance = field(default_factory=Appearance)
    catalogue: Catalogue = field(default_factory=Catalogue)
    data: Data = field(default_factory=Data)
    data_viewer: DataViewer = field(default_factory=DataViewer)
    inspection_results: InspectionResults = field(default_factory=InspectionResults)
    plugins: list[str] | None = None
