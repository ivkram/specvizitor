import astropy.units as u
import pyqtgraph as pg
from qtpy import QtGui

from specvizitor.plugins.plugin_core import PluginCore
from specvizitor.widgets.ViewerElement import ViewerElement
from specvizitor.widgets.Image2D import Image2D
from specvizitor.widgets.Spec1D import Spec1D
from specvizitor.widgets.Plot1D import Plot1D


class Plugin(PluginCore):
    def invoke(self, widgets: dict[str, ViewerElement]):
        spec_1d: Spec1D | None = widgets.get("Spectrum 1D")
        spec_2d: Image2D | None = widgets.get("Spectrum 2D")
        z_pdf: Plot1D | None = widgets.get("Redshift PDF")

        if spec_2d is not None:
            line = self.add_central_line_to_spec2d(spec_2d)
            spec_2d.register_item(line)

            if spec_1d is not None:
                qtransform = self.transform_spec2d(spec_1d, spec_2d)
                line.setTransform(qtransform)
                self.link_spec1d_to_spec2d(spec_1d, spec_2d)
                spec_1d.reset_view()
            else:
                self.reset_spec2d_transform(spec_2d)
                self.unlink(spec_2d)
                spec_2d.reset_view()

        if spec_1d is not None and z_pdf is not None:
            self.add_current_redshift_line_to_z_pdf(spec_1d, z_pdf)

    @staticmethod
    def transform_spec2d(spec_1d: Spec1D, spec_2d: Image2D) -> QtGui.QTransform:
        scale = u.Unit('micron') / spec_1d.plot_1d.data.x.unit

        dlam = spec_2d.meta['CD1_1'] * scale
        crval = spec_2d.meta['CRVAL1'] * scale
        crpix = spec_2d.meta['CRPIX1']

        qtransform = QtGui.QTransform().translate(crval - dlam * crpix, 0).scale(dlam, 1)

        spec_2d.image_2d.setTransform(qtransform)
        spec_2d.container.setAspectLocked(True, 1 / dlam)

        return qtransform

    @staticmethod
    def reset_spec2d_transform(spec_2d: Image2D):
        spec_2d.image_2d.resetTransform()
        spec_2d.container.setAspectLocked(True, 1)

    @staticmethod
    def link_spec1d_to_spec2d(spec_1d: Spec1D, spec_2d: Image2D):
        spec_2d.container.setXLink(spec_1d.title)

    @staticmethod
    def unlink(spec_2d: Image2D):
        spec_2d.container.setXLink(None)

    @staticmethod
    def add_central_line_to_spec2d(spec_2d: Image2D) -> pg.PlotCurveItem:
        y = spec_2d.meta['NAXIS2'] / 2
        pen = 'w'

        line = pg.PlotCurveItem([0, spec_2d.meta['NAXIS1']], [y, y], pen=pen)
        spec_2d.container.addItem(line)

        return line

    @staticmethod
    def add_current_redshift_line_to_z_pdf(spec_1d: Spec1D, z_pdf: Plot1D):
        line = pg.InfiniteLine(spec_1d.z_slider.value, pen='r')
        spec_1d.redshift_changed.connect(lambda z: line.setPos(z))
        z_pdf.plot_1d.addItem(line)
