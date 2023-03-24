from astropy.table import Table
from astropy.visualization import ZScaleInterval
import astropy.units as u
import numpy as np
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

        if spec_1d is not None:
            self.convert_spec1d_flux_units(spec_1d)
            spec_1d.reset_view()

    @staticmethod
    def transform_spec2d(spec_1d: Spec1D, spec_2d: Image2D) -> QtGui.QTransform:
        scale = (1 * u.Unit('micron')).to(spec_1d.plot_item.data.x.unit).value

        dlam = spec_2d.meta['CD1_1'] * scale
        crval = spec_2d.meta['CRVAL1'] * scale
        crpix = spec_2d.meta['CRPIX1']

        qtransform = QtGui.QTransform().translate(crval - dlam * crpix, 0).scale(dlam, 1)

        spec_2d.image_item.setTransform(qtransform)
        spec_2d.container.setAspectLocked(True, 1 / dlam)

        return qtransform

    @staticmethod
    def reset_spec2d_transform(spec_2d: Image2D):
        spec_2d.image_item.resetTransform()
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
        line = pg.InfiniteLine(spec_1d.z_slider.value, pen='m')
        spec_1d.redshift_changed.connect(lambda z: line.setPos(z))
        z_pdf.plot_item.addItem(line)

    @staticmethod
    def convert_spec1d_flux_units(spec_1d: Spec1D):
        if not isinstance(spec_1d.data, Table):
            return

        plot_data = spec_1d.plot_item.data
        if not plot_data.y.unit:
            return

        flat = spec_1d.data['flat'].to('1e19 AA cm2 ct / erg')
        plot_data.y.unit = plot_data.y.unit / flat.unit

        with np.errstate(divide='ignore'):
            scale = 1 / flat.value
        scale[scale == np.inf] = 0
        plot_data.y.scale(scale)

        limits = ZScaleInterval().get_limits(plot_data.y.value)
        flux = plot_data.y.value.copy()
        additional_mask = (spec_1d.data['npix'].value < 1E5)
        flux[((flux < limits[0]) | (flux > limits[1])) & additional_mask] = 0
        plot_data.y.set_value(flux)

        spec_1d.update_labels()
        spec_1d.redraw()
