from dataclasses import dataclass

from ..utils.params import Params


@dataclass
class Cat:
    filename: str | None
    translate: dict[str, list[str]] | None


@dataclass
class Data:
    dir: str
    id_pattern: str
    translate: dict[str, list[str]] | None


@dataclass
class Appearance:
    antialiasing: bool = False


@dataclass
class ControlPanel:
    button_width: int


@dataclass
class ObjectInfo:
    items: dict[str, str] | None


@dataclass
class ReviewForm:
    checkboxes: dict[str, str] | None


@dataclass
class ViewerGeometry:
    spacing: int
    margins: int


@dataclass
class Config(Params):
    cat: Cat
    data: Data
    appearance: Appearance
    control_panel: ControlPanel
    object_info: ObjectInfo
    review_form: ReviewForm
    viewer_geometry: ViewerGeometry
    plugins: list[str]
