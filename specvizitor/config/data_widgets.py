from dataclasses import dataclass, field
from typing import Any

from ..utils.params import Params


@dataclass
class SpectralLines:
    visible: bool = False


@dataclass
class Slider:
    visible: bool = True

    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default_value: float = 0

    name_in_catalogue: str | None = None
    link_to: str | None = None
    show_text_editor: bool = False
    n_decimal_places: int = 6


@dataclass
class ColorBar:
    visible: bool = True
    link_to: str | None = None

    vmin: float | None = None
    vmax: float | None = None


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
class DataElement:
    filename_keyword: str | None = None
    loader: str = 'auto'
    loader_params: dict[str, Any] | None = None


@dataclass
class ViewerElement:
    visible: bool = True
    position: str | None = None
    relative_to: str | None = None
    dock_title_fmt: str | None = None

    data: DataElement = field(default_factory=DataElement)

    container: str = 'PlotItem'
    link_view: dict[str, str] | None = None
    spectral_lines: SpectralLines = field(default_factory=SpectralLines)
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))
    redshift_slider: Slider = field(default_factory=lambda: Slider(visible=False, max_value=10, step=1e-6,
                                                                   show_text_editor=True))


@dataclass
class Image(ViewerElement):
    wcs_transform: bool = False
    color_bar: ColorBar = field(default_factory=ColorBar)
    central_axes: str | None = None
    central_crosshair: bool = False


@dataclass
class Plot1D(ViewerElement):
    x_axis: Axis = field(default_factory=Axis)
    y_axis: Axis = field(default_factory=Axis)


@dataclass
class SpectrumRegion(ViewerElement):
    window_size: str = '300 Angstrom'


@dataclass
class Spectrum(Plot1D):
    tracked_lines: dict[str, SpectrumRegion] | None = None


@dataclass
class DataWidgets(Params):
    images: dict[str, Image] | None
    plots: dict[str, Plot1D] | None
    spectra: dict[str, Spectrum] | None
