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

    catalogue_name: str | None = None
    show_text_editor: bool = False
    text_editor_precision: int = 6


@dataclass
class ColorBar:
    visible: bool = True


@dataclass
class LazyViewerElement:
    visible: bool = True

    position: str | None = None
    relative_to: str | None = None


@dataclass
class SpectrumRegion(LazyViewerElement):
    window_size: str = '200 Angstrom'


@dataclass
class ViewerElement(LazyViewerElement):
    filename_keyword: str | None = None
    data_loader: str = 'auto'
    data_loader_params: dict[str, Any] | None = None
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))


@dataclass
class Image(ViewerElement):
    rotate: int = 0
    scale: float = 1
    container: str = 'ViewBox'
    color_bar: ColorBar = field(default_factory=lambda: ColorBar())


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
    limits: Limits = field(default_factory=lambda: Limits())
    label: Label = field(default_factory=lambda: Label())


@dataclass
class Plot1D(ViewerElement):
    x_axis: Axis = field(default_factory=lambda: Axis())
    y_axis: Axis = field(default_factory=lambda: Axis())


@dataclass
class Spectrum(Plot1D):
    data_loader: str = 'specutils'
    redshift_slider: Slider = field(default_factory=lambda: Slider(max_value=10, step=1e-4))
    tracked_lines: dict[str, SpectrumRegion] | None = None


@dataclass
class Docks(Params):
    spectra: dict[str, Spectrum] | None
    images: dict[str, Image] | None
    plots: dict[str, Plot1D] | None
