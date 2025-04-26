import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

import argparse
import importlib
import logging
import sys

from . import ORGANIZATION, APPLICATION
from .config.appearance import setup_appearance
from .config import Cache, Config, DataWidgets, SpectralLineData
from .config import CACHE_DIR, CONFIG_DIR
from .io.viewer_data import add_unit_aliases
from .utils.params import LocalFile

from .widgets.MainWindow import MainWindow

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', action='count', default=0)
    parser.add_argument('--purge', action='store_true')

    args = parser.parse_args()

    # configure logging parameters
    if args.verbosity == 0:
        level = logging.WARNING
    elif args.verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    # configure pyqtgraph options
    pg.setConfigOption('imageAxisOrder', 'row-major')

    # read local config files
    local_files: dict[str, LocalFile] = {
        'config': LocalFile(CONFIG_DIR, filename='config.yml', full_name='General GUI settings'),
        'cache': LocalFile(CACHE_DIR, full_name='Cache', auto_backup=False),
        'widgets': LocalFile(CONFIG_DIR, filename='data_widgets.yml', full_name='Data viewer configuration'),
        'lines': LocalFile(CONFIG_DIR, filename='spectral_lines.yml', full_name='List of spectral lines'),
    }

    if args.purge:
        settings = QtCore.QSettings(ORGANIZATION, APPLICATION)
        settings.clear()
        settings.sync()
        for f in local_files.values():
            f.delete()  # safe delete

    config = Config.read_user_params(local_files['config'], default='config.yml')

    # register unit aliases
    add_unit_aliases(config.data.enabled_unit_aliases)

    # "discover" and "register" plugins
    plugins = []
    undiscovered_plugins = []
    for plugin_name in config.plugins:
        try:
            plugins.append(importlib.import_module("specvizitor.plugins." + plugin_name).Plugin())
        except ModuleNotFoundError:
            logger.warning(f'Plugin not found: {plugin_name}')
            undiscovered_plugins.append(plugin_name)

    config.plugins = [plugin_name for plugin_name in config.plugins if plugin_name not in undiscovered_plugins]
    config.save()

    exit_code = MainWindow.EXIT_CODE_REBOOT
    while exit_code == MainWindow.EXIT_CODE_REBOOT:
        # start the application
        app = QtWidgets.QApplication(sys.argv)
        app.setOrganizationName(ORGANIZATION)
        app.setApplicationName(APPLICATION)
        logger.info("Application started")

        # set up the GUI appearance
        setup_appearance(cfg=config.appearance)

        # create the main window
        window = MainWindow(config=config,
                            cache=Cache.read_user_params(local_files['cache']),
                            widget_cfg=DataWidgets.read_user_params(local_files['widgets'], default='data_widgets.yml'),
                            spectral_lines=SpectralLineData.read_user_params(local_files['lines'],
                                                                             default='spectral_lines.yml'),
                            plugins=plugins)
        window.show()

        exit_code = app.exec_()
        app = None
        logger.info("Application closed")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
