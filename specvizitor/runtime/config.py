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
class AbstractWidget:
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
    filename_keyword: str
    loader: str | None = None
    loader_config: dict[str, str] | None = None
    position: str | None = None
    relative_to: str | None = None
    smoothing_slider: bool = True


@dataclass
class Image(ViewerElement):
    rotate: int | None = None
    scale: float | None = None
    interactive: bool = True


@dataclass
class RedshiftSlider:
    min_value: float
    max_value: float
    step: float
    default_value: float


@dataclass
class Spectrum(ViewerElement):
    redshift_slider: RedshiftSlider | None = None


@dataclass
class Viewer(AbstractWidget):
    images: dict[str, Image] | None
    spectra: dict[str, Spectrum] | None


@dataclass
class Config(Params):
    cat: Cat
    data: Data
    appearance: Appearance
    control_panel: ControlPanel
    object_info: ObjectInfo
    review_form: ReviewForm
    viewer: Viewer
    plugins: list[str]
