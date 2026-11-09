import logging
import pathlib
import threading
import time
from dataclasses import dataclass

from qtpy import QtCore

from astropy.coordinates import SkyCoord

from ..config import config, data_widgets
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..io.viewer_data import LocalPath, ViewerData, get_wcs
from .ViewerElement import ViewerElement

__all__ = [
    "LoadTask",
    "LoaderState",
    "ViewerDataLoader"
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadTask:
    """ What a loader needs to know of a widget, taken on the main thread: the loader never touches the widget, which
    the main thread may delete in the meantime.
    """
    title: str
    cfg: data_widgets.ViewerElement  # shared with the widget, only read here (copying it costs ~3 ms per object)
    widget_type: type[ViewerElement]

    @property
    def allowed_data_types(self) -> tuple[type, ...]:
        return self.widget_type.allowed_data_types

    def prepare_data(self, data, meta) -> dict:
        return self.widget_type.prepare_data(self.cfg, data, meta)


class LoaderState:
    """ Shared by the loaders of one viewer, which use the same files. An aborted loader still finishes the widget it
    is loading: the next one waits for it on the lock, in its own thread rather than the main thread, and learns from
    `open_files` which file to close, since the data of an aborted loader is dropped.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.open_files: dict[str, str] = {}  # widget title -> the file its data was last loaded from


class ViewerDataLoader(QtCore.QThread):
    data_loaded = QtCore.Signal(object, str, object, object, object, object)  # title, data, meta, data path, prepared
    # QThread.finished, but telling which loader finished: emitted however run() ends
    done = QtCore.Signal(object)

    def __init__(self, tasks: list[LoadTask], j: int, inspection_data: InspectionData,
                 viewer_data: ViewerData, data_sources: config.DataSources, cat_entry: Catalog | None, t_grace=0.1,
                 state: LoaderState | None = None):
        super().__init__(parent=None)

        self.tasks: list[LoadTask] = tasks

        self.j: int = j
        self.inspection_data: InspectionData = inspection_data
        self.data_sources: config.DataSources = data_sources
        self.cat_entry: Catalog | None = cat_entry
        self.viewer_data = viewer_data

        self.t_grace = t_grace

        self._state = state if state is not None else LoaderState()

        self._runs = True

    def run(self):
        try:
            self._run()
        finally:
            self.done.emit(self)

    def _run(self):
        i = 0
        n = 30
        dt = self.t_grace / n
        while self._runs and i < n:
            time.sleep(dt)
            i += 1

        if i < n:
            return

        with self._state.lock:
            for task in self.tasks:
                if not self._runs:
                    break
                res = self._load_data(task)
                if res is None:
                    res = (None, None, None, None)
                self.data_loaded.emit(self, task.title, *res)

    @property
    def aborted(self) -> bool:
        return not self._runs

    @QtCore.Slot()
    def abort(self):
        self._runs = False
    
    def _load_data(self, task: LoadTask):
        self._free_resources(task)

        data_path = self._get_data_path(task)
        if data_path is None:
            return None

        try:
            data_path.resolve(self.inspection_data.get_id(self.j), self.cat_entry)
        except Exception as e:
            logger.error(f"Failed to resolve the filename: {e} (widget: {task.title})")
            return None

        try:
            data_path.validate()
        except FileNotFoundError:
            logger.error(f"`{task.title}` not found (filename: {data_path.name})")
            return None
        except Exception as e:
            logger.error(f"{e} (widget: {task.title})")
            return None

        loader_params = self._get_loader_params(task)
        if loader_params is None:
            return None

        data, meta = self.viewer_data.load(str(data_path),
                                           loader=task.cfg.data.loader,
                                           allowed_dtypes=task.allowed_data_types,
                                           **loader_params)

        prepared = None
        if data is not None:
            self._state.open_files[task.title] = str(data_path)
            try:
                prepared = task.prepare_data(data, meta)
            except Exception as e:
                logger.error(f"Failed to prepare the data: {e} (widget: {task.title})")

        return data, meta, data_path, prepared

    def _free_resources(self, task: LoadTask):
        filename = self._state.open_files.pop(task.title, None)
        if filename is None:
            return

        if not task.cfg.data.source:
            self.viewer_data.close(filename)
            return

        self.viewer_data.reopen(filename)

    def _get_data_path(self, task: LoadTask) -> LocalPath | None:
        if not task.cfg.data.source:
            if not task.cfg.data.filename:
                logger.error(f"Filename not specified (widget: {task.title})")
                return None
            if not self.data_sources.dir:
                logger.error(f"Data directory not set for this workspace (widget: {task.title})")
                return None
            return LocalPath(str(pathlib.Path(self.data_sources.dir) / task.cfg.data.filename))

        # for now assume that a non-empty data source == image
        image = self.data_sources.images.get(task.cfg.data.source)
        if not image:
            logger.error(f"Shared image not found (label: {task.cfg.data.source}, widget: {task.title})")
            return None

        if not image.filename:
            logger.error(f"Image path not set for this workspace "
                         f"(image: {task.cfg.data.source}, widget: {task.title})")
            return None

        return LocalPath(image.filename)

    def _get_loader_params(self, task: LoadTask) -> dict | None:
        # a copy: the cutout parameters below are recomputed per object and must not leak into
        # the widget configuration, which is persisted and shared
        params = dict(task.cfg.data.loader_params)

        if not task.cfg.data.source:
            return params

        if self.cat_entry is None:
            logger.error(f"Failed to create an image cutout: Catalog entry not loaded (widget: {task.title})")
            return None

        image = self.data_sources.images.get(task.cfg.data.source)
        if not image:
            logger.error(f"Shared image not found (label: {task.cfg.data.source}, widget: {task.title})")
            return None

        wcs_source = image.wcs_source if image.wcs_source else image.filename
        if not wcs_source:
            logger.error(f"Image path not set for this workspace "
                         f"(image: {task.cfg.data.source}, widget: {task.title})")
            return None

        cutout_params = self._get_cutout_params(wcs_source)
        if cutout_params is None:
            return None

        params.update(cutout_params)

        return params

    def _get_cutout_params(self, wcs_source: str) -> dict | None:
        params = {"create_cutout": True}

        try:
            ra = self.cat_entry.get_col("ra")
            dec = self.cat_entry.get_col("dec")
        except KeyError as e:
            logger.error(e)
            return None

        _, meta = self.viewer_data.load(wcs_source, lazy=True, create_wcs=True)
        if meta is None:
            return None

        try:
            wcs = get_wcs(meta)
        except Exception as e:
            logger.error(f"Failed to create the WCS object: {e} (image: {wcs_source})")
            return None

        try:
            coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            x0, y0 = wcs.world_to_pixel(coord)
        except Exception as e:
            logger.error(f"Failed to calculate pixel coordinates of the cutout's center: {e} (image: {wcs_source})")
            return None

        params.update(x0=float(x0), y0=float(y0))

        return params