import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

import argparse
import importlib
import logging
import pathlib
import sys

from . import ORGANIZATION, APPLICATION
from .config.appearance import setup_appearance
from .config import Config, SpectralLineData, WorkspaceRegistry, Workspace
from .config import (CACHE_DIR, CONFIG_DIR, DEFAULT_WORKSPACE_NAME, WORKSPACES_DIR, REGISTRY_FILENAME,
                     SPECTRAL_LINES_FILENAME)
from .config.migration import migrate_legacy_config, needs_migration
from .io.viewer_data import set_unit_aliases
from .plugins import available_plugins
from .utils.params import LocalFile

from .widgets.MainWindow import MainWindow

logger = logging.getLogger(__name__)

LEGACY_CACHE_FILENAME = f"{APPLICATION.lower()}.yml"


def resolve_workspace(registry: WorkspaceRegistry) -> Workspace | None:
    active = registry.resolve_active()

    if active is not None:
        workspace = Workspace.open(active)
        if workspace is not None:
            return workspace
        logger.error(f"Failed to open the active workspace (path: {active})")

    default_path = pathlib.Path(WORKSPACES_DIR) / DEFAULT_WORKSPACE_NAME
    if Workspace.is_workspace(default_path):
        return Workspace.open(default_path)

    logger.info("No workspace found, creating a default one")
    return Workspace.create(default_path, name=DEFAULT_WORKSPACE_NAME)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', action='count', default=0)
    parser.add_argument('--purge', action='store_true',
                        help="reset user preferences and the workspace list (workspaces themselves are kept)")
    parser.add_argument('--workspace', metavar='PATH', default=None,
                        help="open the workspace at PATH instead of the active one")

    args = parser.parse_args()

    if args.verbosity == 0:
        level = logging.WARNING
    elif args.verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=level)

    pg.setConfigOption('imageAxisOrder', 'row-major')

    user_files: dict[str, LocalFile] = {
        'config': LocalFile(CONFIG_DIR, filename='config.yml', full_name='User preferences'),
        'registry': LocalFile(CONFIG_DIR, filename=REGISTRY_FILENAME, full_name='Workspace list'),
        'lines': LocalFile(CONFIG_DIR, filename=SPECTRAL_LINES_FILENAME, full_name='List of spectral lines'),
        'legacy_cache': LocalFile(CACHE_DIR, filename=LEGACY_CACHE_FILENAME, full_name='Cache',
                                  auto_backup=False),
    }

    if args.purge:
        settings = QtCore.QSettings(ORGANIZATION, APPLICATION)
        settings.clear()
        settings.sync()
        for f in user_files.values():
            f.delete()
        logger.warning(f"User preferences reset. Workspaces were left untouched (location: {WORKSPACES_DIR})")

    if needs_migration(CONFIG_DIR, REGISTRY_FILENAME):
        migrated = migrate_legacy_config(CONFIG_DIR, CACHE_DIR, WORKSPACES_DIR, LEGACY_CACHE_FILENAME)
        if migrated is not None:
            registry = WorkspaceRegistry.read_user_params(user_files['registry'])
            registry.set_active(migrated)
            registry.save()

    exit_code = MainWindow.EXIT_CODE_REBOOT
    while exit_code == MainWindow.EXIT_CODE_REBOOT:
        # re-read on every reboot to pick up a workspace switch
        config = Config.read_user_params(user_files['config'], default='config.yml')
        spectral_lines = SpectralLineData.read_user_params(user_files['lines'], default=SPECTRAL_LINES_FILENAME)
        registry = WorkspaceRegistry.read_user_params(user_files['registry'])

        if args.workspace is not None:
            if Workspace.is_workspace(args.workspace):
                registry.set_active(args.workspace)
                registry.save()
            else:
                logger.error(f"Not a workspace, falling back to the active one (path: {args.workspace})")
            args.workspace = None  # only on the first start

        workspace = resolve_workspace(registry)
        if workspace is None:
            logger.critical("Failed to open or create a workspace")
            sys.exit(1)

        registry.set_active(workspace.path)
        registry.save()

        set_unit_aliases(workspace.config.data.enabled_unit_aliases)

        missing = [p for p in workspace.config.plugins if p not in available_plugins()]
        if missing:
            logger.warning(f"Plugins not found: {', '.join(missing)}")
            workspace.config.plugins = [p for p in workspace.config.plugins if p not in missing]
            workspace.config.save()
        plugins = [importlib.import_module("specvizitor.plugins." + p).Plugin() for p in workspace.config.plugins]

        app = QtWidgets.QApplication(sys.argv)
        app.setOrganizationName(ORGANIZATION)
        app.setApplicationName(APPLICATION)
        logger.info("Application started")

        setup_appearance(cfg=config.appearance)

        window = MainWindow(config=config, spectral_lines=spectral_lines, workspace=workspace, registry=registry,
                            plugins=plugins)
        window.show()

        exit_code = app.exec_()
        app = None
        logger.info("Application closed")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
