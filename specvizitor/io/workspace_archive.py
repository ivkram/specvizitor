from dataclasses import asdict, dataclass
import copy
import logging
import pathlib
import shutil
import yaml
import zipfile

from ..config.workspace import (WORKSPACE_CONFIG_FILENAME, WORKSPACE_LAYOUT_FILENAME, WORKSPACE_WIDGETS_FILENAME,
                                Workspace, WorkspaceConfig)

logger = logging.getLogger(__name__)

__all__ = [
    "ARCHIVE_EXTENSION",
    "ARCHIVE_FILTER",
    "ExportOptions",
    "unset_paths",
    "export_workspace",
    "inspect_archive",
    "archive_workspace_name",
    "import_workspace"
]

ARCHIVE_EXTENSION = '.sviz'
ARCHIVE_FILTER = f'Specvizitor Workspaces (*{ARCHIVE_EXTENSION})'

# the inspection file can be included as well
ARCHIVED_FILENAMES = (WORKSPACE_CONFIG_FILENAME, WORKSPACE_WIDGETS_FILENAME, WORKSPACE_LAYOUT_FILENAME)


@dataclass
class ExportOptions:
    include_widgets: bool = True
    include_layout: bool = True
    include_results: bool = False
    include_local_paths: bool = False


def _selected_filenames(options: ExportOptions) -> list[str]:
    selected = []
    if options.include_widgets:
        selected.append(WORKSPACE_WIDGETS_FILENAME)
    if options.include_layout:
        selected.append(WORKSPACE_LAYOUT_FILENAME)
    return selected


def _path_fields(cfg: WorkspaceConfig) -> list[tuple[str, object, str]]:
    # the machine-specific paths, as (title, parent, attribute)
    fields = [("Data directory", cfg.data, 'dir'), ("Catalogue", cfg.catalogue, 'filename')]
    for label, image in cfg.data.images.items():
        fields += [(f"Image ({label})", image, 'filename'), (f"WCS source ({label})", image, 'wcs_source')]
    return fields


def unset_paths(cfg: WorkspaceConfig) -> list[tuple[str, object, str]]:
    # a WCS source is optional: ask for it only along with its image
    return [(title, obj, attr) for title, obj, attr in _path_fields(cfg)
            if getattr(obj, attr) is None and (attr != 'wcs_source' or obj.filename is None)]


def _shareable_config(cfg: WorkspaceConfig) -> dict:
    cfg = copy.deepcopy(cfg)
    for _, obj, attr in _path_fields(cfg):
        setattr(obj, attr, None)
    return asdict(cfg)


def export_workspace(workspace: Workspace, dest, options: ExportOptions | None = None) -> bool:
    options = options if options is not None else ExportOptions()

    workspace.save_all()

    try:
        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            if options.include_local_paths:
                archive.write(workspace.path / WORKSPACE_CONFIG_FILENAME, arcname=WORKSPACE_CONFIG_FILENAME)
            else:
                archive.writestr(WORKSPACE_CONFIG_FILENAME,
                                 yaml.safe_dump(_shareable_config(workspace.config), sort_keys=False))

            for filename in _selected_filenames(options):
                src = workspace.path / filename
                if src.is_file():
                    archive.write(src, arcname=filename)

            if options.include_results:
                results = workspace.state.last_inspection_file
                if results and pathlib.Path(results).is_file():
                    archive.write(results, arcname=pathlib.Path(results).name)
                elif results:
                    logger.warning(f"Inspection file not found, excluded from the archive (path: {results})")
    except OSError as e:
        logger.error(f"Failed to export the workspace: {e} (path: {dest})")
        return False

    logger.info(f"Workspace exported (path: {dest})")
    return True


def _is_safe_member(name: str) -> bool:
    # only plain filenames: nothing that could end up outside the destination directory
    if not name or name.endswith('/'):
        return False
    path = pathlib.PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or len(path.parts) != 1:
        return False
    # a drive letter or a backslash would still be a single POSIX part
    return not (':' in name or '\\' in name)


def _is_expected_member(name: str) -> bool:
    return name in ARCHIVED_FILENAMES or name.endswith('.csv')


# the files that the archive would install, or None if it is not a workspace archive
def inspect_archive(path) -> list[str] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as e:
        logger.error(f"Failed to read the archive: {e} (path: {path})")
        return None

    if WORKSPACE_CONFIG_FILENAME not in names:
        logger.error(f"Not a workspace archive: no {WORKSPACE_CONFIG_FILENAME} inside (path: {path})")
        return None

    return [n for n in names if _is_safe_member(n) and _is_expected_member(n)]


def archive_workspace_name(path) -> str | None:
    try:
        with zipfile.ZipFile(path) as archive:
            with archive.open(WORKSPACE_CONFIG_FILENAME) as f:
                cfg = yaml.safe_load(f)
    except (OSError, KeyError, zipfile.BadZipFile, yaml.YAMLError):
        return None

    if not isinstance(cfg, dict):
        return None

    name = cfg.get('name')
    return name if isinstance(name, str) and name.strip() else None


def import_workspace(archive_path, dest_dir) -> Workspace | None:
    members = inspect_archive(archive_path)
    if members is None:
        return None

    # the archived files replace the defaults
    workspace = Workspace.create(dest_dir)
    if workspace is None:
        return None

    try:
        with zipfile.ZipFile(archive_path) as archive:
            skipped = [n for n in archive.namelist() if n not in members]
            for name in members:
                with archive.open(name) as src, open(workspace.path / name, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
    except (OSError, zipfile.BadZipFile) as e:
        logger.error(f"Failed to import the workspace: {e} (path: {archive_path})")
        return None

    if skipped:
        logger.warning(f"Unexpected entries were skipped during the import: {', '.join(sorted(skipped))}")

    workspace = Workspace.open(workspace.path)
    if workspace is None:
        return None

    results = [name for name in members if name.endswith('.csv')]
    if results:
        workspace.state.last_inspection_file = str(workspace.path / results[0])
        workspace.state.save()

    logger.info(f"Workspace imported (path: {workspace.path})")
    return workspace
