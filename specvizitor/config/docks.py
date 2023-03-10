from dataclasses import dataclass, field

from ..utils.params import Params


@dataclass
class Slider:
    visible: bool = True
    cat_name: str | None = None
    text_editor: bool = False
    precision: int = 6
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default_value: float = 0


@dataclass
class ColorBar:
    visible: bool = True


@dataclass
class LazyViewerElement:
    position: str | None = None
    relative_to: str | None = None


@dataclass
class ViewerElement(LazyViewerElement):
    filename_keyword: str | None = None
    loader: str | None = None
    loader_config: dict[str, str] | None = None
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))


@dataclass
class Image(ViewerElement):
    rotate: int = 0
    scale: float = 1
    container: str = 'ViewBox'
    color_bar: ColorBar = field(default_factory=lambda: ColorBar())


@dataclass
class Spectrum(ViewerElement):
    redshift_slider: Slider = field(default_factory=lambda: Slider(max_value=10, step=1e-4))
    follow: dict[str, LazyViewerElement] | None = None


@dataclass
class SpectrumRegion(LazyViewerElement):
    window: float = 20


@dataclass
class Docks(Params):
    images: dict[str, Image] | None
    spectra: dict[str, Spectrum] | None
