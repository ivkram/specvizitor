from qtpy import QtWidgets

from .AbstractWidget import AbstractWidget
from .ViewerElement import ViewerElement
from .ImageCutout import ImageCutout
from .Spec2D import Spec2D
from .Spec1D import Spec1D

from ..appdata.runtime import RuntimeData
from ..utils.widgets import get_widgets


class DataViewer(AbstractWidget):
    def __init__(self, rd: RuntimeData, parent=None):
        super().__init__(rd=rd, cfg=rd.config.viewer, parent=parent)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        # add a widget for the image cutout
        self.image_cutout = ImageCutout(self.rd, parent=self)
        grid.addWidget(self.image_cutout, 1, 1, 1, 1)

        # add a widget for the 2D spectrum
        self.spec_2D = Spec2D(self.rd, parent=self)
        grid.addWidget(self.spec_2D, 2, 1, 1, 1)

        # add a widget for the 1D spectrum
        self.spec_1D = Spec1D(self.rd, parent=self)
        grid.addWidget(self.spec_1D, 3, 1, 1, 1)

        self.setLayout(grid)

    @property
    def widgets(self) -> list[ViewerElement]:
        """
        @return: a list of widgets added to the data viewer.
        """
        return get_widgets(self.layout())

    def load_object(self):
        for w in self.widgets:
            w.load_object()

    def reset_view(self):
        for w in self.widgets:
            w.reset_view()
