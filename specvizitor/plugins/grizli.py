import astropy.units as u
from qtpy import QtGui

from ..widgets.ViewerElement import ViewerElement
from ..widgets.Image2D import Image2D
from ..widgets.Spec1D import Spec1D


class Plugin:
    # TODO: create BasePlugin
    @staticmethod
    def link(widgets: dict[str, ViewerElement], label_style: dict[str, str] | None = None):

        try:
            spec_1d_widget: Spec1D = widgets["Spectrum 1D"]
            spec_2d_widget: Image2D = widgets["Spectrum 2D"]
        except KeyError:
            return

        if any(w.data is None for w in (spec_1d_widget, spec_2d_widget)):
            return

        # set x-axis transformation for the 2D spectrum plot
        scale = u.Unit('micron') / spec_1d_widget.spec_1d.spec.spectral_axis.unit

        dlam = spec_2d_widget.meta['CD1_1'] * scale
        crval = spec_2d_widget.meta['CRVAL1'] * scale
        crpix = spec_2d_widget.meta['CRPIX1']

        qtransform = QtGui.QTransform().translate(crval - dlam * crpix, 0).scale(dlam, 1)

        spec_2d_widget.image_2d.setTransform(qtransform)
        spec_2d_widget._container.setAspectLocked(True, 1 / dlam)
        if label_style is None:
            label_style = {}
        spec_2d_widget._container.setLabel('bottom', spec_1d_widget.spec_1d.spec.spectral_axis.unit, **label_style)
        spec_2d_widget._container.setXLink(spec_1d_widget.title)  # link the x-axis range
