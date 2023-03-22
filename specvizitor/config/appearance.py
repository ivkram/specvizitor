import pyqtgraph as pg
import qdarktheme

from .config import Appearance


def configure(cfg: Appearance):
    pg.setConfigOption('antialias', cfg.antialiasing)

    # set up the theme
    qdarktheme.setup_theme(cfg.theme)
    if cfg.theme == 'dark':
        pg.setConfigOption('background', "#1d2023")
        pg.setConfigOption('foreground', '#eff0f1')
    else:
        pg.setConfigOption('background', "w")
        pg.setConfigOption('foreground', 'k')
