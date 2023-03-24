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
    user_defined_units: dict[str, str] | None = None


@dataclass
class Appearance:
    theme: str = 'light'
    antialiasing: bool = False
    viewer_spacing: int = 5
    viewer_margins: int = 5


@dataclass
class ReviewForm:
    default_checkboxes: dict[str, str] | None = None


@dataclass
class Config(Params):
    appearance: Appearance = field(default_factory=lambda: Appearance())
    catalogue: Catalogue = field(default_factory=lambda: Catalogue())
    data: Data = field(default_factory=lambda: Data())
    review_form: ReviewForm = field(default_factory=lambda: ReviewForm())
    plugins: list[str] = field(default_factory=list)
