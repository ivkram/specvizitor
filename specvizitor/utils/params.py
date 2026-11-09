import logging
import pathlib
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from functools import wraps
from typing import ClassVar, get_args, get_origin, get_type_hints

import dacite
import yaml

from .paths import absolute_path, atomic_write

logger = logging.getLogger(__name__)


def _unknown_keys(tp, data, path: str = '') -> list[str]:
    """ The keys in `data` that match no field of the dataclass `tp`, at any depth, as dotted paths.
    """
    if is_dataclass(tp):
        if not isinstance(data, dict):
            return []
        names = {f.name for f in fields(tp)}
        hints = get_type_hints(tp)
        unknown = []
        for key, value in data.items():
            key_path = f'{path}.{key}' if path else str(key)
            if key in names:
                unknown += _unknown_keys(hints[key], value, key_path)
            else:
                unknown.append(key_path)
        return unknown

    origin, args = get_origin(tp), get_args(tp)
    if origin is dict and isinstance(data, dict):
        return [k for key, value in data.items() for k in _unknown_keys(args[1], value, f'{path}.{key}')]
    if origin is list and isinstance(data, list):
        return [k for i, value in enumerate(data) for k in _unknown_keys(args[0], value, f'{path}[{i}]')]
    # a union, e.g. `Axis | None`
    return list(dict.fromkeys(k for arg in args for k in _unknown_keys(arg, data, path)))


@dataclass
class LocalFile:
    directory: str
    filename: str = f"{__package__.split('.')[0]}.yml"
    full_name: str = "Local file"
    auto_backup: bool = True

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.directory) / self.filename

    @staticmethod
    def missing_ok(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.path.exists():
                return
            return func(self, *args, **kwargs)
        return wrapper

    def save(self, data: dict) -> bool:
        if self.path.exists():
            msg = f"{self.full_name} updated (path: {self.path})"
        else:
            msg = f"{self.full_name} created (path: {self.path})"

        # the file may be on read-only or unreachable storage: report it instead of crashing
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            save_yaml(self.path, data)
        except OSError as e:
            logger.error(f"Failed to write the {self.full_name.lower()}: {e} (path: {self.path})")
            return False

        logger.debug(msg)
        return True

    @missing_ok
    def backup(self) -> pathlib.Path:
        dst = self.path.parent / (self.filename + '.bak')
        shutil.copy(self.path, dst)
        logger.debug(f'{self.full_name} backed up (path: {dst})')
        return dst

    @missing_ok
    def delete(self) -> None:
        if self.auto_backup:
            self.backup()

        self.path.unlink()
        logger.debug(f'{self.full_name} deleted (path: {self.path})')


@dataclass
class Params:
    # Schema migrations, as {version: function}. Each function takes the data read from a file one version
    # older and returns it in the new layout. Files from before schema versions are version 0.
    #
    # Only breaking changes need a migration. A new field with a default, or a removed field, works without one.
    #
    # Example: renaming `foo` to `bar` in version 2:
    #   MIGRATIONS = {2: lambda d: {**d, "bar": d.pop("foo", None)}}
    MIGRATIONS: ClassVar[dict[int, Callable[[dict], dict]]] = {}

    def __post_init__(self):
        self._file: LocalFile | None = None
        # the data last read from or written to the file, so that saving it unchanged can be skipped
        self._saved: dict | None = None
        # the file was saved by a newer version, so it must not be overwritten
        self._read_only: bool = False

    @classmethod
    def schema_version(cls) -> int:
        # the version of the newest migration, or 1 if there are none
        return max(cls.MIGRATIONS, default=1)

    @classmethod
    def _pop_schema_version(cls, data) -> int:
        if not isinstance(data, dict):
            # a ValueError, like any other malformed file, so that the callers fall back to the defaults
            raise ValueError("Expected a mapping of keys to values")  # noqa: TRY004

        # before schema versions, files recorded the package version instead
        data.pop('config_version', None)
        version = data.pop('schema_version', 0)
        if not isinstance(version, int) or isinstance(version, bool) or version < 0:
            raise ValueError(f"Invalid schema_version: {version!r}")
        return version

    @classmethod
    def _parse(cls, data: dict, version: int, source) -> "Params":
        for to_version, migrate in sorted(cls.MIGRATIONS.items()):
            if version < to_version:
                data = migrate(data)

        unknown = _unknown_keys(cls, data)
        if unknown:
            logger.warning(f"Unknown keys ignored: {', '.join(unknown)} (path: {source})")

        return dacite.from_dict(data_class=cls, data=data)

    @classmethod
    def read_default_params(cls, filename: str):
        path = pathlib.Path(__file__).parent.parent / 'data' / 'config' / filename
        return dacite.from_dict(data_class=cls, data=read_yaml(path), config=dacite.Config(strict=True))

    @classmethod
    def read_user_params(cls, file: LocalFile, default: str | None = None):
        fallback_params = cls.read_default_params(default) if default is not None else cls()
        fallback_params._file = file

        if not file.path.exists():
            # start from the defaults, so that there is a file to edit
            fallback_params.save()
            return fallback_params

        version = None
        try:
            data = read_yaml(file.path)
            version = cls._pop_schema_version(data)
            user_params = cls._parse(data, version, file.path)
        except (yaml.YAMLError, ValueError, dacite.DaciteError) as e:
            if version is not None and version > cls.schema_version():
                user_params = fallback_params
            else:
                if file.auto_backup:
                    backup = file.backup()
                    logger.error(f"Invalid {file.full_name.lower()}, reset to defaults: {e} "
                                 f"(path: {file.path}, backup: {backup})")
                else:
                    logger.debug(f"Invalid {file.full_name.lower()}, reset: {e} (path: {file.path})")
                fallback_params.save()
                return fallback_params

        user_params._file = file
        if version > cls.schema_version():
            logger.warning(f"{file.full_name} was saved by a newer version of {__package__.split('.')[0]}, "
                           f"changes to it will not be saved (path: {file.path})")
            user_params._read_only = True
        elif version < cls.schema_version():
            if file.auto_backup:
                file.backup()
            if user_params.save():
                logger.info(f"{file.full_name} upgraded to schema version {cls.schema_version()} "
                            f"(path: {file.path})")
        else:
            user_params._saved = user_params.to_dict()

        return user_params

    def replace_params(self, filename: pathlib.Path):
        try:
            data = read_yaml(filename)
            version = self._pop_schema_version(data)
            params = self._parse(data, version, filename)
        except (OSError, yaml.YAMLError, ValueError, dacite.DaciteError) as e:
            logger.error(f"Failed to read the file: {e} (path: {filename})")
            return None

        params._file = self._file
        return params

    def to_dict(self) -> dict:
        return {'schema_version': self.schema_version(), **asdict(self)}

    def save(self) -> bool:
        if self._file is None:
            logger.error('No output file specified')
            return False
        if self._read_only:
            logger.debug(f"{self._file.full_name} not saved: it belongs to a newer version (path: {self._file.path})")
            return False

        data = self.to_dict()
        if data == self._saved:
            return True
        if not self._file.save(data=data):
            return False

        self._saved = data
        return True

    def get_user_params_filename(self) -> str | None:
        return str(absolute_path(self._file.path)) if self._file is not None else None


def read_yaml(filename) -> dict:
    with open(filename, "r") as yaml_file:
        return yaml.safe_load(yaml_file) or {}  # return empty dictionary if the file is empty


def save_yaml(filename, data):
    with atomic_write(filename) as tmp, open(tmp, 'w') as yaml_file:
        yaml.safe_dump(data, yaml_file, sort_keys=False)
