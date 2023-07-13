import pyqtgraph as pg
from qtpy import QtWidgets

import argparse
import importlib
import logging
import pathlib
from platformdirs import user_config_dir, user_cache_dir
import sys

from .config.appearance import set_up_appearance
from .config import Config, DataWidgets, SpectralLines, Cache
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
        'config': LocalFile(CONFIG_DIR, filename='config.yml', full_name='General GUI settings'),
        'cache': LocalFile(CACHE_DIR, full_name='Cache', auto_backup=False),
        'widgets': LocalFile(CONFIG_DIR, filename='data_widgets.yml', full_name='Data viewer configuration'),
        'lines': LocalFile(CONFIG_DIR, filename='spectral_lines.yml', full_name='List of spectral lines'),
    }

    if args.purge:
        # deleting old configuration files which are no longer in use
        with open(pathlib.Path(__file__).parent / 'data' / 'presets' / 'legacy.txt', 'r') as file:
            for line in file:
                legacy_config = pathlib.Path(CONFIG_DIR) / line.rstrip()
                legacy_config.unlink(missing_ok=True)
                (legacy_config.parent / (legacy_config.name + '.bak')).unlink(missing_ok=True)

        for f in local_files.values():
            f.delete()  # safe delete

    config = Config.read_user_params(local_files['config'], default='config.yml')

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
    window = MainWindow(config=config,
                        cache=Cache.read_user_params(local_files['cache']),
                        viewer_cfg=DataWidgets.read_user_params(local_files['widgets'], default='data_widgets.yml'),
                        spectral_lines=SpectralLines.read_user_params(local_files['lines'],
                                                                      default='spectral_lines.yml'),
                        plugins=plugins)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
