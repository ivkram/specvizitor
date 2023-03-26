import pyqtgraph as pg
from qtpy import QtWidgets

import argparse
import importlib
import logging
from platformdirs import user_config_dir, user_cache_dir
import sys

from .config.appearance import set_up_appearance
from .config import Config, Docks, SpectralLines, Cache
from .io.viewer_data import add_enabled_aliases
from .utils.params import LocalFile

from .widgets.MainWindow import MainWindow

logger = logging.getLogger(__name__)

ORGANIZATION_NAME = 'FRESCO'
APPLICATION_NAME = __package__.split('.')[0]

CONFIG_DIR = user_config_dir(APPLICATION_NAME)
CACHE_DIR = user_cache_dir(APPLICATION_NAME)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--purge', action='store_true')

    args = parser.parse_args()

    # configure logging parameters
    level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    # configure pyqtgraph options
    pg.setConfigOption('imageAxisOrder', 'row-major')

    # read local config files
    local_files: dict[str, LocalFile] = {
        'config': LocalFile(CONFIG_DIR, full_name='Settings file'),
        'cache': LocalFile(CACHE_DIR, full_name='Cache file', auto_backup=False),
        'docks': LocalFile(CONFIG_DIR, filename='docks.yml', full_name='Dock configuration file'),
        'lines': LocalFile(CONFIG_DIR, filename='lines.yml', full_name='List of spectral lines'),
    }

    if args.purge:
        for f in local_files.values():
            f.delete()

    config = Config.read_user_params(local_files['config'], default='default_config.yml')
    docks = Docks.read_user_params(local_files['docks'], default='default_docks.yml')
    lines = SpectralLines.read_user_params(local_files['lines'], default='default_lines.yml')
    cache = Cache.read_user_params(local_files['cache'])

    # register unit aliases
    if config.data.enabled_unit_aliases is not None:
        add_enabled_aliases(config.data.enabled_unit_aliases)

    # start the application
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME.capitalize())
    logger.info("Application started")

    # set up the GUI appearance
    set_up_appearance(cfg=config.appearance)

    # "discover" and "register" plugins (to be updated)
    plugins = [importlib.import_module("specvizitor.plugins." + plugin_name).Plugin()
               for plugin_name in config.plugins]

    # create the main window
    window = MainWindow(config=config, cache=cache, docks=docks, spectral_lines=lines, plugins=plugins)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
