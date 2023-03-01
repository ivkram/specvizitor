from dataclasses import dataclass

from ..utils.params import Params, LocalFile


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
class Loader:
    cat: Cat
    data: Data


@dataclass
class GUI:
    antialiasing: bool = False


@dataclass
class Geometry:
    min_width: int | None
    min_height: int | None


@dataclass
class AbstractWidget(Geometry):
    pass


@dataclass
class ControlPanel(AbstractWidget):
    button_width: int


@dataclass
class ObjectInfo(AbstractWidget):
    items: dict[str, str] | None


@dataclass
class ReviewForm(AbstractWidget):
    checkboxes: dict[str, str] | None


@dataclass
class ViewerElement(AbstractWidget):
    filename_pattern: str
    ext_name: str | None
    ext_ver: str | None
    position: str | None
    relative_to: str | None


@dataclass
class Image(ViewerElement):
    rotate: int | None
    scale: float | None


@dataclass
class Slider:
    min_value: float | None
    max_value: float | None
    step: float | None
    default_value: float | None


@dataclass
class Spectrum(ViewerElement):
    slider: Slider


@dataclass
class Viewer(AbstractWidget):
    images: dict[str, Image] | None
    spectra: dict[str, Spectrum] | None


@dataclass
class Config(Params):
    loader: Loader
    writer: None
    gui: GUI
    control_panel: ControlPanel
    object_info: ObjectInfo
    review_form: ReviewForm
    viewer: Viewer
    plugins: list[str]
