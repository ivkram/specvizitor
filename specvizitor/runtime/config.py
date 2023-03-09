from dataclasses import dataclass, field

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
class Slider:
    visible: bool = True
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default_value: float = 0


@dataclass
class ViewerElement(AbstractWidget):
    filename_keyword: str
    loader: str | None = None
    loader_config: dict[str, str] | None = None
    position: str | None = None
    relative_to: str | None = None
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))


@dataclass
class Image(ViewerElement):
    rotate: int | None = None
    scale: float | None = None
    interactive: bool = True


@dataclass
class Spectrum(ViewerElement):
    redshift_slider: Slider = field(default_factory=lambda: Slider(max_value=10, step=1e-4))


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
