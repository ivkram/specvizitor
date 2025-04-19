from astropy.io.fits.header import Header
import astropy.units as u
from astropy.units import Quantity, UnitConversionError
import numpy as np
from qtpy import QtGui, QtCore, QtWidgets
import pyqtgraph as pg

import abc
from dataclasses import asdict, dataclass, field
import logging
import pathlib

from ..config import config, data_widgets
from ..config import SpectralLineData
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData, REDSHIFT_FILL_VALUE
from ..io.viewer_data import ViewerData, get_cutout_params, load_widget_data
from ..utils.widgets import AbstractWidget, MyViewBox

from .SmartSlider import SmartSlider

logger = logging.getLogger(__name__)


@dataclass
class Axis:
    unit: u.Unit | None = None
    scale: str = 'linear'
    label: str | None = None
    limits: tuple[float, float] = (0, 1)
    padding: float = 0

    @property
    def label_ext(self) -> str | None:
        if not self.label:
            return None

        unit_str = None
        if self.unit:
            unit_str = self.unit.to_string('unicode', fraction=True)

        label = self.label
        if self.scale == 'log':
            if unit_str:
                label = f'{label}/{unit_str}'
            label = f'log {label}'
        elif unit_str:
            label = f'{label} [{unit_str}]'

        return label

    @property
    def limits_padded(self) -> tuple[float, float]:
        w = self.limits[1] - self.limits[0]
        pad_abs = self.padding * w
        return self.limits[0] - pad_abs, self.limits[1] + pad_abs


@dataclass
class Axes:
    x: Axis = field(default_factory=Axis)
    y: Axis = field(default_factory=Axis)


class PlotTransformBase:
    def __init__(self, widget_title: str):
        self.widget_title = widget_title

    @abc.abstractmethod
    def apply(self, plot_data: Quantity | np.ndarray) -> Quantity | np.ndarray:
        pass


class ScaleTransform(PlotTransformBase):
    ALLOWED_PLOT_SCALES: tuple[str] = ('linear', 'log')

    def __init__(self, widget_title: str, scale='linear'):
        super().__init__(widget_title=widget_title)

        if scale not in self.ALLOWED_PLOT_SCALES:
            logger.error(f'Unknown scaling type: `{scale}` (widget: {self.widget_title})')
            self.scale = None

        self.scale = scale

    def apply(self, plot_data: Quantity | np.ndarray) -> Quantity | np.ndarray:
        if self.scale == 'log':
            if isinstance(plot_data, Quantity):
                plot_data = plot_data.value
            with np.errstate(invalid='ignore', divide='ignore'):
                plot_data = np.log10(plot_data)

        return plot_data


class UnitTransform(PlotTransformBase):
    def __init__(self, widget_title: str, unit: u.Unit):
        super().__init__(widget_title=widget_title)
        self.unit = unit

    def apply(self, plot_data: Quantity | np.ndarray) -> Quantity:
        if isinstance(plot_data, Quantity):
            try:
                plot_data = plot_data.value * plot_data.unit.to(self.unit)
            except UnitConversionError as e:
                logger.error(f'{e}. Axis unit will be ignored (widget: {self.widget_title})')
        else:
            plot_data = plot_data * self.unit

        return plot_data


class ViewerElement(AbstractWidget):
    content_added = QtCore.Signal()
    view_reset = QtCore.Signal()
    content_cleared = QtCore.Signal(str)
    smoothing_applied = QtCore.Signal(float)

    ALLOWED_DATA_TYPES: tuple[type] | None = None

    def __init__(self, title: str, cfg: data_widgets.ViewerElement, appearance: config.Appearance,
                 spectral_lines: SpectralLineData, parent=None):
        self.title = title
        self.cfg = cfg
        self.appearance = appearance

        self.filename: pathlib.Path | None = None
        self.data = None
        self.meta: dict | Header | None = None

        self._graphics_view: pg.GraphicsView | None = None
        self.graphics_layout: pg.GraphicsLayout | None = None

        # graphics view properties
        self._axes: Axes | None = None
        self._qtransform: QtGui.QTransform | None = None

        # graphics items
        self.container: pg.PlotItem | None = None
        self._registered_items: list[pg.GraphicsItem] = []

        self._spectral_lines = spectral_lines
        self._spectral_line_artists: dict[str, tuple[pg.InfiniteLine, pg.TextItem]] = {}

        self.sliders: dict[str, SmartSlider] = {}  # has to be a dictionary to enable links
        self.smoothing_slider: SmartSlider | None = None
        self.redshift_slider: SmartSlider | None = None

        super().__init__(parent=parent)

        self.init_view()
        self.setEnabled(False)

        self.content_cleared.connect(ViewerData().close)

    def _apply_axis_data_transform(self, plot_data: Quantity | np.ndarray, scale: str,
                                   unit: u.Unit | None) -> Quantity | np.ndarray:
        # order is important: first convert units, then apply scaling
        if unit:
            plot_data = UnitTransform(self.title, unit=unit).apply(plot_data)
        plot_data = ScaleTransform(self.title, scale=scale).apply(plot_data)

        return plot_data

    def apply_xdata_transform(self, plot_data: Quantity | np.ndarray) -> Quantity | np.ndarray:
        return self._apply_axis_data_transform(plot_data, scale=self._axes.x.scale, unit=self._axes.x.unit)

    def apply_ydata_transform(self, plot_data: Quantity | np.ndarray) -> Quantity | np.ndarray:
        return self._apply_axis_data_transform(plot_data, scale=self._axes.y.scale, unit=self._axes.y.unit)

    def _create_line_artists(self):
        if self._spectral_line_artists:
            for line_artist in self._spectral_line_artists.values():
                line_artist[0].deleteLater()
                line_artist[1].deleteLater()

        self._spectral_line_artists = {}

        line_color = self.cfg.spectral_lines.color
        if line_color is None:
            if self.appearance.theme == 'dark':
                line_color = (255, 255, 255)
            else:
                line_color = (175.68072, 220.68924, 46.59488)
        line_pen = pg.mkPen(color=line_color, width=1)

        for line_name, lambda0 in self._spectral_lines.wavelengths.items():
            line = pg.InfiniteLine(pen=line_pen)
            line.setZValue(10)

            label = pg.TextItem(text=line_name, color=line_color, anchor=(0, 1), angle=-90)
            label.setZValue(11)

            self._spectral_line_artists[line_name] = (line, label)

    def _add_line_artists(self):
        if self.cfg.spectral_lines.visible:
            for line_name, line_artist in self._spectral_line_artists.items():
                self.container.addItem(line_artist[0], ignoreBounds=True)
                self.container.addItem(line_artist[1])

    def init_ui(self):
        self._graphics_view = pg.GraphicsView(parent=self)

        self.graphics_layout = pg.GraphicsLayout()
        self._graphics_view.setCentralItem(self.graphics_layout)

        self.container = pg.PlotItem(name=self.title, viewBox=MyViewBox(enableMenu=False))
        self.set_axes_visibility()
        self.container.hideButtons()
        self.container.setMouseEnabled(True, True)

        self._create_line_artists()
        self._add_line_artists()

        self.graphics_layout.addItem(self.container, 0, 0)

        self._init_sliders()

    def _init_sliders(self):
        self.smoothing_slider = SmartSlider(short_name='sigma', action='smooth the data', parent=self,
                                            **asdict(self.cfg.smoothing_slider))
        self.redshift_slider = SmartSlider(short_name='z', full_name='redshift', parent=self,
                                           **asdict(self.cfg.redshift_slider))

        self.sliders['smoothing'] = self.smoothing_slider
        self.sliders['redshift'] = self.redshift_slider

        self.smoothing_slider.value_changed[float].connect(self.smooth)
        self.redshift_slider.value_changed[float].connect(self.redshift_changed_action)

    def set_geometry(self, spacing: int, margins: int | tuple[int, int, int, int]):
        super().set_geometry(spacing=spacing, margins=margins)

        self.graphics_layout.setSpacing(spacing)
        self.graphics_layout.setContentsMargins(0, 0, 5, 5)

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=self.appearance.viewer_spacing, margins=self.appearance.viewer_margins)

    def populate(self):
        # add vertical sliders and the graphics view
        sub_layout = QtWidgets.QHBoxLayout()
        for s in self.sliders.values():
            if not s.show_text_editor:
                sub_layout.addWidget(s)
        sub_layout.addWidget(self._graphics_view)
        self.layout().addLayout(sub_layout, 1, 1, 1, 1)

        # add horizontal sliders
        sub_layout = QtWidgets.QVBoxLayout()
        for s in self.sliders.values():
            if s.show_text_editor:
                sub_layout.addWidget(s)
        self.layout().addLayout(sub_layout, 2, 1, 1, 1)

    def init_view(self):
        x_unit = u.Unit(self.cfg.x_axis.unit) if self.cfg.x_axis.unit else None
        y_unit = u.Unit(self.cfg.y_axis.unit) if self.cfg.y_axis.unit else None
        self._axes = Axes(x=Axis(unit=x_unit, scale=self.cfg.x_axis.scale, label=self.cfg.x_axis.label),
                          y=Axis(unit=y_unit, scale=self.cfg.y_axis.scale, label=self.cfg.y_axis.label))
        self._qtransform = QtGui.QTransform()

    def set_axes_visibility(self):
        self.container.showAxes((self.cfg.y_axis.visible, False, False, self.cfg.x_axis.visible),
                                showValues=(self.cfg.y_axis.visible, False, False, self.cfg.x_axis.visible))

    def update_axis_labels(self):
        show_xaxis = self.container.getAxis('bottom').isVisible()
        show_yaxis = self.container.getAxis('left').isVisible()

        self.container.setLabel(axis='bottom', text=self._axes.x.label_ext)
        self.container.setLabel(axis='left', text=self._axes.y.label_ext)

        # pyqtgraph changes axis visibility after adding labels
        self.container.showAxes((show_yaxis, False, False, show_xaxis))

    def setEnabled(self, a0: bool = True):
        super().setEnabled(a0)
        for line_artist in self._spectral_line_artists.values():
            line_artist[0].setVisible(a0)
            line_artist[1].setVisible(a0)
        for s in self.sliders.values():
            s.setEnabled(a0)

    @QtCore.Slot(int, InspectionData, config.DataSources, object)
    def load_object(self, j: int, review: InspectionData, data_sources: config.DataSources, cat_entry: Catalog | None):
        self.setEnabled(False)
        if self.data is not None:
            self.clear_content()
            self.clear_slider_view()
        self.filename, self.data, self.meta = None, None, None

        self.load_data(review.get_id(j), data_sources, cat_entry)

        if self.data is None:
            self.filename, self.meta = None, None
            return

        self.add_content(cat_entry)
        self.setup_slider_view(j, review, cat_entry)
        self.update_widgets_from_sliders()
        self.reset_view()
        self.setEnabled(True)

    def load_data(self, obj_id: str | int, data_sources: config.DataSources, cat_entry: Catalog | None):
        kwargs = dict()

        if self.cfg.data.source:  # for now assume this is equivalent to self.cfg.data.source.startswith("image")
            if cat_entry is None:
                logger.error(f"Failed to create an image cutout: Catalog entry not loaded (widget: {self.title})")
                return
            image = data_sources.images.get(self.cfg.data.source)
            if not image:
                logger.error(f"Shared image not found (label: {self.cfg.data.source}, widget: {self.title})")
                return

            filename = image.filename
            wcs_source = image.wcs_source if image.wcs_source else image.filename

            kwargs = get_cutout_params(cat_entry, wcs_source)
            if kwargs is None:
                return
        else:
            if self.cfg.data.filename is None:
                logger.error(f"Filename not specified (widget: {self.title})")
                return
            filename = str(pathlib.Path(data_sources.dir) / self.cfg.data.filename)

        self.filename, self.data, self.meta = load_widget_data(
            obj_id, filename, self.cfg.data.loader, self.title, cat_entry, allowed_dtypes=self.ALLOWED_DATA_TYPES,
            **self.cfg.data.loader_params, **kwargs
        )

    def add_content(self, cat_entry: Catalog | None):
        self.setup_view(cat_entry)

    def register_item(self, item: pg.GraphicsItem, **kwargs):
        item.setTransform(self._qtransform)
        self.container.addItem(item, **kwargs)
        self._registered_items.append(item)

    def setup_view(self, cat_entry: Catalog | None):
        xlim = (self.cfg.x_axis.limits.min, self.cfg.x_axis.limits.max)
        ylim = (self.cfg.y_axis.limits.min, self.cfg.y_axis.limits.max)

        xlim = (xlim[0] if xlim[0] is not None else self._axes.x.limits[0],
                xlim[1] if xlim[1] is not None else self._axes.x.limits[1])

        ylim = (ylim[0] if ylim[0] is not None else self._axes.y.limits[0],
                ylim[1] if ylim[1] is not None else self._axes.y.limits[1])

        self.set_default_range(xrange=xlim, yrange=ylim)

        self.update_axis_labels()
        self.apply_qtransform()

    def setup_slider_view(self, j: int, review: InspectionData, cat_entry: Catalog | None):
        for slider_name, s in self.sliders.items():
            s.set_default_value_from_catalog(cat_entry)  # load the catalog value to the slider
            if slider_name == 'redshift':  # load redshift from inspection results
                redshift = review.get_value(j, 'z_sviz')
                if not np.isclose(redshift, REDSHIFT_FILL_VALUE):
                    s.set_default_value(redshift)

    def update_widgets_from_sliders(self):
        for s in self.sliders.values():
            s.update_from_slider()

    def set_default_range(self, xrange: tuple[float, float] | None = None, yrange: tuple[float, float] | None = None,
                          apply_qtransform=False, update: bool = False):
        if apply_qtransform:
            if not xrange or not yrange:
                raise ValueError("Can only apply transformation when both x- and y-axis limits are specified")

            x1, y1 = self._qtransform.map(xrange[0], yrange[0])
            x2, y2 = self._qtransform.map(xrange[1], yrange[1])

            xrange, yrange = (x1, x2), (y1, y2)

        if xrange:
            self._axes.x.limits = xrange
        if yrange:
            self._axes.y.limits = yrange

        if update:
            self.reset_range()

    def set_content_padding(self, xpad: float | None = None, ypad: float | None = None):
        if xpad:
            self._axes.x.padding = xpad
        if ypad:
            self._axes.y.padding = ypad

    def apply_qtransform(self, apply_to_default_range=False):
        if apply_to_default_range:
            self.set_default_range(self._axes.x.limits, self._axes.y.limits, apply_qtransform=True)

        for item in self._registered_items:
            item.setTransform(self._qtransform)

    def smooth(self, sigma: float):
        pass

    def set_spectral_line_positions(self, redshift: float = 0):
        # check unit compatibility
        line_unit = u.Unit(self._spectral_lines.wave_unit)
        if self._axes.x.unit:
            try:
                line_unit.to(self._axes.x.unit)
            except UnitConversionError as e:
                if self.cfg.spectral_lines.visible:
                    logger.error(f'Failed to calculate positions of spectral lines: {e} (widget: {self.title})')
                return

        scale0 = 1 + redshift
        y_min, y_max = self._axes.y.limits
        label_height = y_max - (y_max - y_min) * 0.03

        line_waves = np.array([self._spectral_lines.wavelengths[line_name]
                               for line_name in self._spectral_line_artists.keys()]) * scale0
        line_waves = self.apply_xdata_transform(line_waves * u.Unit('AA'))
        if isinstance(line_waves, Quantity):
            line_waves = line_waves.value

        for line_wave, line_artist in zip(line_waves, self._spectral_line_artists.values()):
            line_artist[0].setPos(line_wave)
            line_artist[1].setPos(QtCore.QPointF(line_wave, label_height))

    def redshift_changed_action(self, redshift: float):
        self.set_spectral_line_positions(redshift)

    def reset_range(self):
        self.container.setRange(xRange=self._axes.x.limits_padded, yRange=self._axes.y.limits_padded, padding=0)

    def reset_view(self):
        self.reset_range()

        self.redshift_slider.reset()
        self.redshift_changed_action(self.redshift_slider.value)

    def remove_registered_items(self):
        while self._registered_items:
            item = self._registered_items.pop()
            self.container.removeItem(item)

    def clear_content(self):
        self.remove_registered_items()
        self.init_view()

        self.content_cleared.emit(str(self.filename))

    def clear_slider_view(self):
        for s in self.sliders.values():
            s.clear()

    @QtCore.Slot()
    def hide_interface(self):
        self.container.showAxes(False, showValues=False)
        self.smoothing_slider.setVisible(False)

    @QtCore.Slot()
    def update_visibility(self):
        self.set_axes_visibility()
        self.smoothing_slider.setVisible(self.cfg.smoothing_slider.visible)

    @QtCore.Slot()
    def update_spectral_lines(self):
        self._create_line_artists()
        self._add_line_artists()
