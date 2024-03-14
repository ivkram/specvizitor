import pyqtgraph as pg
import qdarktheme

from .config import Appearance


def set_up_appearance(cfg: Appearance):
    pg.setConfigOption('antialias', cfg.antialiasing)

    qdarktheme.setup_theme(cfg.theme)
    if cfg.theme == 'dark':
        pg.setConfigOption('background', "#1d2023")
        pg.setConfigOption('foreground', '#eff0f1')
    else:
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
