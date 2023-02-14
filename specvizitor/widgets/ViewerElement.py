from astropy.utils.decorators import lazyproperty

from .AbstractWidget import AbstractWidget

from ..runtime import RuntimeData
from ..utils import params
from ..io.viewer_data import get_filename


class ViewerElement(AbstractWidget):
    def __init__(self, rd: RuntimeData, cfg: params.ViewerElement, parent=None):
        super().__init__(rd=rd, cfg=cfg, parent=parent)

    @lazyproperty
    def _filename(self):
        return get_filename(self.rd.config.loader.data.dir, self.cfg.search_mask, self.rd.id)

    def reset_view(self):
        pass

    def load_object(self):
        del self._filename
