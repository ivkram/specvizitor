from .AbstractWidget import AbstractWidget
from .ViewerElement import ViewerElement
from .ImageCutout import ImageCutout
from .Spec2D import Spec2D
from .Spec1D import Spec1D

from ..runtime.appdata import AppData
from ..utils.widgets import get_widgets


class DataViewer(AbstractWidget):
    def __init__(self, rd: AppData, parent=None):
        self.cfg = rd.config.viewer
        super().__init__(rd=rd, cfg=self.cfg, parent=parent)

        self.layout.setSpacing(10)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create a widget for the image cutout
        self.image_cutout = ImageCutout(self.rd, parent=self)

        # create a widget for the 2D spectrum
        self.spec_2D = Spec2D(self.rd, parent=self)

        # create a widget for the 1D spectrum
        self.spec_1D = Spec1D(self.rd, parent=self)

        self.init_ui()

    def init_ui(self):
        self.layout.addWidget(self.image_cutout, 1, 1, 1, 1)
        self.layout.addWidget(self.spec_2D, 2, 1, 1, 1)
        self.layout.addWidget(self.spec_1D, 3, 1, 1, 1)

    @property
    def widgets(self) -> list[ViewerElement]:
        """
        @return: a list of widgets added to the data viewer.
        """
        return get_widgets(self.layout)

    def load_object(self):
        for w in self.widgets:
            w.load_object()

    def reset_view(self):
        for w in self.widgets:
            w.reset_view()
