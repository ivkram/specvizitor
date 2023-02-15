from astropy.utils import lazyproperty

from .AbstractWidget import AbstractWidget

from ..runtime.appdata import AppData
from ..runtime import config
from ..io.viewer_data import get_filename


class ViewerElement(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.ViewerElement, parent=None):
        super().__init__(rd=rd, cfg=cfg, parent=parent)

        self.layout.setContentsMargins(0, 0, 0, 0)

    @lazyproperty
    def _filename(self):
        return get_filename(self.rd.config.loader.data.dir, self.cfg.search_mask, self.rd.id)

    def reset_view(self):
        pass

    def load_object(self):
        del self._filename
