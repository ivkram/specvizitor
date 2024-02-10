from astropy.table import Row
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from qtpy import QtWidgets, QtCore

from functools import partial
import logging
import pathlib

from ..config import config
from ..config.data_widgets import DataWidgets
from ..config.spectral_lines import SpectralLineData
from ..io.inspection_data import InspectionData
from ..io.viewer_data import get_filenames_from_id, load_image, FieldImage, REQUESTS
from ..plugins.plugin_core import PluginCore
from ..utils.widgets import AbstractWidget

from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Plot1D import Plot1D

logger = logging.getLogger(__name__)


class DataViewer(AbstractWidget):
    object_selected = QtCore.Signal(int, InspectionData, object, list)
    shared_resources_queried = QtCore.Signal(str, pathlib.Path, object, object)
    view_reset = QtCore.Signal()
    data_collected = QtCore.Signal(dict)
    redshift_fixed = QtCore.Signal(float)

    zen_mode_activated = QtCore.Signal()
    visibility_changed = QtCore.Signal()

    def __init__(self,
                 viewer_cfg: DataWidgets,
                 appearance: config.Appearance,
                 images: dict[str, config.Image] | None = None,
                 spectral_lines: SpectralLineData | None = None,
                 plugins: list[PluginCore] | None = None,
                 parent=None):

        self._appearance = appearance
        self._viewer_cfg = viewer_cfg
        self._spectral_lines = spectral_lines
        self._plugins: list[PluginCore] = plugins if plugins is not None else []

        # images that are shared between widgets and can be used to create cutouts
        self._field_images: dict[str, FieldImage] = {}

        self._field_images_cfg: dict[str, config.Data.images] = images if images else {}
        self.load_field_images()

        self.dock_area: DockArea | None = None
        self.added_docks: list[str] = []

        self.core_widgets: dict[str, ViewerElement] = {}
        self.docks: dict[str, Dock] = {}

        super().__init__(parent=parent)
        self.setEnabled(False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    @property
    def widgets(self) -> list[ViewerElement]:
        lazy_widgets = []
        for w in self.core_widgets.values():
            lazy_widgets.extend(w.lazy_widgets)

        return list(self.core_widgets.values()) + lazy_widgets

    @property
    def active_core_widgets(self) -> dict[str, ViewerElement]:
        return {title: w for title, w in self.core_widgets.items() if w.data is not None}

    def _create_widgets(self):
        # delete previously created widgets
        if self.widgets:
            # disconnect signals
            self.object_selected.disconnect()
            self.zen_mode_activated.disconnect()
            self.visibility_changed.disconnect()
            self.shared_resources_queried.disconnect()
            try:
                self.view_reset.disconnect()
            except TypeError:
                pass

            for w in self.widgets:
                w.shared_resource_requested.disconnect()
                w.graphics_layout.clear()
                w.deleteLater()

        widgets = {}

        # create widgets for images (e.g. image cutouts, 2D spectra)
        if self._viewer_cfg.images is not None:
            for name, image_cfg in self._viewer_cfg.images.items():
                widgets[name] = Image2D(cfg=image_cfg, title=name, appearance=self._appearance,
                                        spectral_lines=self._spectral_lines, parent=self)

        # create widgets for plots, including 1D spectra
        if self._viewer_cfg.plots is not None:
            for name, plot_cfg in self._viewer_cfg.plots.items():
                widgets[name] = Plot1D(cfg=plot_cfg, title=name, appearance=self._appearance,
                                       spectral_lines=self._spectral_lines, parent=self)

        self._connect_widgets(widgets)

        for plugin in self._plugins:
            plugin.overwrite_widget_configs(widgets)

        self.core_widgets = widgets

    def _connect_widgets(self, widgets: dict[str, ViewerElement]):
        for w in widgets.values():
            self.object_selected.connect(w.load_object)
            self.zen_mode_activated.connect(w.hide_interface)
            self.visibility_changed.connect(w.update_visibility)
            self.shared_resources_queried.connect(w.get_shared_resource)

            w.shared_resource_requested.connect(self._query_shared_resources)
            w.redshift_slider.save_button_clicked.connect(self._save_redshift)

        for w in widgets.values():
            # link view(s)
            # TODO: throw a warning if two axes have different unit/scale
            if w.cfg.x_axis.link_to:
                w.container.setXLink(w.cfg.x_axis.link_to)
            if w.cfg.y_axis.link_to:
                w.container.setYLink(w.cfg.y_axis.link_to)

            # link sliders
            for slider_name, slider in w.sliders.items():
                if slider.link_to is not None:
                    try:
                        source_slider = widgets[slider.link_to].sliders[slider_name]
                    except KeyError:
                        logger.error(f'Failed to link sliders (source widget: {slider.link_to}, slider: {slider_name})')
                    else:
                        source_slider.value_changed[float].connect(slider.set_value)
                        slider.value_changed[float].connect(source_slider.set_value)

        images: dict[str, Image2D] = {title: w for title, w in widgets.items() if isinstance(w, Image2D)}
        for w in images.values():
            if w.cfg.color_bar.link_to is not None:
                try:
                    source_widget = widgets[w.cfg.color_bar.link_to]
                except KeyError:
                    logger.error(f'Failed to link color bars (source widget: {w.cfg.color_bar.link_to})')
                else:
                    source_widget.cbar.sigLevelsChanged[tuple].connect(partial(w.set_default_levels, update=True))
                    w.cbar.sigLevelsChanged[tuple].connect(partial(source_widget.set_default_levels, update=True))

    def _create_docks(self):
        # delete previously created docks
        docks = list(self.docks.values())
        if len(docks) == 1:
            docks[0].close()
        else:
            for d in docks[:-1]:
                # pyqtgraph bug: d.close() would leave a floating TContainer (created when docks are stacked)
                d.container().close()

        docks = {}
        for widget in self.widgets:
            docks[widget.title] = Dock(widget.title, widget=widget)

        self.docks = docks

    def _add_dock(self, widget: ViewerElement):
        position = widget.cfg.position if widget.cfg.position is not None else 'bottom'
        relative_to = widget.cfg.relative_to if widget.cfg.relative_to in self.added_docks else None

        self.dock_area.addDock(dock=self.docks[widget.title],
                               position=position,
                               relativeTo=relative_to)
        self.added_docks.append(widget.title)

    def _add_docks(self):
        self.added_docks = []

        for widget in self.widgets:
            if widget.cfg.visible:
                self._add_dock(widget)

        for plugin in self._plugins:
            plugin.tweak_docks(self.docks)

    @QtCore.Slot()
    def init_docks(self):
        self._create_docks()
        self._add_docks()
        self._update_dock_titles()

    @QtCore.Slot(dict)
    def restore_dock_layout(self, layout: dict):
        try:
            # set `extra` to None to catch an exception (KeyError) when adding extra docks not mentioned in `layout`
            self.dock_area.restoreState(layout, missing='ignore', extra=None)
            logger.info('Dock layout restored')

            for plugin in self._plugins:
                plugin.tweak_docks(self.docks)

        except (KeyError, ValueError, TypeError):
            self.init_docks()  # to reset the dock layout
            logger.error('Failed to restore the dock layout')

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
        self._viewer_cfg = viewer_cfg
        self.init_ui()

    @QtCore.Slot(dict)
    def load_field_images(self):
        for img_label, img_cfg in self._field_images_cfg.items():
            data, meta = load_image(filename=img_cfg.filename, loader=img_cfg.loader, widget_title='Data Viewer',
                                    wcs_source=img_cfg.wcs_source, **(img_cfg.loader_params or {}))
            if data is None:
                continue

            self._field_images[img_label] = FieldImage(pathlib.Path(img_cfg.filename), data, meta)

    @QtCore.Slot(str, REQUESTS, dict)
    def _query_shared_resources(self, widget_title: str, request: REQUESTS, request_params: dict):
        if request == REQUESTS.CUTOUT:
            label = request_params.get('image')
            if label not in self._field_images:
                logger.error(f'Shared image not found (label: {label})')
                return

            img = self._field_images[label]

            cutout_size = request_params.get('cutout_size')
            if cutout_size:
                ra, dec = request_params.get('ra'), request_params.get('dec')
                data = img.create_cutout(cutout_size, ra=ra, dec=dec)
                if data is not None:
                    self._share_resource(widget_title, img.filename, data, img.meta)
                return

            self._share_resource(widget_title, img.filename, img.data, img.meta)

    def _share_resource(self, widget_title, *args):
        w = self.core_widgets.get(widget_title)
        if w is None:
            logger.error(f'Failed to share the resource: Widget `{widget_title}` not found')
            return

        self.shared_resources_queried.emit(w.title, *args)

    @QtCore.Slot()
    def load_project(self):
        self.setEnabled(True)

    @QtCore.Slot(int, InspectionData, object, config.Data)
    def load_object(self, j: int, review: InspectionData, obj_cat: Row | None, data_cfg: config.Data):
        # perform search for files containing the object ID in their filename
        discovered_data_files = get_filenames_from_id(data_cfg.dir, review.get_id(j))

        # load the object data to the widgets
        self.object_selected.emit(j, review, obj_cat, discovered_data_files)

        # connecting the `view_reset` signal to activate core widgets
        try:
            self.view_reset.disconnect()
        except TypeError:
            pass
        for w in self.active_core_widgets.values():
            self.view_reset.connect(w.reset_view)

        self._update_dock_titles()

        for plugin in self._plugins:
            plugin.tweak_widgets(self.active_core_widgets, obj_cat)

    @QtCore.Slot(float)
    def _save_redshift(self, redshift: float):
        self.redshift_fixed.emit(redshift)

    @QtCore.Slot()
    def collect(self):
        self.data_collected.emit(self.dock_area.saveState())

    @QtCore.Slot(str)
    def take_screenshot(self, filename: str):
        self.grab().save(filename)

    def _update_dock_titles(self):
        for core_widget in self.core_widgets.values():
            if core_widget.filename is not None and core_widget.meta is not None:
                title = core_widget.filename.name

                # adding EXTNAME and EXTVER to the dock title
                fits_meta = core_widget.meta.get('EXTNAME'), core_widget.meta.get('EXTVER')
                j = 0
                while j < len(fits_meta) and fits_meta[j] is not None:
                    j += 1
                title_extra = ', '.join(map(str, fits_meta[:j]))

                if title_extra:
                    if core_widget.cfg.dock_title_fmt == 'short':
                        title = title_extra  # str(fits_meta[j - 1])
                    else:
                        title += f' [{title_extra}]'

                for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                    self.docks[w.title].setTitle(title)

            else:
                for w in (core_widget,) + tuple(core_widget.lazy_widgets):
                    self.docks[w.title].setTitle(w.title)

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

