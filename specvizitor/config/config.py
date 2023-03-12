from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class Catalogue:
    filename: str | None = None
    translate: dict[str, list[str]] | None = None


@dataclass
class Data:
    dir: str = '.'
    id_pattern: str = r'\d+'
    defined_units: dict[str, str] | None = None


@dataclass
class Appearance:
    theme: str = 'light'
    antialiasing: bool = False


@dataclass
class ObjectInfo:
    show_all: bool = False
    items: list[str] | None = field(default_factory=lambda: ['ra', 'dec'])


@dataclass
class ReviewForm:
    default_checkboxes: dict[str, str] | None = None


@dataclass
class DataViewer:
    spacing: int = 5
    margins: int = 5
    label_style: dict[str, str] = field(default_factory=lambda: {'font-size': '20px'})


@dataclass
class Config(Params):
    catalogue: Catalogue = field(default_factory=lambda: Catalogue())
    data: Data = field(default_factory=lambda: Data())
    appearance: Appearance = field(default_factory=lambda: Appearance())
    object_info: ObjectInfo = field(default_factory=lambda: ObjectInfo())
    review_form: ReviewForm = field(default_factory=lambda: ReviewForm())
    data_viewer: DataViewer = field(default_factory=lambda: DataViewer())
    plugins: list[str] = field(default_factory=list)
