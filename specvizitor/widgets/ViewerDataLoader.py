from qtpy import QtCore

import logging
import pathlib
import time

from ..config import config
from ..io.catalog import Catalog
from ..io.inspection_data import InspectionData
from ..io.viewer_data import ViewerData, LocalPath

from .ViewerElement import ViewerElement


__all__ = [
    "ViewerDataLoader"
]

logger = logging.getLogger(__name__)


class ViewerDataLoader(QtCore.QThread):
    data_loaded = QtCore.Signal(object, object, object)

    def __init__(self, widgets: dict[str, ViewerElement], j: int, review: InspectionData, viewer_data: ViewerData,
                 data_sources: config.DataSources, cat_entry: Catalog | None, t_grace=0.1):
        super().__init__(parent=None)

        self.widgets: dict[str, ViewerElement] = widgets
        
        self.j: int = j
        self.review: InspectionData = review
        self.data_sources: config.DataSources = data_sources
        self.cat_entry: Catalog | None = cat_entry
        self.viewer_data = viewer_data

        self.t_grace = t_grace
        
        self._runs = True

    def run(self):
        i = 0
        n = 30
        dt = self.t_grace / n
        while self._runs and i < n:
            time.sleep(dt)
            i += 1

        if i < n:
            return

        widgets = list(self.widgets.values())

        i = 0
        n = len(widgets)
        while self._runs and i < n:
            w0 = widgets[i]
            res = self._load_data(w0)
            if res is None:
                res = (None, None, None)
            self.data_loaded.connect(w0.set_data)
            self.data_loaded.emit(*res)
            self.data_loaded.disconnect(w0.set_data)
            i += 1

    @QtCore.Slot()
    def abort(self):
        self._runs = False
    
    def _load_data(self, w0: ViewerElement):
        if w0.data is not None:
            self._free_resources(w0)
        
        data_path = self._get_data_path(w0)
        if data_path is None:
            return None

        try:
            data_path.resolve(self.review.get_id(self.j), self.cat_entry)
        except Exception as e:
            logger.error(f"Failed to resolve the filename: {e} (widget: {w0.title})")
            return None

        try:
            data_path.validate()
        except FileNotFoundError:
            logger.error(f"`{w0.title}` not found (filename: {data_path.name})")
            return None
        except Exception as e:
            logger.error(f"{e} (widget: {w0.title})")
            return None

        loader_params = self._get_loader_params(w0)
        if loader_params is None:
            return None

        data, meta = self.viewer_data.load(str(data_path),
                                           loader=w0.cfg.data.loader,
                                           allowed_dtypes=w0.allowed_data_types,
                                           **loader_params)

        return data, meta, data_path

    def _free_resources(self, w0: ViewerElement):
        if not w0.cfg.data.source:
            self.viewer_data.close(str(w0.data_path))
            return

        self.viewer_data.reopen(str(w0.data_path))

    def _get_data_path(self, w0: ViewerElement) -> LocalPath | None:
        if not w0.cfg.data.source:
            if not w0.cfg.data.filename:
                logger.error(f"Filename not specified (widget: {w0.title})")
                return
            return LocalPath(str(pathlib.Path(self.data_sources.dir) / w0.cfg.data.filename))

        # for now assume that a non-empty data source == image
        image = self.data_sources.images.get(w0.cfg.data.source)
        if not image:
            logger.error(f"Shared image not found (label: {w0.cfg.data.source}, widget: {w0.title})")
            return

        return LocalPath(image.filename)

    def _get_loader_params(self, w0: ViewerElement) -> dict | None:
        params = w0.cfg.data.loader_params

        if not w0.cfg.data.source:
            return params

        if self.cat_entry is None:
            logger.error(f"Failed to create an image cutout: Catalog entry not loaded (widget: {w0.title})")
            return None

        image = self.data_sources.images.get(w0.cfg.data.source)
        if not image:
            logger.error(f"Shared image not found (label: {w0.cfg.data.source}, widget: {w0.title})")
            return None

        wcs_source = image.wcs_source if image.wcs_source else image.filename
        cutout_params = self._get_cutout_params(wcs_source)
        if cutout_params is None:
            return None

        params.update(cutout_params)

        return params

    def _get_cutout_params(self, wcs_source: str) -> dict | None:
        params = dict(create_cutout=True)

        try:
            ra = self.cat_entry.get_col('ra')
            dec = self.cat_entry.get_col('dec')
        except KeyError as e:
            logger.error(e)
            return None

        _, meta = self.viewer_data.load(wcs_source, lazy=True, create_wcs=True)
        if meta is None:
            return

        try:
            x0, y0 = meta.wcs.all_world2pix(ra, dec, 0)
        except Exception as e:
            logger.error(f"Calculation of pixel coordinates failed: {e} (image: {wcs_source})")
            return None
        params.update(x0=x0, y0=y0)

        return params