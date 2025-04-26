from astropy.table import Table
import astropy.units as u
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Container import StackedWidget
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

        lm_stack = self.get_dock_stack(lm_docks)

        if lm_stack:
            self.fix_dock_stack_labels(lm_stack)
            if cat_entry:
                self.raise_lm_dock(lm_stack, cat_entry)
            if not self._shortcuts_added:
                self._add_shortcuts(lm_docks, parent=lm_stack.widget(0).area.parent())

    @staticmethod
    def raise_lm_dock(lm_stack: StackedWidget, cat_entry: Catalog):
        lines = []
        for i in range(lm_stack.count()):
            d = lm_stack.widget(i)
            try:
                extver = d.widgets[0].meta["EXTVER"]
            except (TypeError, KeyError):
                lines.append(None)
            else:
                lines.append(extver)

        snr = []
        for i, line in enumerate(lines):
            try:
                snr_from_cat = cat_entry.get_col(f"sn_{line}")
            except KeyError:
                snr.append(0.)
            else:
                snr.append(snr_from_cat)

        i = int(np.argmax(snr))
        lm_stack.widget(i).raiseDock()


    def _add_shortcuts(self, lm_docks: dict[str, Dock], parent=None):
        QtWidgets.QShortcut('Up', parent, partial(self._switch_current_linemap, lm_docks, -1))
        QtWidgets.QShortcut('Down', parent, partial(self._switch_current_linemap, lm_docks, 1))
        self._shortcuts_added = True

    def _switch_current_linemap(self, lm_docks: dict[str, Dock], delta_index: int):
        lm_stack = self.get_dock_stack(lm_docks)
        if not lm_stack:
            return

        i = (lm_stack.currentIndex() + delta_index) % lm_stack.count()
        lm_stack.widget(i).raiseDock()

    def update_active_widgets(self, widgets: dict[str, ViewerElement], cat_entry: Catalog | None = None):
        spec_1d: Plot1D | None = widgets.get('Spectrum 1D')
        z_pdf: Plot1D | None = widgets.get('Redshift PDF')

        if spec_1d is not None:
            for w in widgets.values():
                if 'Spectrum 2D' in w.title:
                    self.transform_spec2d(w, spec_1d)

        if spec_1d is not None and z_pdf is not None:
            self.add_current_redshift_to_z_pdf(spec_1d, z_pdf)

        if spec_1d is not None:
            self.convert_spec1d_flux_unit_to_physical(spec_1d)
            spec_1d.setup_view(cat_entry)

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

        y_unit = (t['flux'] * scale).unit
        spec_1d._axes.y.unit = y_unit

        for label in ('flux', 'err', 'model'):
            plot_data_item = spec_1d.plot_data_items.get(label)
            if plot_data_item is None:
                continue

            x_data, _ = plot_data_item.getData()

            y_data = spec_1d.get_plot_data(spec_1d.cfg.plots[label].y)
            y_data *= scale
            y_data = spec_1d.apply_ydata_transform(y_data)

            t[label] = y_data * y_unit  # replace the original data
            plot_data_item.setData(x=x_data, y=y_data)
