import importlib

from .AbstractWidget import AbstractWidget
from .ViewerElement import ViewerElement
from .Image2D import Image2D
from .Spec1D import Spec1D

from ..runtime.appdata import AppData
from ..runtime import config
from ..utils.widgets import get_widgets


class DataViewer(AbstractWidget):
    def __init__(self, rd: AppData, cfg: config.Viewer, plugins=None, parent=None):
        super().__init__(cfg=cfg, parent=parent)

        if plugins is not None:
            self._plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin() for plugin_name in plugins]
        else:
            self._plugins = []

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

    def init_ui(self):
        for i, image in enumerate(self.images.values()):
            self.layout.addWidget(image, i + 1, 1, 1, 1)
            image.init_ui()

        for i, spectrum in enumerate(self.spectra.values()):
            self.layout.addWidget(spectrum, i + len(self.images) + 1, 1, 1, 1)
            spectrum.init_ui()

    @property
    def widgets(self) -> list[ViewerElement]:
        """
        @return: a list of widgets added to the data viewer.
        """
        return get_widgets(self.layout)

    def load_object(self):
        for w in self.widgets:
            w.load_object()

        for plugin in self._plugins:
            plugin.link({w.name: w for w in self.widgets})

    def reset_view(self):
        for w in self.widgets:
            w.reset_view()
