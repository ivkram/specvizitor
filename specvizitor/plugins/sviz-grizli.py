from astropy.table import Table
import astropy.units as u
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from qtpy import QtGui, QtWidgets

from functools import partial
import logging

from specvizitor.io.catalog import Catalog
from specvizitor.plugins.plugin_core import PluginCore

from specvizitor.widgets.ViewerElement import ViewerElement
from specvizitor.widgets.Image2D import Image2D
from specvizitor.widgets.Plot1D import Plot1D

logger = logging.getLogger(__name__)


class Plugin(PluginCore):
    LM_NAME = 'Line Map {}'

    def __init__(self):
        super().__init__()

        self._shortcuts_added = False

    def override_widget_configs(self, widgets: dict[str, ViewerElement]):
        """Override configurations of line maps.
        """
        lm: Image2D

        i = 1
        while widgets.get(self.LM_NAME.format(i)):
            lm = widgets.get(self.LM_NAME.format(i))
            if i > 1:
                lm.cfg.relative_to = self.LM_NAME.format(i - 1)
                lm.cfg.position = 'below'
            lm.cfg.data.loader_params['extver_index'] = i - 1  # EXTVER indexing starts at 0
            i += 1

    def update_docks(self, docks: dict[str, Dock], cat_entry: Catalog | None = None):
        """Add keyboard shortcuts to switch between line maps.
        """

        i = 1
        lm_docks = {}

        while docks.get(self.LM_NAME.format(i)):
            title = self.LM_NAME.format(i)
            lm_docks[title] = docks[title]
            i += 1

        stacked_lm_docks = self.get_stacked_docks(lm_docks)
        if not stacked_lm_docks:
            return

        stacked_lm_docks = list(stacked_lm_docks.values())

        '''
        * patching a pyqtgraph bug *
        when the dock area state is restored, the current active widget of the line map stack is changed to Line Map 1,
        however the last Line Map remains active (i.e. its label is still highlighted). therefore, when Line Map 1 is
        raised to the top, the last Line Map remains active
        '''
        if len(stacked_lm_docks) > 1:
            stacked_lm_docks[-1].label.setDim(True)

        # raise the first line map dock to the top
        stacked_lm_docks[0].raiseDock()

        if not self._shortcuts_added:
            data_viewer = stacked_lm_docks[0].area.parent()
            QtWidgets.QShortcut('Up', data_viewer, partial(self.switch_current_linemap, lm_docks, -1))
            QtWidgets.QShortcut('Down', data_viewer, partial(self.switch_current_linemap, lm_docks, 1))
            self._shortcuts_added = True

    def switch_current_linemap(self, lm_docks: dict[str, Dock], delta_index: int):
        stacked_lm_docks = self.get_stacked_docks(lm_docks)
        if not stacked_lm_docks:
            return

        stacked_lm_docks = list(stacked_lm_docks.values())
        stack = stacked_lm_docks[0].container().stack
        stacked_lm_docks[(stack.currentIndex() + delta_index) % stack.count()].raiseDock()

    def update_active_widgets(self, widgets: dict[str, ViewerElement], cat_entry: Catalog | None = None):
        spec_1d: Plot1D | None = widgets.get('Spectrum 1D')
        z_pdf: Plot1D | None = widgets.get('Redshift PDF')

        if spec_1d is not None:
            for w in widgets.values():
                if 'Spectrum 2D' in w.title:
                    self.transform_spec2d(w, spec_1d)
                    w.reset_view()

        if spec_1d is not None and z_pdf is not None:
            self.add_current_redshift_to_z_pdf(spec_1d, z_pdf)

        if spec_1d is not None:
            self.convert_spec1d_flux_unit_to_physical(spec_1d)
            spec_1d.setup_view(cat_entry)
            spec_1d.reset_view()

    @staticmethod
    def transform_spec2d(spec_2d: Image2D, spec_1d: Plot1D):
        wave_unit = spec_1d._axes.x.unit
        if not wave_unit or not wave_unit.is_equivalent('AA'):
            wave_unit = 'AA'

        spec_2d._axes.x.unit = wave_unit
        spec_2d._axes.x.label = spec_1d._axes.x.label
        spec_2d.update_axis_labels()

        scale = (1 * u.Unit('micron')).to(wave_unit).value

        dlam = spec_2d.meta['CD1_1'] * scale
        crval = spec_2d.meta['CRVAL1'] * scale
        crpix = spec_2d.meta['CRPIX1']

        spec_2d._qtransform = QtGui.QTransform().translate(crval - dlam * crpix, 0).scale(dlam, 1)
        spec_2d.apply_qtransform(apply_to_default_range=True)

    @staticmethod
    def add_current_redshift_to_z_pdf(spec_1d: Plot1D, z_pdf: Plot1D):
        line = pg.InfiniteLine(spec_1d.redshift_slider.value, pen='m')
        spec_1d.redshift_slider.value_changed[float].connect(lambda z: line.setPos(z))
        z_pdf.register_item(line)

    @staticmethod
    def convert_spec1d_flux_unit_to_physical(spec_1d: Plot1D):
        t = spec_1d.data
        if not isinstance(t, Table):
            logger.error('Spectrum 1D data must be of the `astropy.table.Table` type')
            return

        # check that the `flux` and `flat` columns are in the table
        if 'flux' not in t.colnames:
            logger.error('Column not found: flux')
        if 'flat' not in t.colnames:
            logger.error('Column not found: flat')

        # check that the flux unit is correct
        if not t['flux'].unit or not t['flux'].unit.is_equivalent(u.Unit('ct / s')):
            logger.error('The input flux unit must be `ct/s`')
            return

        # convert fluxes to physical units
        flat = t['flat'].to('1e19 AA cm2 ct / erg')

        with np.errstate(divide='ignore'):
            scale = 1 / flat
        scale[scale == np.inf] = np.nan

        spec_1d._axes.y.unit = (t['flux'] * scale).unit

        for label in ('flux', 'err', 'model'):
            plot_data_item = spec_1d.plot_data_items.get(label)
            if plot_data_item is None:
                continue

            x_data, _ = plot_data_item.getData()

            y_data = spec_1d.get_plot_data(spec_1d.cfg.plots[label].y)
            y_data *= scale
            y_data = spec_1d.apply_ydata_transform(y_data)

            plot_data_item.setData(x=x_data, y=y_data)
