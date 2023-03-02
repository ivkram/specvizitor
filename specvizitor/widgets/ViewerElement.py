import logging
import abc

from astropy.utils import lazyproperty
from astropy.io import fits
from astropy.table import Table

from .AbstractWidget import AbstractWidget

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.viewer_data import get_filename
from ..utils import misc


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
    def hdul(self):
        try:
            hdul = fits.open(self.filename)
        except ValueError:
            logger.warning('{} not found (object ID: {})'.format(self.name, self.rd.id))
            return
        else:
            return hdul

    @lazyproperty
    def hdu(self):
        if self.hdul is None:
            return
        elif self.cfg.ext_name is not None and self.cfg.ext_ver is None:
            index = self.cfg.ext_name
        elif self.cfg.ext_name is not None and self.cfg.ext_ver is not None:
            index = (self.cfg.ext_name, self.cfg.ext_ver)
        else:
            index = 1

        try:
            return self.hdul[index]
        except KeyError:
            logger.error(f'Extension `{index}` not found (object ID: {self.rd.id})')
            return

    @lazyproperty
    def data(self):
        if self.hdu is None:
            return
        else:
            data = self.hdu.data

        if self.hdu.header['XTENSION'] in ('TABLE', 'BINTABLE'):
            data = Table(data)
            translate = self.rd.config.loader.data.translate

            if translate:
                misc.translate(data, translate)

            for cname in ('wavelength', 'flux'):
                if cname not in data.colnames:
                    logger.error(misc.column_not_found_message(cname, translate))
                    return

        return data

    @abc.abstractmethod
    def reset_view(self):
        pass

    def load_object(self):
        del self.filename
        del self.hdul
        del self.hdu
        del self.data
