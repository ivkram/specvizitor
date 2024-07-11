import pyqtgraph as pg

from ..config import Appearance
from .qdarktheme import setup_theme as setup_qtheme


__all__ = [
    "setup_appearance"
]


def setup_theme(theme: str):
    setup_qtheme(theme)

    if theme == 'dark':
        pg.setConfigOption('background', "#1d2023")
        pg.setConfigOption('foreground', '#eff0f1')
    else:
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')


def setup_appearance(cfg: Appearance, update_theme: bool = True):
    pg.setConfigOption('antialias', cfg.antialiasing)

    if update_theme:
        setup_theme(theme=cfg.theme)
