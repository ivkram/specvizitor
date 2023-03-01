import logging
import pathlib
import yaml
# from dictdiffer import diff, patch, swap
from dataclasses import dataclass, asdict
import dacite
from dacite.exceptions import WrongTypeError, MissingValueError

logger = logging.getLogger(__name__)


@dataclass
class LocalFile:
    directory: str
    filename: str = f"{__package__.split('.')[0]}.yml"
    full_name: str = "Local file"

    @property
    def path(self) -> pathlib.Path:
        return pathlib.Path(self.directory) / self.filename

    def save(self, data: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            msg = "{} updated (path: {})".format(self.full_name, self.path)
        else:
            msg = "{} created (path: {})".format(self.full_name, self.path)

        save_yaml(self.path, data)
        logger.debug(msg)


@dataclass
class Params:
    @classmethod
    def read(cls, file: LocalFile, path_to_default: str | None = None):
        default_params = read_yaml(path_to_default, in_dist=True)
        params = dacite.from_dict(data_class=cls, data=default_params)

        if file.path.exists():
            try:
                user_params = read_yaml(file.path)
            except yaml.YAMLError:
                logger.error('Error occurred when parsing `{}`. The file will be overwritten.'.format(file.path))
                cls.save(params, file)
                return params

            # TODO: patch the user config file using dictdiffer
            try:
                user_params = dacite.from_dict(data_class=cls, data=user_params, config=dacite.Config())
            except (WrongTypeError, MissingValueError):
                logger.error('Error occurred when parsing `{}`. The file will be overwritten.'.format(file.path))
                cls.save(params, file)
                return params
            else:
                return user_params
        else:
            cls.save(params, file)

        return params

    def save(self, file: LocalFile):
        file.save(data=asdict(self))


def read_yaml(filename=None, in_dist=False) -> dict:
    if filename is None:
        return {}

    if in_dist:
        yaml_path = (pathlib.Path(__file__).parent.parent / 'data' / filename).resolve()
    else:
        yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, "r") as yaml_file:
        return yaml.safe_load(yaml_file)


def filter_none_values(data):
    if isinstance(data, dict):
        return {k: filter_none_values(v) for k, v in data.items() if v is not None}
    return data


def save_yaml(filename, data):
    yaml_path = pathlib.Path(filename).resolve()

    with open(yaml_path, 'w') as yaml_file:
        yaml.safe_dump(data, yaml_file, sort_keys=False)
