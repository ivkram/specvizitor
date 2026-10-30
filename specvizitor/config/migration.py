"""Moves a configuration from before workspaces existed into a "Default" workspace."""

import logging
import pathlib
import shutil

from . import DEFAULT_WORKSPACE_NAME
from ..utils.params import read_yaml, save_yaml
from ..utils.paths import absolute_path

logger = logging.getLogger(__name__)

__all__ = [
    "needs_migration",
    "migrate_legacy_config"
]

# keys of the legacy config.yml that belong to a workspace rather than to the user (`catalogue` has since been
# renamed to `catalog`)
WORKSPACE_KEYS = ('catalogue', 'data', 'inspection_results', 'plugins')
USER_KEYS = ('appearance', 'data_viewer')

LEGACY_SUFFIX = '.pre-workspace'


def needs_migration(config_dir, registry_filename: str) -> bool:
    config_dir = pathlib.Path(config_dir)

    # the registry only exists once workspaces have been used
    if (config_dir / registry_filename).is_file():
        return False

    legacy_config = config_dir / 'config.yml'
    if not legacy_config.is_file():
        return False

    try:
        data = read_yaml(legacy_config)
    except Exception:
        return False

    return any(key in data for key in WORKSPACE_KEYS)


def _archive(path: pathlib.Path) -> None:
    if not path.is_file():
        return
    dst = path.with_suffix(LEGACY_SUFFIX + path.suffix)
    try:
        shutil.move(str(path), str(dst))
        logger.info(f"Legacy file archived (path: {dst})")
    except OSError as e:
        logger.warning(f"Failed to archive a legacy file: {e} (path: {path})")


def migrate_legacy_config(config_dir, cache_dir, workspaces_dir, cache_filename: str) -> str | None:
    """Return the path to the new workspace, or None if nothing was migrated."""
    from .workspace import (WORKSPACE_CONFIG_FILENAME, WORKSPACE_LAYOUT_FILENAME, WORKSPACE_STATE_FILENAME,
                            WORKSPACE_WIDGETS_FILENAME)

    config_dir = pathlib.Path(config_dir)
    workspace_dir = pathlib.Path(workspaces_dir) / DEFAULT_WORKSPACE_NAME

    try:
        legacy = read_yaml(config_dir / 'config.yml')
    except Exception as e:
        logger.error(f"Failed to read the legacy configuration, migration skipped: {e}")
        return None

    try:
        workspace_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create the default workspace, migration skipped: {e}")
        return None

    # 1. split the legacy configuration into a workspace half and a user half
    workspace_data = {key: legacy[key] for key in WORKSPACE_KEYS if key in legacy}
    workspace_data['name'] = DEFAULT_WORKSPACE_NAME

    for section, key in (('data', 'dir'), ('catalogue', 'filename')):
        values = workspace_data.get(section) or {}
        value = values.pop(key, None)
        # '.' was the old default
        if value and value != '.':
            values[key] = str(absolute_path(value))

    if 'catalogue' in workspace_data:
        workspace_data['catalog'] = workspace_data.pop('catalogue')

    user_data = {key: legacy[key] for key in USER_KEYS if key in legacy}

    try:
        save_yaml(workspace_dir / WORKSPACE_CONFIG_FILENAME, workspace_data)
    except OSError as e:
        logger.error(f"Failed to write the default workspace, migration skipped: {e}")
        return None

    # 2. move the data viewer configuration into the workspace
    src = config_dir / WORKSPACE_WIDGETS_FILENAME
    if src.is_file():
        try:
            shutil.copy(src, workspace_dir / WORKSPACE_WIDGETS_FILENAME)
        except OSError as e:
            logger.warning(f"Failed to migrate `{WORKSPACE_WIDGETS_FILENAME}`: {e}")
        else:
            _archive(src)

    # 3. carry the session state and the layout over from the old cache
    legacy_cache = pathlib.Path(cache_dir) / cache_filename
    if legacy_cache.is_file():
        try:
            cache = read_yaml(legacy_cache)
        except Exception as e:
            logger.warning(f"Failed to read the legacy cache, state not carried over: {e}")
        else:
            state = {key: cache[key] for key in ('last_inspection_file', 'last_object_index', 'last_subset_file')
                     if cache.get(key) is not None}
            layout = {key: cache[key] for key in ('dock_layout',) if cache.get(key) is not None}
            try:
                if state:
                    save_yaml(workspace_dir / WORKSPACE_STATE_FILENAME, state)
                if layout:
                    save_yaml(workspace_dir / WORKSPACE_LAYOUT_FILENAME, layout)
            except OSError as e:
                logger.warning(f"Failed to carry the session state over: {e}")

    # 4. replace the legacy config.yml with the user-scoped half only
    _archive(config_dir / 'config.yml')
    try:
        save_yaml(config_dir / 'config.yml', user_data)
    except OSError as e:
        logger.warning(f"Failed to write the user configuration: {e}")

    # 5. check the result
    from .workspace import Workspace
    if not Workspace.is_workspace(workspace_dir):
        logger.error(f"Migration produced an unusable workspace (path: {workspace_dir})")
        return None

    logger.warning(f"Configuration migrated into a workspace (path: {workspace_dir}). "
                   f"Legacy files were kept alongside with a `{LEGACY_SUFFIX}` suffix.")
    return str(workspace_dir)
