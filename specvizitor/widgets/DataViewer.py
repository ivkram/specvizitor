from qtpy import QtGui

from .AbstractWidget import AbstractWidget
from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D

from ..runtime.appdata import AppData
from ..runtime import config
from ..utils.widgets import get_widgets


class DataViewer(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.Viewer, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        self.layout.setSpacing(10)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create widgets for images (image cutout, 2D spectrum, etc.)
        self.images = {}
        for name, image_cfg in cfg.images.items():
            self.images[name] = Image2D(rd=rd, cfg=image_cfg, name=name, parent=self)

        # create widgets for 1D spectra
        self.spectra = {}
        for name, spec_cfg in cfg.spectra.items():
            self.spectra[name] = Spec1D(rd=rd, cfg=spec_cfg, name=name, parent=self)

        self.init_ui()

    def init_ui(self):
        for i, image in enumerate(self.images.values()):
            self.layout.addWidget(image, i + 1, 1, 1, 1)

        for i, spectrum in enumerate(self.spectra.values()):
            self.layout.addWidget(spectrum, i + len(self.images) + 1, 1, 1, 1)

    @property
    def widgets(self) -> list[ViewerElement]:
        """
        @return: a list of widgets added to the data viewer.
        """
        return get_widgets(self.layout)

    def load_object(self):
        for w in self.widgets:
            w.load_object()

        # DLAM = 1
        # if all(x is not None for x in (self.spec_2d.cfg.link, self.spec_1d._data, self.spec_1d._data)):
        #     # set x-axis transformation for the 2D spectrum plot
        #     DLAM = self.spec_2d._hdu.header['CD1_1'] * 1e4
        #     CRVAL = self.spec_2d._hdu.header['CRVAL1'] * 1e4
        #     CRPIX = self.spec_2d._hdu.header['CRPIX1']
        #     qtransform = QtGui.QTransform(DLAM, 0, 0,
        #                                   0, 1, 0,
        #                                   CRVAL - DLAM * CRPIX, 0, 1)
        #     self.spec_2d._image_2d.setTransform(qtransform)
        #
        #     self.spec_2d._image_2d_plot.setXLink(self.spec_2d.cfg.link)  # link the x-axis range

        # self.spec_2d._image_2d_plot.setAspectLocked(True, 1 / DLAM)

        for image in self.images.values():
            image.image_2d_plot.setAspectLocked(True)

    def reset_view(self):
        for w in self.widgets:
            w.reset_view()
