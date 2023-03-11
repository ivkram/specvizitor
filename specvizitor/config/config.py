from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class Cat:
    filename: str | None = None
    translate: dict[str, list[str]] | None = None


@dataclass
class Data:
    dir: str = '.'
    id_pattern: str = r'\d+'
    translate: dict[str, list[str]] | None = None


@dataclass
class Appearance:
    antialiasing: bool = False


@dataclass
class ControlPanel:
    button_width: int = 130


@dataclass
class ObjectInfo:
    items: dict[str, str] | None = field(default_factory=lambda: {'ra': 'RA: {}', 'dec': 'Dec: {}'})


@dataclass
class ReviewForm:
    checkboxes: dict[str, str] | None = None


@dataclass
class DataViewer:
    spacing: int = 5
    margins: int = 5
    label_style: dict[str, str] = field(default_factory=lambda: {'font-size': '20px'})


@dataclass
class Config(Params):
    cat: Cat
    data: Data
    appearance: Appearance = field(default_factory=lambda: Appearance())
    control_panel: ControlPanel = field(default_factory=lambda: ControlPanel())
    object_info: ObjectInfo = field(default_factory=lambda: ObjectInfo())
    review_form: ReviewForm = field(default_factory=lambda: ReviewForm())
    data_viewer: DataViewer = field(default_factory=lambda: DataViewer())
    plugins: list[str] = field(default_factory=list)
