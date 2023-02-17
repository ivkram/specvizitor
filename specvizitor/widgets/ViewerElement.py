import logging

import numpy as np
from astropy.utils import lazyproperty
from astropy.io import fits

from .AbstractWidget import AbstractWidget

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.viewer_data import get_filename


logger = logging.getLogger(__name__)


class ViewerElement(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ViewerElement, parent=None):
        self.cfg = cfg

        super().__init__(rd=rd, cfg=cfg, parent=parent)
        self.layout.setContentsMargins(0, 0, 0, 0)

    @lazyproperty
    def _filename(self):
        return get_filename(self.rd.config.loader.data.dir, self.cfg.search_mask, self.rd.id)

    @lazyproperty
    def _hdul(self):
        try:
            hdul = fits.open(self._filename)
        except ValueError:
            logger.warning('{} not found (object ID: {})'.format(self.cfg.title, self.rd.id))
            return
        else:
            return hdul

    @lazyproperty
    def _hdu(self):
        return self._hdul[1] if self._hdul else None

    @lazyproperty
    def _data(self):
        if self._hdu is None:
            return

        data = self._hdu.data

        # rotate the image
        if self.cfg.rotate is not None:
            data = np.rot90(data, k=self.cfg.rotate // 90)

        return data

    def reset_view(self):
        pass

    def load_object(self):
        del self._filename
        del self._hdul
        del self._hdu
        del self._data
