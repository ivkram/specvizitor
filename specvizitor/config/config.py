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
    viewer_spacing: int = 5
    viewer_margins: int = 5
    label_style: dict[str, str] = field(default_factory=lambda: {})


@dataclass
class ObjectInfo:
    show_all: bool = True
    items: list[str] | None = field(default_factory=lambda: ['ra', 'dec'])


@dataclass
class ReviewForm:
    default_checkboxes: dict[str, str] | None = None


@dataclass
class Config(Params):
    appearance: Appearance = field(default_factory=lambda: Appearance())
    catalogue: Catalogue = field(default_factory=lambda: Catalogue())
    data: Data = field(default_factory=lambda: Data())
    object_info: ObjectInfo = field(default_factory=lambda: ObjectInfo())
    review_form: ReviewForm = field(default_factory=lambda: ReviewForm())
    plugins: list[str] = field(default_factory=list)
