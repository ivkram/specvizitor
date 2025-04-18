from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

from functools import partial
import logging
import pathlib

from ..config import config
from ..config.data_widgets import DataWidgets
from ..config.spectral_lines import SpectralLineData
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..io.viewer_data import add_image
from ..plugins.plugin_core import PluginCore
from ..utils.qt_tools import safe_disconnect
from ..utils.widgets import AbstractWidget

from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Plot1D import Plot1D
from .SmartSlider import SmartSlider

logger = logging.getLogger(__name__)


class DataViewer(AbstractWidget):
    object_selected = QtCore.Signal(int, InspectionData, config.DataSources, object)
    view_reset = QtCore.Signal()
    data_collected = QtCore.Signal(dict)
    redshift_requested = QtCore.Signal()
    redshift_changed = QtCore.Signal(float)
    redshift_obtained = QtCore.Signal(float)

    zen_mode_activated = QtCore.Signal()
    visibility_changed = QtCore.Signal()
    spectral_lines_changed = QtCore.Signal()

    def __init__(self,
                 global_cfg: config.DataViewer,
                 data_cfg: config.DataSources,
                 widget_cfg: DataWidgets,
                 appearance: config.Appearance,
                 spectral_lines: SpectralLineData,
                 plugins: list[PluginCore],
                 parent=None):

        self._global_cfg = global_cfg
        self._data_cfg = data_cfg
        self._widget_cfg = widget_cfg
        self._appearance = appearance
        self._spectral_lines = spectral_lines
        self._plugins = plugins

        # load images that are shared between widgets and can be used to create cutouts
        self.load_field_images()

        self.dock_area: DockArea | None = None
        self.added_docks: list[str] = []

        self.widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        QtWidgets.QShortcut('Q', self, partial(self.change_redshift, -1))
        QtWidgets.QShortcut('W', self, partial(self.change_redshift, 1))

        QtWidgets.QShortcut('Shift+Q', self, partial(self.change_redshift, -1, True))
        QtWidgets.QShortcut('Shift+W', self, partial(self.change_redshift, 1, True))

    @property
    def active_widgets(self) -> dict[str, ViewerElement]:
        return {title: w for title, w in self.widgets.items() if w.data is not None}

    def _delete_widgets(self):
        # disconnect signals
        self.object_selected.disconnect()
        self.zen_mode_activated.disconnect()
        self.visibility_changed.disconnect()
        self.spectral_lines_changed.disconnect()
        safe_disconnect(self.view_reset)

        for w in self.widgets.values():
            w.graphics_layout.clear()
            w.deleteLater()

        self.widgets = {}

    def _create_widgets(self):
        # delete previously created widgets
        if self.widgets:
            self._delete_widgets()

        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        for name, image_cfg in self._widget_cfg.images.items():
            widgets[name] = Image2D(cfg=image_cfg, title=name, appearance=self._appearance,
                                    spectral_lines=self._spectral_lines, parent=self)

        # create widgets for plots, including 1D spectra
        for name, plot_cfg in self._widget_cfg.plots.items():
            widgets[name] = Plot1D(cfg=plot_cfg, title=name, appearance=self._appearance,
                                   spectral_lines=self._spectral_lines, parent=self)

        for plugin in self._plugins:
            plugin.override_widget_configs(widgets)

        self.widgets = widgets
        self._connect_widgets()

    def _connect_widgets(self):
        for w in self.widgets.values():
            self.object_selected.connect(w.load_object)
            self.zen_mode_activated.connect(w.hide_interface)
            self.visibility_changed.connect(w.update_visibility)
            self.spectral_lines_changed.connect(w.update_spectral_lines)

            w.redshift_slider.save_button_clicked.connect(self._save_redshift)

        self._connect_sliders()  # sliders always stay connected

    def _connect_sliders(self):
        for w in self.widgets.values():
            for slider_name, slider in w.sliders.items():
                if slider.link_to is not None:
                    try:
                        source_slider = self.widgets[slider.link_to].sliders[slider_name]
                    except KeyError:
                        logger.error(f'Failed to link sliders (source widget: {slider.link_to}, slider: {slider_name})')
                    else:
                        source_slider.value_changed[float].connect(slider.set_value)
                        slider.value_changed[float].connect(source_slider.set_value)

    def _reconnect_widgets(self):
        self._connect_views()
        self._connect_colorbars()

    def _disconnect_widgets(self):
        self._disconnect_views()
        self._disconnect_colorbars()

    def _connect_views(self):
        for w in self.active_widgets.values():
            self.view_reset.connect(w.reset_view)

            # TODO: throw a warning if two axes have different unit/scale
            if w.cfg.x_axis.link_to:
                w.container.setXLink(w.cfg.x_axis.link_to)
            if w.cfg.y_axis.link_to:
                w.container.setYLink(w.cfg.y_axis.link_to)

    def _disconnect_views(self):
        safe_disconnect(self.view_reset)
        for w in self.widgets.values():
            w.container.setXLink(None)
            w.container.setYLink(None)

    def _connect_colorbars(self):
        images: dict[str, Image2D] = {widget_name: w for widget_name, w in self.widgets.items() if isinstance(w, Image2D)}
        for w in images.values():
            if w.cfg.color_bar.link_to is not None:
                try:
                    source_widget = images[w.cfg.color_bar.link_to]
                except KeyError:
                    logger.error(f'Failed to (un)link color bars (source widget: {w.cfg.color_bar.link_to})')
                else:
                    if w.data is not None and w.has_defined_levels:
                        source_widget.cbar.sigLevelsChanged[tuple].connect(w.set_levels)
                        w.cbar.sigLevelsChanged[tuple].connect(source_widget.set_levels)

    def _disconnect_colorbars(self):
        images: dict[str, Image2D] = {widget_name: w for widget_name, w in self.widgets.items() if
                                      isinstance(w, Image2D)}
        for w in images.values():
            safe_disconnect(w.cbar.sigLevelsChanged[tuple])

    def _close_dock(self, dock: Dock):
        container = dock.container()
        if container and not isinstance(container, DockArea):
            self._close_dock(container)
        else:
            dock.close()
            return

    def _close_docks(self):
        for d in self.docks.values():
            self._close_dock(d)
        self.docks = {}

    def _create_docks(self):
        # delete previously created docks
        self._close_docks()

        docks = {}
        for widget in self.widgets.values():
            docks[widget.title] = Dock(widget.title, widget=widget)

        self.docks = docks

    def _add_dock(self, widget: ViewerElement):
        dock = self.docks[widget.title]
        position = widget.cfg.position if widget.cfg.position is not None else 'bottom'
        relative_to = widget.cfg.relative_to if widget.cfg.relative_to in self.added_docks else None

        self.dock_area.addDock(dock=dock, position=position, relativeTo=relative_to)
        self.added_docks.append(widget.title)

    def _add_docks(self):
        self.added_docks = []

        for widget in self.widgets.values():
            if widget.cfg.visible:
                self._add_dock(widget)

        for plugin in self._plugins:
            plugin.update_docks(self.docks)

    @QtCore.Slot()
    def init_docks(self):
        self._create_docks()
        self._add_docks()
        self._update_dock_titles()

    @staticmethod
    def clean_layout(layout: dict):
        float_layout_cleaned = []
        for l in layout['float']:
            if l[0]['main'] is not None:
                float_layout_cleaned.append(l)

        layout['float'] = float_layout_cleaned

    @QtCore.Slot(dict)
    def restore_dock_layout(self, layout: dict):
        # fix for a pyqtgraph bug where empty layouts throw an error
        self.clean_layout(layout)

        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `layout`
            self.dock_area.restoreState(layout, missing='ignore', extra=None)
            logger.info('Dock layout restored')

            for plugin in self._plugins:
                plugin.update_docks(self.docks)
        except (KeyError, ValueError, TypeError) as e:
            self.init_docks()  # to reset the dock layout
            logger.error(f'Failed to restore the dock layout: {e}')

    def init_ui(self):
        if self.dock_area is None:
            self.dock_area = DockArea(parent=self)
        self._create_widgets()
        self.init_docks()

    def set_layout(self):
        self.setLayout(QtWidgets.QGridLayout())
        self.set_geometry(spacing=0, margins=0)

    def populate(self):
        self.layout().addWidget(self.dock_area, 1, 1, 1, 1)

    @QtCore.Slot(DataWidgets)
    def update_viewer_configuration(self, viewer_cfg: DataWidgets):
        self._widget_cfg = viewer_cfg
        self.init_ui()

    @QtCore.Slot()
    def load_field_images(self):
        if self._data_cfg.images is None:
            return

        for img_label, img_cfg in self._data_cfg.images.items():
            add_image(filename=img_cfg.filename, loader=img_cfg.loader, wcs_source=img_cfg.wcs_source,
                      **img_cfg.loader_params)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object)
    def load_object(self, j: int, review: InspectionData, cat_entry: Catalog | None):
        self._disconnect_widgets()

        self.object_selected.emit(j, review, self._data_cfg, cat_entry)

        self._reconnect_widgets()
        self._update_dock_titles()

        for plugin in self._plugins:
            plugin.update_viewer(self.active_widgets, cat_entry)
            plugin.update_docks(self.docks, cat_entry)

    def _find_active_redshift_slider(self) -> SmartSlider | None:
        for w in self.active_widgets.values():
            if w.redshift_slider.isVisible():
                return w.redshift_slider
        return None

    @QtCore.Slot()
    def request_redshift(self):
        slider = self._find_active_redshift_slider()
        if slider:
            self.redshift_requested.connect(slider.save_value)
            self.redshift_requested.emit()
            self.redshift_requested.disconnect()

    @QtCore.Slot(float)
    def _save_redshift(self, redshift: float):
        self.redshift_obtained.emit(redshift)

    def change_redshift(self, n_steps: int, small_step: bool = False):
        slider = self._find_active_redshift_slider()
        if slider:
            self.redshift_changed.connect(slider.set_value)

            z = slider.value
            step = self._global_cfg.redshift_small_step if small_step else self._global_cfg.redshift_step
            dz = n_steps * step * (1 + z)

            self.redshift_changed.emit(z + dz)
            self.redshift_changed.disconnect()

    @QtCore.Slot()
    def collect(self):
        self.data_collected.emit(self.dock_area.saveState())

    @QtCore.Slot(str)
    def take_screenshot(self, filename: str):
        self.grab().save(filename)

    def _update_dock_titles(self):
        for w in self.widgets.values():
            if w.filename is None or w.meta is None:
                self.docks[w.title].setTitle(w.title)
                continue

            title = w.filename.name if isinstance(w.filename, pathlib.Path) else w.filename

            # adding EXTNAME and EXTVER to the dock title
            fits_meta = w.meta.get('EXTNAME'), w.meta.get('EXTVER')
            j = 0
            while j < len(fits_meta) and fits_meta[j] is not None:
                j += 1
            title_meta = ', '.join(map(str, fits_meta[:j]))

            if title_meta:
                if w.cfg.dock_title_fmt == 'short':
                    title = title_meta  # str(fits_meta[j - 1])
                else:
                    title += f' [{title_meta}]'

            self.docks[w.title].setTitle(title)

    @QtCore.Slot()
    def hide_interface(self):
        for dock in self.docks.values():
            dock.hideTitleBar()
        self.zen_mode_activated.emit()

    @QtCore.Slot()
    def restore_visibility(self):
        for dock in self.docks.values():
            dock.showTitleBar()
        self.visibility_changed.emit()
