import logging
import pathlib
import shutil
import yaml
from dataclasses import dataclass, asdict

import dacite
from dacite.exceptions import WrongTypeError, MissingValueError
from dictdiffer import diff, patch, swap

logger = logging.getLogger(__name__)


@dataclass
class LocalFile:
    directory: str
    filename: str = f"{__package__.split('.')[0]}.yml"
    full_name: str = "Local file"
    auto_backup: bool = True

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.directory) / self.filename

    def save(self, data: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            msg = f"{self.full_name} updated (path: {self.path})"
        else:
            msg = f"{self.full_name} created (path: {self.path})"

        save_yaml(self.path, data)

        logger.info(msg)

    def backup(self):
        dst = self.path.parent / (self.filename + '.bak')
        shutil.copy(self.path, dst)
        logger.info(f'{self.full_name} backed up (path: {dst})')

    def delete(self):
        if not self.path.exists():
            return

        # backup the file
        if self.auto_backup:
            self.backup()

        # delete the file
        self.path.unlink()
        logger.info(f'{self.full_name} deleted (path: {self.path})')


@dataclass
class Params:
    def __post_init__(self):
        self._user_file: LocalFile | None = None

    @classmethod
    def _read(cls, filename: pathlib.Path):
        params_dict = read_yaml(filename)
        return dacite.from_dict(data_class=cls, data=params_dict)

    @classmethod
    def read_default_params(cls, filename: str):
        return cls._read(pathlib.Path(__file__).parent.parent / 'data' / filename)

    @classmethod
    def read_user_params(cls, file: LocalFile, default: str | None = None):
        if default is None:
            params = dacite.from_dict(data_class=cls, data={})
        else:
            params = cls.read_default_params(default)

        try:
            user_params = read_yaml(file.path)
        except FileNotFoundError:
            pass
        except yaml.YAMLError:
            logger.error(f'Failed to parse `{file.path}`. The file will be overwritten.')
        else:
            # TODO: patch the user config file using dictdiffer
            try:
                user_params = dacite.from_dict(data_class=cls, data=user_params, config=dacite.Config())
            except (WrongTypeError, MissingValueError):
                logger.error(f'Failed to create a dataclass from `{file.path}`. The file will be overwritten.')
            else:
                params = user_params

        params._user_file = file
        params.save()

        return params

    def save(self, file: LocalFile | None = None):
        if file is not None:
            output_file = file
        elif self._user_file is not None:
            output_file = self._user_file
        else:
            logger.error('No output file specified')
            return

        output_file.save(data=asdict(self))

    def get_user_params_filename(self) -> str | None:
        return str(self._user_file.path.resolve()) if self._user_file is not None else None


def read_yaml(filename) -> dict:
    with open(filename, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def filter_none_values(data):
    if isinstance(data, dict):
        return {k: filter_none_values(v) for k, v in data.items() if v is not None}
    return data


def save_yaml(filename, data):
    with open(filename, 'w') as yaml_file:
        yaml.safe_dump(data, yaml_file, sort_keys=False)
