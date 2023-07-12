from astropy.table import Table
import astropy.units as u
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from qtpy import QtGui, QtCore

import logging

from specvizitor.plugins.plugin_core import PluginCore
from specvizitor.widgets.ViewerElement import ViewerElement
from specvizitor.widgets.Image2D import Image2D
from specvizitor.widgets.Spec1D import Spec1D
from specvizitor.widgets.Plot1D import Plot1D

logger = logging.getLogger(__name__)


class Plugin(PluginCore):
    def override_widget_configs(self, widgets: dict[str, ViewerElement]):
        lm: Image2D

        i = 1
        while lm := widgets.get(f'Line Map {i}'):
            if i > 1:
                lm.cfg.relative_to = f'Line Map {i - 1}'
                lm.cfg.position = 'below'
            lm.cfg.data.loader_params['extver_index'] = i - 1  # EXTVER indexing starts with 0
            i += 1

    def tweak_widgets(self, widgets: dict[str, ViewerElement]):
        spec_1d: Spec1D | None = widgets.get('Spectrum 1D')
        spec_2d: Image2D | None = widgets.get('Spectrum 2D')
        image: Image2D | None = widgets.get('Image Cutout')
        z_pdf: Plot1D | None = widgets.get('Redshift PDF')
        lm: Image2D

        if spec_2d is not None:
            line = self.add_axis_of_symmetry_to_spec2d(spec_2d)

            if spec_1d is not None:
                qtransform = self.transform_spec2d_x_axis(spec_2d, spec_1d)
                line.setTransform(qtransform)
                self.link_spec2d_to_spec1d(spec_2d, spec_1d)
                spec_1d.reset_view()
            else:
                self.reset_spec2d_transformation(spec_2d)
                self.unlink_spec2d(spec_2d)
                spec_2d.reset_view()

        if image is not None:
            self.add_crosshair_to_image_cutout(image)

        if spec_1d is not None and z_pdf is not None:
            self.add_current_redshift_to_z_pdf(spec_1d, z_pdf)

        if spec_1d is not None:
            self.convert_spec1d_flux_unit_to_physical(spec_1d)
            spec_1d.reset_view()

    def refine_dock_titles(self, docks: dict[str, Dock], widgets: dict[str, ViewerElement]):
        i = 1
        while lm := widgets.get(f'Line Map {i}'):
            if extver := lm.meta.get('EXTVER'):
                docks[lm.title].setTitle(extver)
            i += 1

    @staticmethod
    def transform_spec2d_x_axis(spec_2d: Image2D, spec_1d: Spec1D) -> QtGui.QTransform:
        scale = (1 * u.Unit('micron')).to(spec_1d.plot_item.data.x.unit).value

        dlam = spec_2d.meta['CD1_1'] * scale
        crval = spec_2d.meta['CRVAL1'] * scale
        crpix = spec_2d.meta['CRPIX1']

        qtransform = QtGui.QTransform().translate(crval - dlam * crpix, 0).scale(dlam, 1)

        spec_2d.image_item.setTransform(qtransform)
        spec_2d.container.setAspectLocked(True, 1 / dlam)

        return qtransform

    @staticmethod
    def reset_spec2d_transformation(spec_2d: Image2D):
        spec_2d.image_item.resetTransform()
        spec_2d.container.setAspectLocked(True, 1)

    @staticmethod
    def link_spec2d_to_spec1d(spec_2d: Image2D, spec_1d: Spec1D):
        spec_2d.container.setXLink(spec_1d.title)

    @staticmethod
    def unlink_spec2d(spec_2d: Image2D):
        spec_2d.container.setXLink(None)

    @staticmethod
    def add_axis_of_symmetry_to_spec2d(spec_2d: Image2D) -> pg.PlotCurveItem:
        y = spec_2d.meta['NAXIS2'] / 2
        pen = 'w'

        line = pg.PlotCurveItem([0, spec_2d.meta['NAXIS1']], [y, y], pen=pen)
        spec_2d.register_item(line)

        return line

    @staticmethod
    def add_crosshair_to_image_cutout(image: Image2D) -> tuple[pg.PlotCurveItem, pg.PlotCurveItem]:
        pen = pg.mkPen('w', width=1, style=QtCore.Qt.DashLine)

        x0, y0 = image.data.shape[0] // 2, image.data.shape[1] // 2
        dx, dy = 0.15 * x0, 0.15 * y0

        crosshair_x = pg.PlotCurveItem([0, x0 - dx], [y0, y0], pen=pen)
        crosshair_y = pg.PlotCurveItem([x0, x0], [0, y0 - dy], pen=pen)

        image.register_item(crosshair_x)
        image.register_item(crosshair_y)

        return crosshair_x, crosshair_y

    @staticmethod
    def add_current_redshift_to_z_pdf(spec_1d: Spec1D, z_pdf: Plot1D):
        line = pg.InfiniteLine(spec_1d.z_slider.value, pen='m')
        spec_1d.redshift_changed.connect(lambda z: line.setPos(z))
        z_pdf.plot_item.addItem(line)

    @staticmethod
    def convert_spec1d_flux_unit_to_physical(spec_1d: Spec1D):
        if not isinstance(spec_1d.data, Table):
            try:
                t: Table = Table.read(spec_1d.filename)
            except Exception as e:
                logger.error(e)
                return
        else:
            t = spec_1d.data

        # check that the `flat` column is in the table
        try:
            t.field('flat')
        except KeyError:
            logger.error('Failed to convert the flux unit to physical: `flat` column not found')
            return

        # check that the original units are correct
        plot_data = spec_1d.plot_item.data
        if not plot_data.y.unit or not plot_data.y.unit.is_equivalent(u.Unit('ct / s')):
            return

        # convert fluxes to physical units
        flat = t['flat'].to('1e19 AA cm2 ct / erg')
        plot_data.y.unit = plot_data.y.unit / flat.unit

        with np.errstate(divide='ignore'):
            scale = 1 / flat.value
        scale[scale == np.inf] = np.nan
        plot_data.y.scale(scale)

        # update the y-axis limits based on uncertainties
        plot_data.y.apply_unc_cutoff(0.25)

        # update labels and redraw the plot
        spec_1d.update_labels()
        spec_1d.redraw()
