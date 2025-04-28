from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

from functools import partial
import logging
import time

from ..config import config, data_widgets
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
from .ViewerDataLoader import ViewerDataLoader
from .ItemLinker import ItemLinker, XAxisLinker, YAxisLinker, SliderLinker, ColorBarLinker

logger = logging.getLogger(__name__)


class DataViewer(AbstractWidget):
    project_loaded = QtCore.Signal()
    data_loaded = QtCore.Signal(int, InspectionData, object)
    object_loaded = QtCore.Signal()
    loading_aborted = QtCore.Signal()
    data_collected = QtCore.Signal(dict)

    redshift_requested = QtCore.Signal()
    redshift_changed = QtCore.Signal(float)
    redshift_obtained = QtCore.Signal(float)

    view_reset = QtCore.Signal(object)
    visibility_changed = QtCore.Signal(bool)
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

        self._zen_mode_activated: bool = False

        self._data = ViewerData()
        self.open_images()

        self._widget_links: dict[LinkableItem, dict] = {item: dict() for item in LinkableItem}
        self._widget_linkers: dict[LinkableItem, ItemLinker] = dict()
        self._create_widget_linkers()

        self._worker: ViewerDataLoader | None = None
        self._lock: bool = False
        self._t_worker_start = None
        self._t_old_worker_start = None

        self.dock_area: DockArea | None = None
        self._added_docks: list[str] = []

        self.widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        QtWidgets.QShortcut('Q', self, partial(self._change_redshift, -1))
        QtWidgets.QShortcut('W', self, partial(self._change_redshift, 1))

        QtWidgets.QShortcut('Shift+Q', self, partial(self._change_redshift, -1, True))
        QtWidgets.QShortcut('Shift+W', self, partial(self._change_redshift, 1, True))

    @property
    def active_widgets(self) -> dict[str, ViewerElement]:
        return {wt: w for wt, w in self.widgets.items() if w.data is not None}

    def _create_widget(self, wt: str, cfg: data_widgets.ViewerElement):
        constructor = None
        if isinstance(cfg, data_widgets.Image):
            constructor = Image2D
        elif isinstance(cfg, data_widgets.Plot1D):
            constructor = Plot1D
        if constructor is None:
            logger.error(f"Unknown widget configuration type: {type(cfg)}")

        kwargs = dict(
            appearance=self._appearance,
            spectral_lines=self._spectral_lines,
            parent=self
        )

        self.widgets[wt] = constructor(cfg=cfg, title=wt, **kwargs)
        self._connect_widget(wt)

    def _create_widgets(self):
        for wt in list(self.widgets):
            self._delete_widget(wt)

        for name, image_cfg in self._widget_cfg.images.items():
            self._create_widget(name, image_cfg)

        for name, plot_cfg in self._widget_cfg.plots.items():
            self._create_widget(name, plot_cfg)

        for plugin in self._plugins:
            plugin.override_widget_configs(self.widgets)

    def _delete_widget(self, wt: str):
        self._unlink_widget(wt)
        self._disconnect_widget(wt)

        w0 = self.widgets.pop(wt)

        w0.graphics_layout.clear()
        w0.deleteLater()

    def _connect_widget(self, wt: str):
        w0 = self.widgets[wt]

        self.project_loaded.connect(w0.load_project)
        self.data_loaded.connect(w0.load_object)
        self.view_reset.connect(w0.reset_view)
        self.spectral_lines_changed.connect(w0.update_spectral_lines)

        w0.object_loaded.connect(self._attach_widget)
        w0.object_destroyed.connect(self._detach_widget)
        w0.redshift_slider.save_button_clicked.connect(self._save_redshift)

    def _disconnect_widget(self, wt: str):
        w0 = self.widgets[wt]

        self.project_loaded.disconnect(w0.load_project)
        self.data_loaded.disconnect(w0.load_object)
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

        for w in self.widgets.values():
            for linked_item, linker in self._widget_linkers.items():
                linker.unlink(w0, w, self._widget_links[linked_item])
                linker.unlink(w, w0, self._widget_links[linked_item])

    def _close_dock(self, dt: str, dock: Dock | None = None):
        if dock is None:
            dock = self.docks[dt]

        container = dock.container()
        dock.close()

        if container and not isinstance(container, DockArea):
            self._close_dock(dt, container)
        else:
            self._added_docks.remove(dt)
            self.docks.pop(dt)
            return

    def _create_dock(self, dt: str):
        w0 = self.widgets[dt]
        self.docks[dt] = Dock(dt, widget=w0)
        self._add_dock(dt)

    def _add_dock(self, dt: str):
        dock, w0 = self.docks[dt], self.widgets[dt]
        if not w0.cfg.visible:
            return

        position = w0.cfg.position if w0.cfg.position is not None else 'bottom'
        relative_to = w0.cfg.relative_to if w0.cfg.relative_to in self._added_docks else None

        self.dock_area.addDock(dock=dock, position=position, relativeTo=relative_to)
        self._update_visibility(dt)
        self._added_docks.append(dt)

    def _create_docks(self):
        for dt in list(self.docks):
            self._close_dock(dt)

        for wt in self.widgets:
            self._create_dock(wt)

        for plugin in self._plugins:
            plugin.update_docks(self.docks)

    @QtCore.Slot()
    def reset_dock_layout(self):
        self._create_docks()

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
        self._lock = True
        self.setEnabled(True)
        self.project_loaded.emit()

    @QtCore.Slot(int, InspectionData, object)
    def load_object(self, j: int, review: InspectionData, cat_entry: Catalog | None):
        if self._worker and self._worker.isRunning():
            self._worker.wait()

        self._t_worker_start = time.perf_counter()
        t_grace = self._get_t_grace()
        self._t_old_worker_start = self._t_worker_start

        self._worker = ViewerDataLoader(self.widgets, j, review, self._data, self._data_cfg, cat_entry, t_grace=t_grace)
        self.loading_aborted.connect(self._worker.abort)
        self._worker.finished.connect(self.finalize_loading)
        self._worker.start()

        if self._lock:
            self._worker.wait()

    @QtCore.Slot()
    def abort_loading(self):
        if self._worker and self._worker.isRunning():
            self._worker.finished.disconnect(self.finalize_loading)

        self.loading_aborted.emit()

    def _get_t_grace(self):
        dt = 1000 if self._t_old_worker_start is None else self._t_worker_start - self._t_old_worker_start
        t_grace = 0.35 if 0.10 < dt < 0.35 else 0.10
        return t_grace

    @QtCore.Slot()
    def finalize_loading(self):
        j, review, cat_entry = self._worker.j, self._worker.review, self._worker.cat_entry

        self.data_loaded.emit(j, review, cat_entry)

        for plugin in self._plugins:
            plugin.update_active_widgets(self.active_widgets, cat_entry=cat_entry)
            plugin.update_docks(self.docks, cat_entry=cat_entry)

        self.reset_view()

        self._lock = False
        self.object_loaded.emit()

    @QtCore.Slot(str)
    def _attach_widget(self, wt: str):
        w0 = self.widgets[wt]
        self._link_widget(wt)
        self.docks[wt].setTitle(w0.get_dock_title())
        logger.debug(f"`{wt}` attached to the viewer")

    @QtCore.Slot(str)
    def _detach_widget(self, wt: str):
        w0 = self.widgets[wt]
        self._unlink_widget(wt)
        self.docks[wt].setTitle(w0.title)
        logger.debug(f"`{wt}` detached from the viewer")

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

    def _change_redshift(self, n_steps: int, small_step: bool = False):
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

    @QtCore.Slot(bool)
    def enter_zen_mode(self, is_zen: bool):
        self._zen_mode_activated = is_zen
        for wt in self.widgets:
            self._update_visibility(wt)

    def _update_visibility(self, wt: str):
        w0 = self.widgets[wt]
        dock = self.docks[wt]

        if self._zen_mode_activated:
            dock.hideTitleBar()
        else:
            dock.showTitleBar()

        self.visibility_changed.connect(w0.update_visibility)
        self.visibility_changed.emit(self._zen_mode_activated)
        self.visibility_changed.disconnect(w0.update_visibility)

    @QtCore.Slot()
    def free_resources(self):
        self._data.close_all()
