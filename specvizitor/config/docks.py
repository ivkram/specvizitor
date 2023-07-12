from dataclasses import dataclass, field
from typing import Any

from ..utils.params import Params


@dataclass
class Slider:
    visible: bool = True

    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default_value: float = 0

    name_in_catalogue: str | None = None
    show_text_editor: bool = False
    n_decimal_places: int = 6


@dataclass
class ColorBar:
    visible: bool = True


@dataclass
class Limits:
    min: float | None = None
    max: float | None = None


@dataclass
class Label:
    position: str | None = None


@dataclass
class Axis:
    name: str | None = None
    unit: str | None = None
    scale: str = 'linear'
    limits: Limits = field(default_factory=Limits)
    label: Label = field(default_factory=Label)


@dataclass
class LazyViewerElement:
    visible: bool = True

    position: str | None = None
    relative_to: str | None = None


@dataclass
class DataElement:
    filename_keyword: str | None = None
    loader: str = 'auto'
    loader_params: dict[str, Any] | None = None


@dataclass
class ViewerElement(LazyViewerElement):
    data: DataElement = field(default_factory=DataElement)
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))


@dataclass
class Image(ViewerElement):
    rotate: int = 0
    scale: float = 1
    container: str = 'ViewBox'
    color_bar: ColorBar = field(default_factory=ColorBar)


@dataclass
class Plot1D(ViewerElement):
    x_axis: Axis = field(default_factory=Axis)
    y_axis: Axis = field(default_factory=Axis)


@dataclass
class SpectrumRegion(LazyViewerElement):
    window_size: str = '300 Angstrom'


@dataclass
class Spectrum(Plot1D):
    data: DataElement = field(default_factory=lambda: DataElement(loader='specutils'))
    redshift_slider: Slider = field(default_factory=lambda: Slider(max_value=10, step=1e-4))
    tracked_lines: dict[str, SpectrumRegion] | None = None


@dataclass
class Docks(Params):
    images: dict[str, Image] | None
    plots: dict[str, Plot1D] | None
    spectra: dict[str, Spectrum] | None
