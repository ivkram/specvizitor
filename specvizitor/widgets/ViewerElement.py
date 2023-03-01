import logging
import abc

from astropy.utils import lazyproperty
from astropy.io import fits

from .AbstractWidget import AbstractWidget

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.viewer_data import get_filename


logger = logging.getLogger(__name__)


class ViewerElement(AbstractWidget, abc.ABC):
    def __init__(self, rd: AppData, cfg: config.ViewerElement, name: str, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.rd = rd
        self.cfg = cfg
        self.name = name

        self.layout.setContentsMargins(0, 0, 0, 0)

    @lazyproperty
    def filename(self):
        return get_filename(self.rd.config.loader.data.dir, self.cfg.filename_pattern, self.rd.id)

    @lazyproperty
    def _hdul(self):
        try:
            hdul = fits.open(self.filename)
        except ValueError:
            logger.warning('{} not found (object ID: {})'.format(self.name, self.rd.id))
            return
        else:
            return hdul

    @lazyproperty
    def _hdu(self):
        if self._hdul is None:
            return
        elif self.cfg.ext_name is not None and self.cfg.ext_ver is None:
            return self._hdul[self.cfg.ext_name]
        elif self.cfg.ext_name is not None and self.cfg.ext_ver is not None:
            return self._hdul[self.cfg.ext_name, self.cfg.ext_ver]
        else:
            return self._hdul[1]

    @lazyproperty
    def _data(self):
        return self._hdu.data if self._hdu is not None else None

    @abc.abstractmethod
    def reset_view(self):
        pass

    def load_object(self):
        del self.filename
        del self._hdul
        del self._hdu
        del self._data
