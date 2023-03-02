from qtpy import QtGui

from ..widgets.ViewerElement import ViewerElement


class Plugin:
    # TODO: create BasePlugin
    @staticmethod
    def link(widgets: dict[str, ViewerElement]):

        try:
            spec_1d, spec_2d = widgets["Spectrum 1D"], widgets["Spectrum 2D"]
        except KeyError:
            return

        if any(w.data is None for w in (spec_1d, spec_2d)):
            return

        # set x-axis transformation for the 2D spectrum plot
        DLAM = spec_2d.meta['CD1_1'] * 1e4
        CRVAL = spec_2d.meta['CRVAL1'] * 1e4
        CRPIX = spec_2d.meta['CRPIX1']

        qtransform = QtGui.QTransform().translate(CRVAL - DLAM * CRPIX, 0).scale(DLAM, 1)

        spec_2d.image_2d.setTransform(qtransform)
        spec_2d.image_2d_plot.setAspectLocked(True, 1 / DLAM)
        spec_2d.image_2d_plot.setXLink(spec_1d.alias)  # link the x-axis range
