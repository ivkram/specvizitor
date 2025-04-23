from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

from functools import partial
import logging

from ..config import config
from ..config.data_widgets import DataWidgets
from ..config.spectral_lines import SpectralLineData
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..io.viewer_data import ViewerData
from ..plugins.plugin_core import PluginCore
from ..utils.widgets import AbstractWidget

from .ViewerElement import ViewerElement, LinkableItem, SliderItem
from .Image2D import Image2D
from .Plot1D import Plot1D
from .SmartSlider import SmartSlider
from .ItemLinker import ItemLinker, XAxisLinker, YAxisLinker, SliderLinker, ColorBarLinker

logger = logging.getLogger(__name__)


class DataViewer(AbstractWidget):
    object_selected = QtCore.Signal(int, InspectionData, ViewerData, config.DataSources, object)
    data_collected = QtCore.Signal(dict)

    redshift_requested = QtCore.Signal()
    redshift_changed = QtCore.Signal(float)
    redshift_obtained = QtCore.Signal(float)

    zen_mode_activated = QtCore.Signal()
    visibility_changed = QtCore.Signal()
    view_reset = QtCore.Signal(object)
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

        self._data = ViewerData()
        self.open_images()

        self._widget_links: dict[LinkableItem, dict] = {item: dict() for item in LinkableItem}
        self._widget_linkers: dict[LinkableItem, ItemLinker] | None = None
        self._create_widget_linkers()

        self.dock_area: DockArea | None = None
        self._added_docks: list[str] = []

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
        return {wt: w for wt, w in self.widgets.items() if w.data is not None}

    def _create_widgets(self):
        for wt in list(self.widgets):
            self._delete_widget(wt)

        widgets = {}

        kwargs = dict(
            appearance=self._appearance,
            spectral_lines=self._spectral_lines,
            parent=self
        )

        for name, image_cfg in self._widget_cfg.images.items():
            widgets[name] = Image2D(cfg=image_cfg, title=name, **kwargs)

        for name, plot_cfg in self._widget_cfg.plots.items():
            widgets[name] = Plot1D(cfg=plot_cfg, title=name, **kwargs)

        for plugin in self._plugins:
            plugin.override_widget_configs(widgets)

        self.widgets = widgets

    def _delete_widget(self, wt: str):
        self._unlink_widget(wt)
        self._disconnect_widget(wt)

        w0 = self.widgets.pop(wt)

        w0.graphics_layout.clear()
        w0.deleteLater()

    def _connect_widget(self, wt: str):
        w0 = self.widgets[wt]

        self.object_selected.connect(w0.load_object)
        self.zen_mode_activated.connect(w0.hide_interface)
        self.visibility_changed.connect(w0.update_visibility)
        self.view_reset.connect(w0.reset_view)
        self.spectral_lines_changed.connect(w0.update_spectral_lines)

        w0.object_loaded.connect(self._attach_widget)
        w0.object_destroyed.connect(self._detach_widget)
        w0.redshift_slider.save_button_clicked.connect(self._save_redshift)

    def _disconnect_widget(self, wt: str):
        w0 = self.widgets[wt]

        self.object_selected.disconnect(w0.load_object)
        self.zen_mode_activated.disconnect(w0.hide_interface)
        self.visibility_changed.disconnect(w0.update_visibility)
        self.view_reset.disconnect(w0.reset_view)
        self.spectral_lines_changed.disconnect(w0.update_spectral_lines)

        w0.object_loaded.disconnect()
        w0.object_destroyed.disconnect()
        w0.redshift_slider.save_button_clicked.disconnect()

    def _create_widget_linkers(self):
        self._widget_linkers = {
            LinkableItem.XAXIS: XAxisLinker(),
            LinkableItem.YAXIS: YAxisLinker(),
            LinkableItem.COLORBAR: ColorBarLinker(),
            LinkableItem.S_SLIDER: SliderLinker(SliderItem.SMOOTHING),
            LinkableItem.S_REDSHIFT: SliderLinker(SliderItem.REDSHIFT)
        }

    def _link_widget(self, wt: str):
        w0 = self.widgets[wt]

        for w in self.active_widgets.values():
            for linked_item, linker in self._widget_linkers.items():
                linker.link(w0, w, self._widget_links[linked_item])
                linker.link(w, w0, self._widget_links[linked_item])

    def _unlink_widget(self, wt: str):
        w0 = self.widgets[wt]

        for w in self.active_widgets.values():
            for linked_item, linker in self._widget_linkers.items():
                linker.unlink(w0, w, self._widget_links[linked_item])
                linker.unlink(w, w0, self._widget_links[linked_item])

    def _close_dock(self, dt: str, dock: Dock | None = None):
        if dock is None:
            dock = self.docks[dt]

        container = dock.container()
        if container and not isinstance(container, DockArea):
            self._close_dock(dt, container)
        else:
            dock.close()
            self._added_docks.remove(dt)
            self.docks.pop(dt)
            return

    def _create_docks(self):
        for dt in list(self.docks):
            self._close_dock(dt)

        docks = {}
        for widget in self.widgets.values():
            docks[widget.title] = Dock(widget.title, widget=widget)

        self.docks = docks

    def _add_dock(self, dt: str):
        dock, widget = self.docks[dt], self.widgets[dt]
        position = widget.cfg.position if widget.cfg.position is not None else 'bottom'
        relative_to = widget.cfg.relative_to if widget.cfg.relative_to in self._added_docks else None

        self.dock_area.addDock(dock=dock, position=position, relativeTo=relative_to)
        self._added_docks.append(dt)

    def _add_docks(self):
        for dt in self.docks:
            if not self.widgets[dt].cfg.visible:
                continue
            self._add_dock(dt)

        for plugin in self._plugins:
            plugin.update_docks(self.docks)

    @QtCore.Slot()
    def reset_dock_layout(self):
        self._create_docks()
        self._add_docks()

    @staticmethod
    def _clean_dock_layout(layout: dict):
        float_layout_cleaned = []
        for l in layout['float']:
            if l[0]['main'] is not None:
                float_layout_cleaned.append(l)

        layout['float'] = float_layout_cleaned

    @QtCore.Slot(dict)
    def restore_dock_layout(self, layout: dict):
        # fix for a pyqtgraph bug where empty layouts throw an error
        self._clean_dock_layout(layout)

        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `layout`
            self.dock_area.restoreState(layout, missing='ignore', extra=None)
            logger.info("Dock layout restored")

            for plugin in self._plugins:
                plugin.update_docks(self.docks)
        except (KeyError, ValueError, TypeError) as e:
            self.reset_dock_layout()
            logger.error(f"Failed to restore the dock layout: {e}")

    def init_ui(self):
        if self.dock_area is None:
            self.dock_area = DockArea(parent=self)

        self._create_widgets()
        self._create_docks()
        self._add_docks()

        for wt in self.widgets:
            self._connect_widget(wt)

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
    def open_images(self):
        if self._data_cfg.images is None:
            return

        for img_label, img_cfg in self._data_cfg.images.items():
            self._data.open_image(filename=img_cfg.filename, loader=img_cfg.loader, wcs_source=img_cfg.wcs_source,
                                  **img_cfg.loader_params)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object)
    def load_object(self, j: int, review: InspectionData, cat_entry: Catalog | None):
        self.object_selected.emit(j, review, self._data, self._data_cfg, cat_entry)

        for plugin in self._plugins:
            plugin.update_active_widgets(self.active_widgets, cat_entry=cat_entry)
            plugin.update_docks(self.docks, cat_entry=cat_entry)

        self.reset_view()

    @QtCore.Slot(str)
    def _attach_widget(self, wt: str):
        w0 = self.widgets[wt]
        self._link_widget(wt)
        self.docks[wt].setTitle(w0.get_dock_title())

    @QtCore.Slot(str)
    def _detach_widget(self, wt: str):
        w0 = self.widgets[wt]
        self._unlink_widget(wt)
        self.docks[wt].setTitle(w0.title)

        self._data.close(str(w0.data_path))

    def _get_active_redshift_slider(self) -> SmartSlider | None:
        for w in self.active_widgets.values():
            if w.redshift_slider.isVisible():
                return w.redshift_slider
        return None

    @QtCore.Slot()
    def reset_view(self):
        self.view_reset.emit(self._widget_links)

    @QtCore.Slot()
    def request_redshift(self):
        slider = self._get_active_redshift_slider()
        if slider is None:
            return

        self.redshift_requested.connect(slider.save_value)
        self.redshift_requested.emit()
        self.redshift_requested.disconnect()

    @QtCore.Slot(float)
    def _save_redshift(self, redshift: float):
        self.redshift_obtained.emit(redshift)

    def change_redshift(self, n_steps: int, small_step: bool = False):
        slider = self._get_active_redshift_slider()
        if slider is None:
            return

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

    @QtCore.Slot()
    def free_resources(self):
        self._data.close_all()
