from dataclasses import dataclass, field
from typing import Any

from ..utils.params import Params


@dataclass
class Limits:
    min: float | None = None
    max: float | None = None


@dataclass
class ColorBarLimits(Limits):
    type: str = 'minmax'


@dataclass
class Slider:
    visible: bool = True
    link_to: str | None = None

    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default_value: float = 0

    catalog_name: str | None = None
    show_text_editor: bool = False
    n_decimal_places: int = 6

    show_save_button: bool = False


@dataclass
class ColorBar:
    visible: bool = True
    link_to: str | None = None

    limits: ColorBarLimits = field(default_factory=ColorBarLimits)


@dataclass
class SpectralLines:
    visible: bool = False
    color: str | None = None


@dataclass
class LinePlot:
    x: str
    y: str
    color: str | None = None
    hide_label: bool = False


@dataclass
class Axis:
    visible: bool = True
    link_to: str | None = None

    unit: str | None = None
    scale: str = 'linear'
    label: str | None = None
    limits: Limits = field(default_factory=Limits)


@dataclass
class DataElement:
    source: str | None = None
    filename: str | None = None
    loader: str = 'auto'
    loader_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ViewerElement:
    visible: bool = True
    position: str | None = None
    relative_to: str | None = None
    dock_title_fmt: str = 'short'

    data: DataElement = field(default_factory=DataElement)

    x_axis: Axis = field(default_factory=Axis)
    y_axis: Axis = field(default_factory=Axis)

    spectral_lines: SpectralLines = field(default_factory=SpectralLines)
    smoothing_slider: Slider = field(default_factory=lambda: Slider(max_value=3, step=0.05))
    redshift_slider: Slider = field(default_factory=lambda: Slider(visible=False, max_value=10, step=1e-6,
                                                                   show_text_editor=True, show_save_button=True))


@dataclass
class ImageCentralAxes:
    x: bool = False
    y: bool = False


@dataclass
class Image(ViewerElement):
    wcs_transform: bool = False
    rotate: float | str | None = None
    color_bar: ColorBar = field(default_factory=ColorBar)
    central_axes: ImageCentralAxes = field(default_factory=ImageCentralAxes)
    central_crosshair: bool = False


@dataclass
class Plot1D(ViewerElement):
    plots: dict[str, LinePlot] = field(default_factory=dict)


@dataclass
class DataWidgets(Params):
    images: dict[str, Image] = field(default_factory=dict)
    plots: dict[str, Plot1D] = field(default_factory=dict)
